from __future__ import annotations

from typing import Any


RISK_LABELS = {
    "negative_net_profit": "Цэвэр ашиг сөрөг байна.",
    "negative_equity": "Өөрийн хөрөнгө сөрөг байна.",
    "liabilities_exceed_assets": "Өр төлбөр нийт хөрөнгөөс өндөр байна.",
    "high_leverage_debt_to_assets": "Өр / хөрөнгийн харьцаа өндөр байна.",
    "weak_current_ratio": "Эргэлтийн харьцаа сул байна.",
    "missing_revenue": "Борлуулалтын орлого дутуу байна.",
    "missing_cash": "Мөнгөн хөрөнгийн мэдээлэл дутуу байна.",
    "low_parser_confidence": "Өгөгдөл уншилтын итгэлцэл бага байна.",
    "document_not_ready_for_memo": "Баримт шууд зээлийн мемо үүсгэхэд бэлэн биш байна.",
}

POSITIVE_LABELS = {
    "profitable": "Тайлант үед ашигтай ажилласан.",
    "positive_equity": "Өөрийн хөрөнгө эерэг байна.",
    "low_leverage": "Өр / хөрөнгийн харьцаа харьцангуй нам байна.",
    "current_ratio_above_1_5": "Эргэлтийн харьцаа 1.5-аас дээш байна.",
    "cash_balance_available": "Мөнгөн хөрөнгийн үлдэгдэл мэдээлэгдсэн байна.",
    "parser_confidence_high": "Өгөгдөл уншилтын итгэлцэл өндөр байна.",
}

QUESTION_LABELS = {
    "Please explain the reason for negative net profit.": "Цэвэр ашиг сөрөг гарсан шалтгааныг тайлбарлана уу.",
    "Please explain the negative equity position.": "Өөрийн хөрөнгө сөрөг болсон шалтгааныг тайлбарлана уу.",
    "Please provide a breakdown of liabilities and debt maturity.": "Өр төлбөрийн бүтэц болон хугацааны задаргааг ирүүлнэ үү.",
    "Please provide a breakdown of short-term liabilities.": "Богино хугацаат өр төлбөрийн задаргааг ирүүлнэ үү.",
    "Please provide bank statements to verify reported revenue.": "Борлуулалтын орлогыг баталгаажуулах банкны хуулгыг ирүүлнэ үү.",
    "Please provide cash and bank balance details.": "Мөнгөн хөрөнгө болон банкны үлдэгдлийн дэлгэрэнгүй мэдээллийг ирүүлнэ үү.",
    "Please provide the original signed/source financial statements for manual verification.": "Гарын үсэгтэй эх тайлан эсвэл эх баримтыг гараар тулган шалгуулахаар ирүүлнэ үү.",
    "Please confirm whether the submitted statements are final audited figures.": "Ирүүлсэн тайлан эцэслэсэн, аудитлагдсан дүн эсэхийг баталгаажуулна уу.",
}


def _field_value(extraction: dict[str, Any], field: str) -> int | float | None:
    for group in ("income_statement", "balance_sheet", "cash_flow"):
        values = extraction.get(group) or {}
        if field in values:
            value = values.get(field)
            return value if isinstance(value, int | float) else None
    return None


def _format_money(value: int | float | None, currency: str) -> str:
    if value is None:
        return "Мэдээлэл дутуу"
    if isinstance(value, float) and not value.is_integer():
        amount = f"{value:,.2f}"
    else:
        amount = f"{int(value):,}"
    return f"{amount} {currency if currency != 'unknown' else ''}".strip()


def _format_ratio(value: float | None) -> str:
    if value is None:
        return "Мэдээлэл дутуу"
    return f"{value:.2f}"


def _format_percent(value: float | None) -> str:
    if value is None:
        return "Мэдээлэл дутуу"
    return f"{value * 100:.1f}%"


def _period_label(extraction: dict[str, Any]) -> str:
    period = extraction.get("period") or {}
    if period.get("start_date") and period.get("end_date"):
        return f"{period['start_date']} - {period['end_date']}"
    if period.get("fiscal_year"):
        return str(period["fiscal_year"])
    if period.get("end_date"):
        return str(period["end_date"])
    return "Мэдээлэл дутуу"


def _company_name(metadata: dict[str, Any] | None) -> str:
    metadata = metadata or {}
    for key in ("company_name", "companyName", "borrower_name", "borrowerName", "name"):
        value = metadata.get(key)
        if value:
            return str(value)
    return "Мэдээлэл дутуу"


def _document_type(extraction: dict[str, Any]) -> str:
    document_type = extraction.get("document_type") or "unknown"
    labels = {
        "financial_statement": "Санхүүгийн тайлан",
        "bank_statement": "Банкны хуулга",
        "tax_report": "Татварын тайлан",
        "loan_contract": "Зээлийн гэрээ",
        "unknown": "Тодорхойгүй",
    }
    return labels.get(str(document_type), str(document_type))


def _data_quality_label(parser_audit: dict[str, Any]) -> str:
    score = float(parser_audit.get("overall_accuracy_score") or 0)
    if score >= 0.85:
        return "Өндөр"
    if score >= 0.65:
        return "Дунд"
    return "Нэмэлт шалгалт шаардлагатай"


def _translate_risk(flag: str) -> str:
    return RISK_LABELS.get(flag, flag.replace("_", " "))


def _translate_positive(signal: str) -> str:
    return POSITIVE_LABELS.get(signal, signal.replace("_", " "))


def _translate_question(question: str) -> str:
    return QUESTION_LABELS.get(question, question)


def _missing_required_fields(parser_audit: dict[str, Any]) -> list[str]:
    readiness = parser_audit.get("lender_insight_readiness") or {}
    reason = str(readiness.get("reason") or "")
    if "Missing minimum credit memo fields:" not in reason:
        return []
    return [part.strip().strip(".") for part in reason.split(":", 1)[1].split(",") if part.strip()]


