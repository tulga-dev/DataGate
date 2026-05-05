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


def _numeric_cells(values: list[str]) -> list[tuple[str, ParsedNumber]]:
    parsed_values = []
    for value in values:
        parsed = find_number(value)
        if parsed:
            parsed_values.append((value, parsed))
    return parsed_values


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
        cells = [str(value).strip() for value in row if str(value).strip()]
        if len(cells) < 2:
            continue

        label_match = None
        label_index = 0
        label = ""
        for index, cell in enumerate(cells):
            label_match = map_label_to_field(cell)
            if label_match:
                label_index = index
                label = cell
                break

        if not label_match:
            combined_label = " ".join(cell for cell in cells if not find_number(cell))
            label_match = map_label_to_field(combined_label)
            label = combined_label

        if not label_match:
            continue

        value_candidates = cells[label_index + 1 :] or cells
        parsed_candidates = _numeric_cells(value_candidates)
        if not parsed_candidates:
            parsed_candidates = _numeric_cells(cells)
        if not parsed_candidates:
            continue

        raw_value, parsed = parsed_candidates[-1]
        reference = {
            "field": label_match.field,
            "value": parsed.value,
            "raw_value": parsed.raw_value,
            "page_number": page_number,
            "source": "table",
            "raw_label": label_match.raw_label,
            "raw_cell": raw_value,
            "row_text": " | ".join(cells),
            "confidence": label_match.confidence,
        }
        _set_field(result, label_match.field, parsed, reference)


def _extract_from_text(result: dict[str, Any], text: str, page_number: int) -> None:
    lines = [line.strip() for line in text.splitlines()]
    for index, clean_line in enumerate(lines):
        if not clean_line:
            continue
        parts = re.split(r"[:：\t]| {2,}", clean_line, maxsplit=1)
        if len(parts) < 2:
            match = re.match(r"(.+?)\s+(\(?-?\d[\d,\s]*(?:\.\d+)?\)?)\s*(?:MNT|USD|₮|төгрөг)?$", clean_line)
            if not match:
                label_match = map_label_to_field(clean_line)
                if not label_match:
                    continue
                next_values = " ".join(lines[index + 1 : index + 3])
                parsed = find_number(next_values)
                if not parsed:
                    continue
                reference = {
                    "field": label_match.field,
                    "value": parsed.value,
                    "raw_value": parsed.raw_value,
                    "page_number": page_number,
                    "source": "text",
                    "raw_label": label_match.raw_label,
                    "source_text": f"{clean_line} {next_values}".strip(),
                    "confidence": max(0.48, label_match.confidence - 0.14),
                }
                _set_field(result, label_match.field, parsed, reference)
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


def _count_accounting_label_hits(pages: list[dict[str, Any]]) -> int:
    hits = 0
    for page in pages:
        for line in str(page.get("raw_text") or page.get("text") or "").splitlines():
            if map_label_to_field(line):
                hits += 1
        for table in page.get("tables") or []:
            for row in table.get("rows") or []:
                if isinstance(row, list) and any(map_label_to_field(str(cell)) for cell in row):
                    hits += 1
    return hits


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
    if classification.document_type == "unknown" and _count_accounting_label_hits(pages) >= 2:
        classification.document_type = "financial_statement"
        classification.confidence = max(classification.confidence, 0.58)
        classification.reasons.append("Detected multiple accounting labels in parsed text/tables.")

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
