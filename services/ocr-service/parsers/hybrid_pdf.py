from __future__ import annotations

import hashlib
from dataclasses import dataclass
from time import perf_counter
from typing import Callable

from normalize import NormalizedPage, average, normalize_ocr_response
from parsers.digital_pdf import DigitalPdfPage, extract_digital_pdf, is_pdf
from parsers.tables import extract_tables

OCRHandler = Callable[[str, bytes], dict]

MIN_DIGITAL_CHARS = 80
MIN_DIGITAL_WORDS = 10
MIN_DIGITAL_CONFIDENCE = 0.55


@dataclass
class PageDecision:
    text_char_count: int
    word_count: int
    table_candidate_count: int
    image_area_ratio: float
    extraction_confidence: float
    selected_strategy: str


def _page_decision(page: DigitalPdfPage, table_count: int) -> PageDecision:
    text = page.raw_text.strip()
    char_count = len(text)
    word_count = len(text.split())
    digital_is_usable = (
        char_count >= MIN_DIGITAL_CHARS
        and word_count >= MIN_DIGITAL_WORDS
        and page.extraction_confidence >= MIN_DIGITAL_CONFIDENCE
    )
    scanned_like = page.image_area_ratio >= 0.75 and char_count < MIN_DIGITAL_CHARS
    selected_strategy = "digital" if digital_is_usable and not scanned_like else "ocr"

    return PageDecision(
        text_char_count=char_count,
        word_count=word_count,
        table_candidate_count=table_count,
        image_area_ratio=page.image_area_ratio,
        extraction_confidence=page.extraction_confidence,
        selected_strategy=selected_strategy,
    )


def _ocr_page_by_number(ocr_result: dict, page_number: int) -> dict | None:
    for page in ocr_result.get("pages") or []:
        if page.get("pageNumber") == page_number:
            return page
    pages = ocr_result.get("pages") or []
    if len(pages) == 1:
        return pages[0]
    return None


def _merge_text(digital_text: str, ocr_text: str) -> str:
    digital_text = digital_text.strip()
    ocr_text = ocr_text.strip()
    if digital_text and ocr_text and ocr_text not in digital_text:
        return f"{digital_text}\n\n--- OCR fallback text ---\n{ocr_text}"
    return digital_text or ocr_text


def _is_mock_fallback_result(ocr_result: dict | None) -> bool:
    if not ocr_result:
        return False
    warnings = " ".join(str(warning) for warning in (ocr_result.get("warnings") or []))
    return bool(
        ocr_result.get("fallbackUsed")
        and str(ocr_result.get("engine") or "").lower() == "mock"
        and "fallback_engine_used" in warnings
    )


def _document_id(filename: str, content: bytes) -> str:
    digest = hashlib.sha256(content).hexdigest()[:16]
    return f"{filename}:{digest}"