def _conclusion(parser_audit: dict[str, Any], lender_insights: dict[str, Any]) -> str:
    readiness = parser_audit.get("lender_insight_readiness") or {}
    risk_flags = set(lender_insights.get("risk_flags") or [])
    positive_signals = set(lender_insights.get("positive_signals") or [])

    if not readiness.get("ready_for_credit_memo"):
        return "Нэмэлт баримт шаардлагатай. Одоогийн өгөгдлөөр зээлийн шийдвэрийг автоматаар дүгнэхгүй."
    if "high_leverage_debt_to_assets" in risk_flags or "negative_equity" in risk_flags:
        return "Өндөр эрсдэлтэй. Нэмэлт баталгаажуулалт, өр төлбөрийн задаргаа шаардлагатай."
    if "profitable" in positive_signals and "high_leverage_debt_to_assets" not in risk_flags:
        return "Цаашид судлах боломжтой. Гэхдээ банкны хуулга, татварын тайлангаар орлогыг тулган баталгаажуулах шаардлагатай."
    return "Нэмэлт баримт шаардлагатай. Санхүүгийн мэдээллийг гараар тулган шалгах нь зүйтэй."


def generate_credit_memo_markdown(
    borrower_metadata: dict[str, Any] | None,
    extraction: dict[str, Any],
    parser_audit: dict[str, Any],
    lender_insights: dict[str, Any],
) -> str:
    currency = extraction.get("currency") or "unknown"
    key_metrics = lender_insights.get("key_metrics") or {}
    risk_flags = lender_insights.get("risk_flags") or []
    positive_signals = lender_insights.get("positive_signals") or []
    questions = lender_insights.get("questions_for_borrower") or []
    manual_review_fields = parser_audit.get("recommended_manual_review_fields") or []
    missing_required = _missing_required_fields(parser_audit)

    financial_rows = [
        ("Борлуулалтын орлого", _field_value(extraction, "revenue")),
        ("Цэвэр ашиг", _field_value(extraction, "net_profit")),
        ("Нийт хөрөнгө", _field_value(extraction, "total_assets")),
        ("Нийт өр төлбөр", _field_value(extraction, "total_liabilities")),
        ("Өөрийн хөрөнгө", _field_value(extraction, "equity")),
        ("Мөнгөн хөрөнгө", _field_value(extraction, "cash")),
    ]
    ratio_rows = [
        ("Цэвэр ашгийн маржин", _format_percent(key_metrics.get("net_margin"))),
        ("Өр / хөрөнгийн харьцаа", _format_ratio(key_metrics.get("debt_to_assets"))),
        ("Өр / өөрийн хөрөнгийн харьцаа", _format_ratio(key_metrics.get("debt_to_equity"))),
        ("Эргэлтийн харьцаа", _format_ratio(key_metrics.get("current_ratio"))),
        ("Өөрийн хөрөнгийн харьцаа", _format_ratio(key_metrics.get("equity_ratio"))),
    ]

    lines = [
        "# Зээлийн шинжилгээний товч мемо",
        "",
        "## 1. Зээл хүсэгчийн товч мэдээлэл",
        f"- Компанийн нэр: {_company_name(borrower_metadata)}",
        f"- Тайлангийн хугацаа: {_period_label(extraction)}",
        f"- Валют: {currency if currency != 'unknown' else 'Мэдээлэл дутуу'}",
        f"- Баримтын төрөл: {_document_type(extraction)}",
        f"- Өгөгдлийн чанарын үнэлгээ: {_data_quality_label(parser_audit)}",
        "",
        "> Өгөгдлийн чанар",
        f"> - Нийт үнэлгээ: {float(parser_audit.get('overall_accuracy_score') or 0):.2f}",
        f"> - Гараар шалгах талбарууд: {', '.join(manual_review_fields) if manual_review_fields else 'Байхгүй'}",
        f"> - Дутуу шаардлагатай талбарууд: {', '.join(missing_required) if missing_required else 'Байхгүй'}",
        "",
        "## 2. Санхүүгийн гол үзүүлэлтүүд",
        "",
        "| Үзүүлэлт | Дүн |",
        "| --- | ---: |",
    ]

    for label, value in financial_rows:
        lines.append(f"| {label} | {_format_money(value, currency)} |")

    lines.extend(
        [
            "",
            "## 3. Гол харьцаа үзүүлэлтүүд",
            "",
            "| Харьцаа | Дүн |",
            "| --- | ---: |",
        ]
    )
    for label, value in ratio_rows:
        lines.append(f"| {label} | {value} |")

    lines.extend(["", "## 4. Эерэг дохио"])
    lines.extend([f"- {_translate_positive(signal)}" for signal in positive_signals] or ["- Одоогоор тодорхой эерэг дохио илрээгүй."])

    lines.extend(["", "## 5. Эрсдэлийн дохио"])
    lines.extend([f"- {_translate_risk(flag)}" for flag in risk_flags] or ["- Томоохон эрсдэлийн дохио илрээгүй."])

    lines.extend(["", "## 6. Зээл олгохоос өмнө тодруулах асуултууд"])
    lines.extend([f"- {_translate_question(question)}" for question in questions] or ["- Нэмэлт асуулт одоогоор алга."])

    lines.extend(
        [
            "",
            "## 7. Урьдчилсан дүгнэлт",
            _conclusion(parser_audit, lender_insights),
            "",
            "_Энэ мемо нь урьдчилсан шинжилгээний зориулалттай. Зээл олгох шийдвэрийг автоматаар гаргаагүй._",
        ]
    )

    return "\n".join(lines)
