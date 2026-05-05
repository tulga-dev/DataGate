from __future__ import annotations

import re
from typing import Any

from financial.classifier import classify_financial_document
from financial.label_mapping import all_schema_fields, map_label_to_field
from financial.numbers import ParsedNumber, find_number


FIELD_GROUPS = {
    "income_statement": [
        "revenue",
        "cost_of_goods_sold",
        "gross_profit",
        "operating_expenses",
        "operating_profit",
        "net_profit",
    ],
    "balance_sheet": [
        "total_assets",
        "current_assets",
        "cash",
        "inventory",
        "receivables",
        "total_liabilities",
        "short_term_debt",
        "long_term_debt",
        "equity",
    ],
    "cash_flow": [
        "operating_cash_flow",
        "investing_cash_flow",
        "financing_cash_flow",
        "ending_cash",
    ],
}


def empty_financial_statement() -> dict[str, Any]:
    return {
        "period": {
            "start_date": None,
            "end_date": None,
            "fiscal_year": None,
        },
        "currency": "unknown",
        "income_statement": {field: None for field in FIELD_GROUPS["income_statement"]},
        "balance_sheet": {field: None for field in FIELD_GROUPS["balance_sheet"]},
        "cash_flow": {field: None for field in FIELD_GROUPS["cash_flow"]},
        "extraction_confidence": {},
        "missing_fields": [],
        "source_references": [],
    }


def _field_group(field: str) -> str | None:
    for group, fields in FIELD_GROUPS.items():
        if field in fields:
            return group
    return None


def _set_field(result: dict[str, Any], field: str, parsed: ParsedNumber, reference: dict[str, Any]) -> None:
    group = _field_group(field)
    if not group:
        return
    current_confidence = result["extraction_confidence"].get(field, 0)
    if result[group][field] is not None and current_confidence > reference["confidence"]:
        return

    result[group][field] = parsed.value
    result["extraction_confidence"][field] = reference["confidence"]
    result["source_references"] = [
        existing for existing in result["source_references"] if existing.get("field") != field
    ]
    result["source_references"].append(reference)


def _detect_currency(text: str) -> str:
    lowered = text.lower()
    if "mnt" in lowered or "₮" in text or "төгрөг" in lowered:
        return "MNT"
    if "usd" in lowered or "$" in text:
        return "USD"
    return "unknown"


def _detect_period(text: str) -> dict[str, Any]:
    years = re.findall(r"\b(20\d{2}|19\d{2})\b", text)
    dates = re.findall(r"\b(20\d{2}-\d{2}-\d{2}|19\d{2}-\d{2}-\d{2})\b", text)
    return {
        "start_date": dates[0] if len(dates) >= 2 else None,
        "end_date": dates[-1] if dates else None,
        "fiscal_year": int(years[-1]) if years else None,
    }


def _iter_parser_pages(parsed_document: dict[str, Any]) -> list[dict[str, Any]]:
    parser_result = parsed_document.get("parserResult") or parsed_document.get("parser_result") or {}
    pages = parser_result.get("pages") or []
    if pages:
        return pages

    return [
        {
            "page_number": page.get("pageNumber", 1),
            "raw_text": page.get("text", ""),
            "tables": page.get("tables", []),
        }
        for page in parsed_document.get("pages", [])
    ]


def _extract_from_table(result: dict[str, Any], table: dict[str, Any], page_number: int) -> None:
    rows = table.get("rows") or []
    columns = table.get("columns") or []
    combined_rows = []
    if columns:
        combined_rows.append(columns)
    combined_rows.extend(rows)

    for row in combined_rows:
        if not isinstance(row, list) or len(row) < 2:
            continue
        label = str(row[0]).strip()
        value_candidates = [str(value).strip() for value in row[1:] if str(value).strip()]
        if not label or not value_candidates:
            continue
        label_match = map_label_to_field(label)
        if not label_match:
            continue
        parsed = None
        raw_value = ""
        for candidate in reversed(value_candidates):
            parsed = find_number(candidate)
            raw_value = candidate
            if parsed:
                break
        if not parsed:
            continue
        reference = {
            "field": label_match.field,
            "value": parsed.value,
            "raw_value": parsed.raw_value,
            "page_number": page_number,
            "source": "table",
            "raw_label": label_match.raw_label,
            "raw_cell": raw_value,
            "confidence": label_match.confidence,
        }
        _set_field(result, label_match.field, parsed, reference)


def _extract_from_text(result: dict[str, Any], text: str, page_number: int) -> None:
    for line in text.splitlines():
        clean_line = line.strip()
        if not clean_line:
            continue
        parts = re.split(r"[:：\t]| {2,}", clean_line, maxsplit=1)
        if len(parts) < 2:
            match = re.match(r"(.+?)\s+(\(?-?\d[\d,\s]*(?:\.\d+)?\)?)\s*(?:MNT|USD|₮)?$", clean_line)
            if not match:
                continue
            label, value_text = match.group(1), match.group(2)
        else:
            label, value_text = parts[0], parts[1]

        label_match = map_label_to_field(label)
        if not label_match:
            continue

        parsed = find_number(value_text)
        if not parsed:
            continue

        reference = {
            "field": label_match.field,
            "value": parsed.value,
            "raw_value": parsed.raw_value,
            "page_number": page_number,
            "source": "text",
            "raw_label": label_match.raw_label,
            "source_text": clean_line,
            "confidence": max(0.5, label_match.confidence - 0.08),
        }
        _set_field(result, label_match.field, parsed, reference)


def extract_financial_statement(parsed_document: dict[str, Any]) -> dict[str, Any]:
    pages = _iter_parser_pages(parsed_document)
    all_text = "\n".join(str(page.get("raw_text") or page.get("text") or "") for page in pages)
    classification = classify_financial_document(all_text)
    parser_result = parsed_document.get("parserResult") or parsed_document.get("parser_result") or {}
    document_type_hint = parser_result.get("document_type")
    if classification.document_type == "unknown" and document_type_hint == "financial_statement":
        classification.document_type = "financial_statement"
        classification.confidence = max(classification.confidence, 0.62)
        classification.reasons.append("Used parser document_type hint: financial_statement.")
    result = empty_financial_statement()
    result["document_type"] = classification.document_type
    result["classification_confidence"] = classification.confidence
    result["classification_reasons"] = classification.reasons
    result["period"] = _detect_period(all_text)
    result["currency"] = _detect_currency(all_text)

    if classification.document_type != "financial_statement":
        result["missing_fields"] = all_schema_fields()
        return result

    for page in pages:
        page_number = int(page.get("page_number") or page.get("pageNumber") or 1)
        for table in page.get("tables") or []:
            _extract_from_table(result, table, page_number)
        _extract_from_text(result, str(page.get("raw_text") or page.get("text") or ""), page_number)

    present_fields = set(result["extraction_confidence"].keys())
    result["missing_fields"] = [field for field in all_schema_fields() if field not in present_fields]
    return result
