from __future__ import annotations

import hashlib
from typing import Any, Callable

from financial.credit_memo import generate_credit_memo_markdown
from financial.lender_insights import generate_lender_insights
from financial.parser_audit import audit_financial_extraction
from financial.statement_extractor import extract_financial_statement
from parsers.digital_pdf import is_pdf
from parsers.hybrid_pdf import parse_pdf_hybrid

PipelineEngineRunner = Callable[[str, str, str, bytes], dict[str, Any]]

DOCUMENT_STORE: dict[str, dict[str, Any]] = {}


def document_id_for(filename: str, content: bytes) -> str:
    digest = hashlib.sha256(content).hexdigest()[:16]
    return f"{filename}:{digest}"


def parser_result_from_ocr_result(result: dict[str, Any], filename: str, content: bytes) -> dict[str, Any]:
    existing = result.get("parserResult") or result.get("parser_result")
    if isinstance(existing, dict):
        return existing

    pages = []
    for index, page in enumerate(result.get("pages") or [], start=1):
        raw_text = str(page.get("text") or "")
        confidence = float(page.get("confidence") or 0.0)
        pages.append(
            {
                "page_number": int(page.get("pageNumber") or index),
                "strategy": str(page.get("strategy") or "ocr"),
                "text_blocks": page.get("blocks") or [],
                "tables": page.get("tables") or [],
                "raw_text": raw_text,
                "confidence": confidence,
                "warnings": page.get("warnings") or [],
                "metrics": page.get("metadata")
                or {
                    "text_char_count": len(raw_text.strip()),
                    "word_count": len(raw_text.split()),
                    "table_candidate_count": len(page.get("tables") or []),
                    "image_area_ratio": 1.0,
                    "extraction_confidence": confidence,
                    "selected_strategy": str(page.get("strategy") or "ocr"),
                },
                "provenance": {
                    "digital_parser": None,
                    "digital_available": False,
                    "ocr_engine": result.get("engine"),
                    "ocr_available": bool(raw_text),
                },
            }
        )

    if not pages:
        pages.append(
            {
                "page_number": 1,
                "strategy": "failed",
                "text_blocks": [],
                "tables": [],
                "raw_text": "",
                "confidence": 0.0,
                "warnings": ["no_pages_available"],
                "metrics": {
                    "text_char_count": 0,
                    "word_count": 0,
                    "table_candidate_count": 0,
                    "image_area_ratio": 1.0,
                    "extraction_confidence": 0.0,
                    "selected_strategy": "failed",
                },
                "provenance": {
                    "digital_parser": None,
                    "digital_available": False,
                    "ocr_engine": result.get("engine"),
                    "ocr_available": False,
                },
            }
        )

    return {
        "document_id": document_id_for(filename, content),
        "document_type": result.get("documentType") or "unknown",
        "pages": pages,
        "global_warnings": result.get("warnings") or [],
        "parser_version": result.get("parserVersion") or "ocr-v1",
    }


def collect_warnings(*payloads: dict[str, Any] | None) -> list[str]:
    warnings: list[str] = []
    for payload in payloads:
        if not payload:
            continue
        for key in ("warnings", "global_warnings", "red_flags"):
            values = payload.get(key)
            if isinstance(values, list):
                warnings.extend(str(value) for value in values)
        parser_result = payload.get("parserResult") or payload.get("parser_result")
        if isinstance(parser_result, dict):
            warnings.extend(str(value) for value in parser_result.get("global_warnings") or [])
    return list(dict.fromkeys(warnings))


