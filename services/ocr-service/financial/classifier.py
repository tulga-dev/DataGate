from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FinancialDocumentClassification:
    document_type: str
    confidence: float
    reasons: list[str] = field(default_factory=list)


SIGNALS = {
    "financial_statement": [
        "balance sheet",
        "income statement",
        "cash flow",
        "assets",
        "liabilities",
        "equity",
        "revenue",
        "net profit",
        "баланс",
        "орлого",
        "зарлага",
        "ашиг",
        "алдагдал",
        "хөрөнгө",
        "өр төлбөр",
        "эзний өмч",
        "мөнгөн гүйлгээ",
    ],
    "bank_statement": ["bank statement", "account statement", "transaction", "дансны хуулга", "гүйлгээ"],
    "tax_report": ["tax report", "vat", "tax", "татвар", "нөат"],
    "loan_contract": ["loan agreement", "loan contract", "borrower", "lender", "зээлийн гэрээ", "зээлдэгч"],
}


def classify_financial_document(text: str) -> FinancialDocumentClassification:
    normalized = text.lower()
    scores: dict[str, list[str]] = {}

    for document_type, terms in SIGNALS.items():
        hits = [term for term in terms if term.lower() in normalized]
        scores[document_type] = hits

    best_type = "unknown"
    best_hits: list[str] = []
    for document_type, hits in scores.items():
        if len(hits) > len(best_hits):
            best_type = document_type
            best_hits = hits

    if not best_hits:
        return FinancialDocumentClassification(
            document_type="unknown",
            confidence=0.24,
            reasons=["No financial document signals matched."],
        )

    confidence = min(0.94, 0.38 + len(best_hits) * 0.08)
    if best_type == "financial_statement" and len(best_hits) >= 4:
        confidence = min(0.96, confidence + 0.12)

    return FinancialDocumentClassification(
        document_type=best_type,
        confidence=confidence,
        reasons=[f"Matched signals: {', '.join(best_hits[:8])}"],
    )
