from __future__ import annotations

from typing import Any


def _field_value(extraction: dict[str, Any], field: str) -> int | float | None:
    for group in ("income_statement", "balance_sheet", "cash_flow"):
        values = extraction.get(group) or {}
        if field in values:
            value = values.get(field)
            return value if isinstance(value, int | float) else None
    return None


def _safe_ratio(numerator: int | float | None, denominator: int | float | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return round(float(numerator) / float(denominator), 4)


def _metric_status(value: float | None) -> str:
    return "available" if value is not None else "missing"


def _period_label(extraction: dict[str, Any]) -> str | None:
    period = extraction.get("period") or {}
    if period.get("fiscal_year"):
        return str(period["fiscal_year"])
    if period.get("end_date"):
        return str(period["end_date"])
    return None


def generate_lender_insights(extraction: dict[str, Any], parser_audit: dict[str, Any]) -> dict[str, Any]:
    revenue = _field_value(extraction, "revenue")
    gross_profit = _field_value(extraction, "gross_profit")
    net_profit = _field_value(extraction, "net_profit")
    total_assets = _field_value(extraction, "total_assets")
    current_assets = _field_value(extraction, "current_assets")
    cash = _field_value(extraction, "cash")
    total_liabilities = _field_value(extraction, "total_liabilities")
    short_term_debt = _field_value(extraction, "short_term_debt")
    equity = _field_value(extraction, "equity")

    key_metrics = {
        "gross_margin": _safe_ratio(gross_profit, revenue),
        "net_margin": _safe_ratio(net_profit, revenue),
        "debt_to_assets": _safe_ratio(total_liabilities, total_assets),
        "debt_to_equity": _safe_ratio(total_liabilities, equity),
        "current_ratio": _safe_ratio(current_assets, short_term_debt),
        "return_on_assets": _safe_ratio(net_profit, total_assets),
        "equity_ratio": _safe_ratio(equity, total_assets),
    }

    risk_flags: list[str] = []
    positive_signals: list[str] = []
    questions: list[str] = []
    next_steps: list[str] = []

    audit_score = float(parser_audit.get("overall_accuracy_score") or 0)
    readiness = parser_audit.get("lender_insight_readiness") or {}
    ready_for_memo = bool(readiness.get("ready_for_credit_memo"))

    if net_profit is not None and net_profit < 0:
        risk_flags.append("negative_net_profit")
        questions.append("Please explain the reason for negative net profit.")
    elif net_profit is not None and net_profit > 0:
        positive_signals.append("profitable")

    if equity is not None and equity < 0:
        risk_flags.append("negative_equity")
        questions.append("Please explain the negative equity position.")
    elif equity is not None and equity > 0:
        positive_signals.append("positive_equity")

    if total_assets is not None and total_liabilities is not None and total_liabilities > total_assets:
        risk_flags.append("liabilities_exceed_assets")

    debt_to_assets = key_metrics["debt_to_assets"]
    if debt_to_assets is not None:
        if debt_to_assets > 0.7:
            risk_flags.append("high_leverage_debt_to_assets")
            questions.append("Please provide a breakdown of liabilities and debt maturity.")
        elif debt_to_assets < 0.5:
            positive_signals.append("low_leverage")

    current_ratio = key_metrics["current_ratio"]
    if current_ratio is not None:
        if current_ratio < 1.0:
            risk_flags.append("weak_current_ratio")
            questions.append("Please provide a breakdown of short-term liabilities.")
        elif current_ratio > 1.5:
            positive_signals.append("current_ratio_above_1_5")

    if revenue is None:
        risk_flags.append("missing_revenue")
        questions.append("Please provide bank statements to verify reported revenue.")

    if cash is None:
        risk_flags.append("missing_cash")
        questions.append("Please provide cash and bank balance details.")
    elif cash > 0:
        positive_signals.append("cash_balance_available")

    if audit_score < 0.65:
        risk_flags.append("low_parser_confidence")
        questions.append("Please provide the original signed/source financial statements for manual verification.")
    elif audit_score >= 0.85:
        positive_signals.append("parser_confidence_high")

    if not ready_for_memo:
        risk_flags.append("document_not_ready_for_memo")
        next_steps.append("Send the document for manual review before generating a credit memo.")

    for audit_flag in parser_audit.get("red_flags") or []:
        if audit_flag not in risk_flags:
            risk_flags.append(audit_flag)

    for field in parser_audit.get("recommended_manual_review_fields") or []:
        next_steps.append(f"Review extracted field: {field}.")

    if revenue is not None and "bank statements" not in " ".join(questions).lower():
        next_steps.append("Verify revenue against bank statements and tax filings.")

    if not questions and not risk_flags:
        questions.append("Please confirm whether the submitted statements are final audited figures.")

    borrower_summary = {
        "period": _period_label(extraction),
        "currency": extraction.get("currency", "unknown"),
        "revenue": revenue,
        "net_profit": net_profit,
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "equity": equity,
        "audit_score": audit_score,
    }

    risk_assessment = {
        "risk_level": "high" if risk_flags else "moderate" if audit_score < 0.85 else "low",
        "risk_flags": risk_flags,
        "positive_signals": positive_signals,
        "parser_audit_score": audit_score,
    }

    data_quality = {
        "ready_for_credit_memo": ready_for_memo,
        "minimum_required_fields_present": bool(readiness.get("minimum_required_fields_present")),
        "parser_audit_reason": readiness.get("reason"),
        "metric_availability": {metric: _metric_status(value) for metric, value in key_metrics.items()},
    }

    return {
        "borrower_summary": borrower_summary,
        "key_metrics": key_metrics,
        "risk_flags": list(dict.fromkeys(risk_flags)),
        "positive_signals": list(dict.fromkeys(positive_signals)),
        "questions_for_borrower": list(dict.fromkeys(questions)),
        "credit_memo_inputs": {
            "financial_snapshot": borrower_summary,
            "risk_assessment": risk_assessment,
            "data_quality": data_quality,
            "recommended_next_steps": list(dict.fromkeys(next_steps)),
        },
    }
