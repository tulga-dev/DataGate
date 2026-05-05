from __future__ import annotations

import re
from dataclasses import dataclass


MONGOLIAN_ACCOUNTING_LABELS: dict[str, str] = {
    "борлуулалтын орлого": "revenue",
    "нийт борлуулалтын орлого": "revenue",
    "борлуулалт": "revenue",
    "орлого": "revenue",
    "үндсэн үйл ажиллагааны орлого": "revenue",
    "борлуулсан бүтээгдэхүүний өртөг": "cost_of_goods_sold",
    "борлуулалтын өртөг": "cost_of_goods_sold",
    "борлуулсан барааны өртөг": "cost_of_goods_sold",
    "нийт ашиг": "gross_profit",
    "бохир ашиг": "gross_profit",
    "үйл ажиллагааны зардал": "operating_expenses",
    "удирдлагын зардал": "operating_expenses",
    "ерөнхий ба удирдлагын зардал": "operating_expenses",
    "үйл ажиллагааны ашиг": "operating_profit",
    "цэвэр ашиг": "net_profit",
    "тайлант үеийн цэвэр ашиг": "net_profit",
    "татварын дараах ашиг": "net_profit",
    "алдагдал": "net_profit",
    "нийт хөрөнгө": "total_assets",
    "хөрөнгийн дүн": "total_assets",
    "хөрөнгө нийт": "total_assets",
    "эргэлтийн хөрөнгө": "current_assets",
    "мөнгөн хөрөнгө": "cash",
    "мөнгө ба түүнтэй адилтгах хөрөнгө": "cash",
    "касс дахь мөнгө": "cash",
    "банкин дахь мөнгө": "cash",
    "бараа материал": "inventory",
    "бараа материалын үлдэгдэл": "inventory",
    "авлага": "receivables",
    "дансны авлага": "receivables",
    "худалдааны авлага": "receivables",
    "нийт өр төлбөр": "total_liabilities",
    "өр төлбөрийн дүн": "total_liabilities",
    "өр төлбөр": "total_liabilities",
    "богино хугацаат өр төлбөр": "short_term_debt",
    "богино хугацаат зээл": "short_term_debt",
    "урт хугацаат өр төлбөр": "long_term_debt",
    "урт хугацаат зээл": "long_term_debt",
    "эзний өмч": "equity",
    "өөрийн хөрөнгө": "equity",
    "эздийн өмч": "equity",
    "хуримтлагдсан ашиг": "equity",
    "үйл ажиллагааны мөнгөн гүйлгээ": "operating_cash_flow",
    "үндсэн үйл ажиллагааны мөнгөн гүйлгээ": "operating_cash_flow",
    "хөрөнгө оруулалтын мөнгөн гүйлгээ": "investing_cash_flow",
    "санхүүгийн мөнгөн гүйлгээ": "financing_cash_flow",
    "эцсийн мөнгөн хөрөнгө": "ending_cash",
    "мөнгөн хөрөнгийн эцсийн үлдэгдэл": "ending_cash",
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
    lowered = re.sub(r"^[\d.\-)()\s]+", "", lowered)
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
