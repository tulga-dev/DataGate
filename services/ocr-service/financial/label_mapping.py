from __future__ import annotations

import re
from dataclasses import dataclass


MONGOLIAN_ACCOUNTING_LABELS: dict[str, str] = {
    "борлуулалтын орлого": "revenue",
    "нийт борлуулалтын орлого": "revenue",
    "орлого": "revenue",
    "борлуулсан бүтээгдэхүүний өртөг": "cost_of_goods_sold",
    "борлуулалтын өртөг": "cost_of_goods_sold",
    "нийт ашиг": "gross_profit",
    "үйл ажиллагааны зардал": "operating_expenses",
    "үйл ажиллагааны ашиг": "operating_profit",
    "цэвэр ашиг": "net_profit",
    "тайлант үеийн цэвэр ашиг": "net_profit",
    "алдагдал": "net_profit",
    "нийт хөрөнгө": "total_assets",
    "эргэлтийн хөрөнгө": "current_assets",
    "мөнгөн хөрөнгө": "cash",
    "мөнгө ба түүнтэй адилтгах хөрөнгө": "cash",
    "бараа материал": "inventory",
    "авлага": "receivables",
    "дансны авлага": "receivables",
    "нийт өр төлбөр": "total_liabilities",
    "өр төлбөр": "total_liabilities",
    "богино хугацаат өр": "short_term_debt",
    "богино хугацаат өр төлбөр": "short_term_debt",
    "урт хугацаат өр": "long_term_debt",
    "урт хугацаат өр төлбөр": "long_term_debt",
    "эзний өмч": "equity",
    "өөрийн хөрөнгө": "equity",
    "үйл ажиллагааны мөнгөн гүйлгээ": "operating_cash_flow",
    "хөрөнгө оруулалтын мөнгөн гүйлгээ": "investing_cash_flow",
    "санхүүгийн мөнгөн гүйлгээ": "financing_cash_flow",
    "эцсийн мөнгөн хөрөнгө": "ending_cash",
}

ENGLISH_ACCOUNTING_LABELS: dict[str, str] = {
    "revenue": "revenue",
    "sales revenue": "revenue",
    "net sales": "revenue",
    "cost of goods sold": "cost_of_goods_sold",
    "cost of sales": "cost_of_goods_sold",
    "gross profit": "gross_profit",
    "operating expenses": "operating_expenses",
    "operating profit": "operating_profit",
    "operating income": "operating_profit",
    "net profit": "net_profit",
    "net income": "net_profit",
    "total assets": "total_assets",
    "current assets": "current_assets",
    "cash": "cash",
    "cash and cash equivalents": "cash",
    "inventory": "inventory",
    "receivables": "receivables",
    "accounts receivable": "receivables",
    "total liabilities": "total_liabilities",
    "short term debt": "short_term_debt",
    "short-term debt": "short_term_debt",
    "long term debt": "long_term_debt",
    "long-term debt": "long_term_debt",
    "equity": "equity",
    "owner equity": "equity",
    "operating cash flow": "operating_cash_flow",
    "cash flow from operations": "operating_cash_flow",
    "investing cash flow": "investing_cash_flow",
    "financing cash flow": "financing_cash_flow",
    "ending cash": "ending_cash",
}

ACCOUNTING_LABELS = {
    **MONGOLIAN_ACCOUNTING_LABELS,
    **ENGLISH_ACCOUNTING_LABELS,
}


@dataclass(frozen=True)
class LabelMatch:
    field: str
    raw_label: str
    confidence: float


def normalize_label(label: str) -> str:
    lowered = label.lower().strip()
    lowered = re.sub(r"[:：]+$", "", lowered)
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered


def map_label_to_field(label: str) -> LabelMatch | None:
    normalized = normalize_label(label)
    if normalized in ACCOUNTING_LABELS:
        return LabelMatch(field=ACCOUNTING_LABELS[normalized], raw_label=label.strip(), confidence=0.94)

    for known_label, field in ACCOUNTING_LABELS.items():
        if known_label in normalized:
            return LabelMatch(field=field, raw_label=label.strip(), confidence=0.82)
        if normalized in known_label and len(normalized) >= 5:
            return LabelMatch(field=field, raw_label=label.strip(), confidence=0.72)

    return None


def all_schema_fields() -> list[str]:
    return [
        "revenue",
        "cost_of_goods_sold",
        "gross_profit",
        "operating_expenses",
        "operating_profit",
        "net_profit",
        "total_assets",
        "current_assets",
        "cash",
        "inventory",
        "receivables",
        "total_liabilities",
        "short_term_debt",
        "long_term_debt",
        "equity",
        "operating_cash_flow",
        "investing_cash_flow",
        "financing_cash_flow",
        "ending_cash",
    ]
