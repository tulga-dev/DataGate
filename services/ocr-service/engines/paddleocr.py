from __future__ import annotations

import importlib.metadata
import os
from pathlib import Path
from time import perf_counter
from typing import Any

from engines.common import temp_document_path
from engines.mock import extract_with_mock
from normalize import NormalizedPage, average, collect_text_and_scores, normalize_ocr_response


def _create_paddleocr():
    from paddleocr import PaddleOCR

    options: dict[str, Any] = {
        "use_doc_orientation_classify": False,
        "use_doc_unwarping": False,
        "use_textline_orientation": False,
        "device": os.getenv("PADDLEOCR_DEVICE", "cpu"),
    }
    lang = os.getenv("PADDLEOCR_LANG")
    version = os.getenv("PADDLEOCR_VERSION")

    if lang:
        options["lang"] = lang
    if version:
        options["ocr_version"] = version

    try:
        return PaddleOCR(**options)
    except TypeError:
        legacy_options: dict[str, Any] = {
            "use_angle_cls": False,
            "lang": lang or "en",
        }
        return PaddleOCR(**legacy_options)


def _is_pdf(filename: str, content: bytes) -> bool:
    return Path(filename).suffix.lower() == ".pdf" or content.startswith(b"%PDF")


def _run_paddleocr_on_path(ocr: Any, input_path: Path) -> tuple[str, float]:
    if hasattr(ocr, "predict"):
        raw_result = ocr.predict(str(input_path))
    else:
        raw_result = ocr.ocr(str(input_path), cls=False)

    texts, scores = collect_text_and_scores(raw_result)
    deduped_text = "\n".join(dict.fromkeys(texts)).strip()
    return deduped_text, average(scores)


def _mock_fallback(filename: str, content: bytes, *, version: str, warning: str, reason: str) -> dict:
    result = extract_with_mock(filename, content)
    result["engine"] = "paddleocr"
    result["engineVersion"] = version
    result["warnings"] = [warning]
    result["fallbackUsed"] = True
    result["fallbackReason"] = reason
    return result


def extract_with_paddleocr(filename: str, content: bytes) -> dict:
    started = perf_counter()

    try:
        version = importlib.metadata.version("paddleocr")
    except importlib.metadata.PackageNotFoundError:
        return _mock_fallback(
            filename,
            content,
            version="not-installed",
            warning="paddleocr_not_installed: install paddleocr and paddlepaddle to enable real PaddleOCR inference.",
            reason="PaddleOCR package is not installed.",
        )

    try:
        ocr = _create_paddleocr()
        pages: list[NormalizedPage] = []

        if _is_pdf(filename, content):
            try:
                from pdf2image import convert_from_bytes
            except ImportError:
                return _mock_fallback(
                    filename,
                    content,
                    version=version,
                    warning="pdf2image_not_installed: install pdf2image and Poppler to OCR PDF files with PaddleOCR.",
                    reason="PDF input requires pdf2image.",
                )

            try:
                images = convert_from_bytes(content)
            except Exception as error:
                return _mock_fallback(
                    filename,
                    content,
                    version=version,
                    warning=f"pdf2image_not_installed: pdf2image is installed, but PDF conversion failed. Poppler may be missing. Detail: {error}",
                    reason="PDF conversion failed before PaddleOCR inference.",
                )

            for index, image in enumerate(images, start=1):
                with temp_document_path(f"{Path(filename).stem}-page-{index}.png", b"") as page_path:
                    image.save(page_path, format="PNG")
                    text, page_confidence = _run_paddleocr_on_path(ocr, page_path)
                pages.append(NormalizedPage(page_number=index, text=text, confidence=page_confidence))
        else:
            with temp_document_path(filename, content) as input_path:
                text, page_confidence = _run_paddleocr_on_path(ocr, input_path)
            pages.append(NormalizedPage(page_number=1, text=text, confidence=page_confidence))

        raw_text = "\n\n".join(page.text for page in pages if page.text).strip()
        confidence = average([page.confidence for page in pages])
        warnings: list[str] = []

        if not raw_text:
            warnings.append("no_text_detected: PaddleOCR returned no recognized text.")
        if raw_text and confidence < 0.65:
            warnings.append("low_confidence_ocr: PaddleOCR confidence is below 0.65.")

        return normalize_ocr_response(
            engine="paddleocr",
            engine_version=version,
            pages=pages,
            confidence=confidence,
            started_at=started,
            warnings=warnings,
        )
    except Exception as error:
        return _mock_fallback(
            filename,
            content,
            version=version,
            warning=f"paddleocr_runtime_error: {error}",
            reason="PaddleOCR failed at runtime.",
        )
