from __future__ import annotations

import re
from typing import Any

MINIMUM_REQUIRED_FIELDS = [
    "revenue",
    "net_profit",
    "total_assets",
    "total_liabilities",
    "equity",
]


def _all_text(parsed_document: dict[str, Any]) -> str:
    parser_result = parsed_document.get("parserResult") or parsed_document.get("parser_result") or {}
    pages = parser_result.get("pages") or parsed_document.get("pages") or []
    chunks = []
    for page in pages:
        chunks.append(str(page.get("raw_text") or page.get("text") or ""))
    return "\n".join(chunks)


def _field_value(extraction: dict[str, Any], field: str) -> Any:
    for group in ("income_statement", "balance_sheet", "cash_flow"):
        values = extraction.get(group) or {}
        if field in values:
            return values.get(field)
    return None


def _source_reference_map(extraction: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    references: dict[str, list[dict[str, Any]]] = {}
    for reference in extraction.get("source_references") or []:
        field = reference.get("field")
        if field:
            references.setdefault(field, []).append(reference)
    return references


def _score_reference(field: str, value: Any, references: list[dict[str, Any]]) -> tuple[float, bool, int | None, list[str]]:
    issues: list[str] = []
    if value is None:
        return 0.0, False, None, ["missing_value"]

    if not references:
        return 0.28, False, None, ["missing_source_reference"]

    best = max(references, key=lambda item: float(item.get("confidence") or 0))
    score = 0.45
    evidence_found = True
    page_number = best.get("page_number")

    if page_number is not None:
        score += 0.18
    else:
        issues.append("missing_page_reference")

    if best.get("raw_label"):
        score += 0.16
    else:
        issues.append("missing_raw_label")

    if best.get("raw_value") is not None:
        score += 0.1
    else:
        issues.append("missing_raw_value")

    reference_confidence = float(best.get("confidence") or 0)
    score += min(reference_confidence, 1.0) * 0.11

    if best.get("source") == "table":
        score += 0.04
    elif best.get("source") == "text":
        score += 0.01
    else:
        issues.append("unknown_source_type")

    distinct_values = {str(reference.get("value")) for reference in references if reference.get("value") is not None}
    if len(distinct_values) > 1:
        score = min(score, 0.48)
        issues.append("conflicting_values_across_sources")

    return min(score, 1.0), evidence_found, page_number, issues


def _approx_equal(left: float, right: float) -> bool:
    tolerance = max(abs(left), abs(right), 1.0) * 0.03
    return abs(left - right) <= tolerance


def _period_conflicts(parsed_document: dict[str, Any], extraction: dict[str, Any]) -> list[str]:
    text = _all_text(parsed_document)
    raw_years = {int(year) for year in re.findall(r"\b(20\d{2}|19\d{2})\b", text)}
    period = extraction.get("period") or {}
    fiscal_year = period.get("fiscal_year")
    end_date = str(period.get("end_date") or "")
    end_year_match = re.search(r"\b(20\d{2}|19\d{2})\b", end_date)

    # Old registration, founding, or certificate years are common in Mongolian
    # documents and should not be treated as reporting-period conflicts.
    years = {str(year) for year in raw_years if 2000 <= year <= 2035}
    if fiscal_year:
        years.discard(str(fiscal_year))
    if end_year_match:
        years.discard(end_year_match.group(1))
    if len(years) >= 2:
        return [f"period_conflict: multiple fiscal years detected in source text ({', '.join(sorted(years))})."]
    return []


def _readiness(extraction: dict[str, Any], red_flags: list[str]) -> dict[str, Any]:
    period = extraction.get("period") or {}
    period_present = bool(period.get("fiscal_year") or period.get("end_date"))
    missing_required = [field for field in MINIMUM_REQUIRED_FIELDS if _field_value(extraction, field) is None]
    minimum_present = not missing_required and period_present

    if not minimum_present:
        reason = f"Missing minimum credit memo fields: {', '.join(missing_required + ([] if period_present else ['period_or_fiscal_year']))}."
    elif red_flags:
        reason = "Manual review recommended because red flags were detected."
    else:
        reason = "Minimum financial statement fields are present and no blocking red flags were detected."

    return {
        "ready_for_credit_memo": minimum_present and not red_flags,
        "reason": reason,
        "minimum_required_fields_present": minimum_present,
    }


def audit_financial_extraction(parsed_document: dict[str, Any], extraction: dict[str, Any]) -> dict[str, Any]:
    references_by_field = _source_reference_map(extraction)
    field_scores = []
    red_flags: list[str] = []
    warnings: list[str] = []
    manual_review_fields: set[str] = set()

    candidate_fields = sorted(set(references_by_field.keys()) | set(extraction.get("extraction_confidence", {}).keys()))
    for required in MINIMUM_REQUIRED_FIELDS:
        if required not in candidate_fields:
            candidate_fields.append(required)

    for field in candidate_fields:
        value = _field_value(extraction, field)
        score, evidence_found, page_number, issues = _score_reference(field, value, references_by_field.get(field, []))
        field_scores.append(
            {
                "field": field,
                "value": value,
                "confidence": round(score, 4),
                "evidence_found": evidence_found,
                "page_number": page_number,
                "issues": issues,
            }
        )
        if score < 0.65 or issues:
            manual_review_fields.add(field)

    total_assets = _field_value(extraction, "total_assets")
    total_liabilities = _field_value(extraction, "total_liabilities")
    equity = _field_value(extraction, "equity")
    revenue = _field_value(extraction, "revenue")
    net_profit = _field_value(extraction, "net_profit")

    if all(value is not None for value in [total_assets, total_liabilities, equity]):
        if not _approx_equal(float(total_assets), float(total_liabilities) + float(equity)):
            red_flags.append("balance_sheet_mismatch: total assets do not approximately equal liabilities plus equity.")
            manual_review_fields.update(["total_assets", "total_liabilities", "equity"])

    if net_profit is not None:
        text = _all_text(parsed_document).lower()
        has_loss_word = "loss" in text or "алдагдал" in text
        if has_loss_word and float(net_profit) > 0:
            red_flags.append("profit_sign_conflict: source text mentions loss but extracted net profit is positive.")
            manual_review_fields.add("net_profit")

    if revenue is None and net_profit is not None:
        red_flags.append("revenue_missing_but_profit_present: revenue is missing while net profit was extracted.")
        manual_review_fields.add("revenue")

    if total_assets is not None and total_liabilities is not None and float(total_liabilities) > float(total_assets):
        red_flags.append("liabilities_exceed_assets: total liabilities exceed total assets.")
        manual_review_fields.update(["total_assets", "total_liabilities"])

    for warning in _period_conflicts(parsed_document, extraction):
        warnings.append(warning)
        manual_review_fields.add("period")

    if not field_scores:
        overall_score = 0.0
        warnings.append("no_auditable_fields: no extracted financial fields were available to audit.")
    else:
        overall_score = sum(field["confidence"] for field in field_scores) / len(field_scores)
        if red_flags:
            overall_score = min(overall_score, 0.62)
        if warnings:
            overall_score = min(overall_score, 0.74)

    readiness = _readiness(extraction, red_flags)
    if not readiness["minimum_required_fields_present"]:
        overall_score = min(overall_score, 0.58)

    return {
        "overall_accuracy_score": round(max(0.0, min(overall_score, 1.0)), 4),
        "field_scores": field_scores,
        "red_flags": red_flags,
        "warnings": warnings,
        "recommended_manual_review_fields": sorted(manual_review_fields),
        "lender_insight_readiness": readiness,
    }