def parse_pdf_hybrid(
    filename: str,
    content: bytes,
    *,
    document_type: str = "unknown",
    selected_engine: str,
    ocr_handler: OCRHandler,
    started_at: float | None = None,
) -> dict:
    started_at = started_at or perf_counter()

    if not is_pdf(filename, content):
        return ocr_handler(filename, content)

    digital_result = extract_digital_pdf(filename, content)
    table_result = extract_tables(filename, content)
    global_warnings = [*digital_result.warnings, *table_result.warnings]
    tables_by_page = table_result.tables_by_page

    decisions: dict[int, PageDecision] = {}
    needs_ocr = not digital_result.pages

    for page in digital_result.pages:
        table_count = len(tables_by_page.get(page.page_number, []))
        decision = _page_decision(page, table_count)
        decisions[page.page_number] = decision
        if decision.selected_strategy == "ocr":
            needs_ocr = True

    ocr_result: dict | None = None
    mock_fallback_ignored = False
    if needs_ocr:
        ocr_result = ocr_handler(filename, content)
        if _is_mock_fallback_result(ocr_result):
            mock_fallback_ignored = True
            global_warnings.extend(
                warning
                for warning in (ocr_result.get("warnings") or [])
                if "fallback_engine_used" not in str(warning)
            )
            global_warnings.append(
                "ocr_fallback_mock_ignored: real OCR failed, so mock OCR text was not used for this uploaded PDF."
            )
        else:
            global_warnings.extend(ocr_result.get("warnings") or [])

    normalized_pages: list[NormalizedPage] = []
    parser_pages: list[dict] = []
    all_page_numbers = sorted(
        set([page.page_number for page in digital_result.pages])
        | set(page.get("pageNumber", 1) for page in ((ocr_result or {}).get("pages") or []))
        or {1}
    )

    digital_by_page = {page.page_number: page for page in digital_result.pages}

    for page_number in all_page_numbers:
        digital_page = digital_by_page.get(page_number)
        ocr_page = _ocr_page_by_number(ocr_result or {}, page_number)
        page_tables = tables_by_page.get(page_number, [])
        page_warnings: list[str] = []

        if digital_page:
            page_warnings.extend(digital_page.warnings)
            decision = decisions.get(page_number) or _page_decision(digital_page, len(page_tables))
            digital_text = digital_page.raw_text
            digital_confidence = digital_page.extraction_confidence
            text_blocks = digital_page.text_blocks
            image_area_ratio = digital_page.image_area_ratio
        else:
            decision = PageDecision(0, 0, len(page_tables), 1.0, 0.0, "ocr")
            digital_text = ""
            digital_confidence = 0.0
            text_blocks = []
            image_area_ratio = 1.0
            page_warnings.append("digital_page_missing: no digital text page was available.")

        if mock_fallback_ignored:
            ocr_page = None
            page_warnings.append("ocr_unavailable: real OCR failed and mock fallback text was ignored.")

        ocr_text = (ocr_page or {}).get("text", "")
        ocr_confidence = float((ocr_page or {}).get("confidence", 0.0) or 0.0)

        if decision.selected_strategy == "digital" and not ocr_text:
            strategy = "digital"
            raw_text = digital_text
            confidence = digital_confidence
        elif digital_text and ocr_text:
            strategy = "hybrid"
            raw_text = _merge_text(digital_text, ocr_text)
            confidence = max(digital_confidence, ocr_confidence)
        elif ocr_text:
            strategy = "ocr"
            raw_text = ocr_text
            confidence = ocr_confidence
        else:
            strategy = "failed"
            raw_text = digital_text
            confidence = digital_confidence
            page_warnings.append("page_extraction_failed: neither digital extraction nor OCR produced usable text.")

        page_metadata = {
            "text_char_count": len(raw_text.strip()),
            "word_count": len(raw_text.split()),
            "table_candidate_count": len(page_tables),
            "image_area_ratio": image_area_ratio,
            "extraction_confidence": confidence,
            "selected_strategy": strategy,
        }

        normalized_pages.append(
            NormalizedPage(
                page_number=page_number,
                text=raw_text,
                confidence=confidence,
                blocks=text_blocks,
                tables=page_tables,
                warnings=page_warnings,
                strategy=strategy,
                metadata=page_metadata,
            )
        )
        parser_pages.append(
            {
                "page_number": page_number,
                "strategy": strategy,
                "text_blocks": text_blocks,
                "tables": page_tables,
                "raw_text": raw_text,
                "confidence": confidence,
                "warnings": page_warnings,
                "metrics": page_metadata,
                "provenance": {
                    "digital_parser": digital_result.parser_name,
                    "digital_available": bool(digital_text),
                    "ocr_engine": (ocr_result or {}).get("engine"),
                    "ocr_available": bool(ocr_text),
                },
            }
        )

    parser_result = {
        "document_id": _document_id(filename, content),
        "document_type": document_type,
        "pages": parser_pages,
        "global_warnings": global_warnings,
        "parser_version": "hybrid-v1",
    }

    final_engine = selected_engine if mock_fallback_ignored else (ocr_result or {}).get("engine", selected_engine)
    final_engine_version = (ocr_result or {}).get("engineVersion", "hybrid-v1")
    fallback_used = bool((ocr_result or {}).get("fallbackUsed", False))
    fallback_reason = (ocr_result or {}).get("fallbackReason")
    confidence = average([page.confidence for page in normalized_pages])

    result = normalize_ocr_response(
        engine=final_engine,
        engine_version=final_engine_version,
        pages=normalized_pages,
        confidence=confidence,
        started_at=started_at,
        warnings=global_warnings,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
        parser_result=parser_result,
        parser_version="hybrid-v1",
    )
    return result