def enrich_pipeline_result(result: dict[str, Any], borrower_metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    financial_extraction = extract_financial_statement(result)
    parser_audit = audit_financial_extraction(result, financial_extraction)
    lender_insights = generate_lender_insights(financial_extraction, parser_audit)
    memo_markdown = generate_credit_memo_markdown(
        borrower_metadata or {},
        financial_extraction,
        parser_audit,
        lender_insights,
    )

    result["financialExtraction"] = financial_extraction
    result["parserAudit"] = parser_audit
    result["lenderInsights"] = lender_insights
    result["creditMemoMarkdown"] = memo_markdown
    return result


def run_document_pipeline(
    *,
    filename: str,
    content: bytes,
    engine: str,
    fallback_engine: str,
    document_type: str,
    run_engine_with_fallback: PipelineEngineRunner,
    borrower_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if is_pdf(filename, content):
        result = parse_pdf_hybrid(
            filename,
            content,
            document_type=document_type,
            selected_engine=engine,
            ocr_handler=lambda name, data: run_engine_with_fallback(engine, fallback_engine, name, data),
        )
    else:
        result = run_engine_with_fallback(engine, fallback_engine, filename, content)

    parser_result = parser_result_from_ocr_result(result, filename, content)
    result["parserResult"] = parser_result
    result["parserVersion"] = parser_result.get("parser_version")
    enriched = enrich_pipeline_result(result, borrower_metadata)
    store_document(enriched)
    return enriched


def store_document(result: dict[str, Any]) -> None:
    parser_result = result.get("parserResult") or {}
    document_id = parser_result.get("document_id")
    if document_id:
        DOCUMENT_STORE[str(document_id)] = result


def get_document(document_id: str | None) -> dict[str, Any] | None:
    if not document_id:
        return None
    return DOCUMENT_STORE.get(document_id)


def placeholder_pipeline_result(reason: str) -> dict[str, Any]:
    result = {
        "engine": "none",
        "engineVersion": None,
        "rawText": "",
        "markdown": None,
        "pages": [],
        "languageGuess": "unknown",
        "confidence": 0.0,
        "warnings": [reason],
        "processingTimeMs": 0,
        "fallbackUsed": True,
        "fallbackReason": reason,
        "parserResult": {
            "document_id": "missing-document",
            "document_type": "unknown",
            "pages": [],
            "global_warnings": [reason],
            "parser_version": "unavailable",
        },
        "parserVersion": "unavailable",
    }
    return enrich_pipeline_result(result)


def financial_analysis_payload(result: dict[str, Any]) -> dict[str, Any]:
    extraction = result.get("financialExtraction") or extract_financial_statement(result)
    audit = result.get("parserAudit") or audit_financial_extraction(result, extraction)
    insights = result.get("lenderInsights") or generate_lender_insights(extraction, audit)
    return {
        "document_type": extraction.get("document_type") or "unknown",
        "financial_extraction": extraction,
        "parser_audit": audit,
        "lender_insights": insights,
    }


def credit_memo_payload(
    result: dict[str, Any],
    borrower_metadata: dict[str, Any] | None = None,
    extra_warnings: list[str] | None = None,
) -> dict[str, Any]:
    extraction = result.get("financialExtraction") or extract_financial_statement(result)
    audit = result.get("parserAudit") or audit_financial_extraction(result, extraction)
    insights = result.get("lenderInsights") or generate_lender_insights(extraction, audit)
    memo = generate_credit_memo_markdown(borrower_metadata or {}, extraction, audit, insights)
    return {
        "memo_markdown": memo,
        "data_quality": {
            "overall_accuracy_score": audit.get("overall_accuracy_score"),
            "recommended_manual_review_fields": audit.get("recommended_manual_review_fields") or [],
            "lender_insight_readiness": audit.get("lender_insight_readiness") or {},
        },
        "warnings": collect_warnings(result, audit) + (extra_warnings or []),
    }


def full_pipeline_payload(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "parse_result": result.get("parserResult") or {},
        "financial_extraction": result.get("financialExtraction") or {},
        "parser_audit": result.get("parserAudit") or {},
        "lender_insights": result.get("lenderInsights") or {},
        "memo_markdown": result.get("creditMemoMarkdown") or "",
    }
