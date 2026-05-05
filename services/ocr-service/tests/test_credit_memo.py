from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from financial.credit_memo import generate_credit_memo_markdown


def extraction(**overrides):
    data = {
        "document_type": "financial_statement",
        "period": {"start_date": None, "end_date": None, "fiscal_year": 2025},
        "currency": "MNT",
        "income_statement": {
            "revenue": 1_000_000,
            "cost_of_goods_sold": None,
            "gross_profit": 400_000,
            "operating_expenses": None,
            "operating_profit": None,
            "net_profit": 100_000,
        },
        "balance_sheet": {
            "total_assets": 2_000_000,
            "current_assets": 600_000,
            "cash": 150_000,
            "inventory": None,
            "receivables": None,
            "total_liabilities": 800_000,
            "short_term_debt": 300_000,
            "long_term_debt": None,
            "equity": 1_200_000,
        },
        "cash_flow": {},
    }
    for group, values in overrides.items():
        if group in data and isinstance(data[group], dict) and isinstance(values, dict):
            data[group].update(values)
        else:
            data[group] = values
    return data


def audit(score=0.91, ready=True, manual_fields=None, reason="ok"):
    return {
        "overall_accuracy_score": score,
        "recommended_manual_review_fields": manual_fields or [],
        "lender_insight_readiness": {
            "ready_for_credit_memo": ready,
            "minimum_required_fields_present": ready,
            "reason": reason,
        },
    }


def insights(risk_flags=None, positive_signals=None, questions=None, ready=True):
    return {
        "key_metrics": {
            "net_margin": 0.1,
            "debt_to_assets": 0.4,
            "debt_to_equity": 0.6667,
            "current_ratio": 2.0,
            "equity_ratio": 0.6,
        },
        "risk_flags": risk_flags or [],
        "positive_signals": positive_signals or ["profitable", "positive_equity", "low_leverage"],
        "questions_for_borrower": questions or ["Please confirm whether the submitted statements are final audited figures."],
        "credit_memo_inputs": {
            "data_quality": {"ready_for_credit_memo": ready},
        },
    }


class CreditMemoTests(unittest.TestCase):
    def test_memo_generated_with_missing_fields(self) -> None:
        memo = generate_credit_memo_markdown(
            {"company_name": "Алтан Трейд ХХК"},
            extraction(income_statement={"revenue": None}, balance_sheet={"cash": None}),
            audit(
                ready=False,
                manual_fields=["revenue"],
                reason="Missing minimum credit memo fields: revenue.",
            ),
            insights(risk_flags=["missing_revenue"], ready=False),
        )
        self.assertIn("# Зээлийн шинжилгээний товч мемо", memo)
        self.assertIn("Алтан Трейд ХХК", memo)
        self.assertIn("Мэдээлэл дутуу", memo)
        self.assertIn("Нэмэлт баримт шаардлагатай", memo)

    def test_memo_does_not_include_raw_ocr_text(self) -> None:
        memo = generate_credit_memo_markdown(
            {"company_name": "Test LLC", "raw_ocr_text": "SECRET OCR RAW TEXT"},
            extraction(),
            audit(),
            insights(),
        )
        self.assertNotIn("SECRET OCR RAW TEXT", memo)
        self.assertNotIn("raw OCR", memo.lower())
        self.assertNotIn("parser log", memo.lower())

    def test_high_leverage_conclusion(self) -> None:
        memo = generate_credit_memo_markdown(
            {},
            extraction(),
            audit(ready=True),
            insights(risk_flags=["high_leverage_debt_to_assets"], positive_signals=["profitable"], ready=True),
        )
        self.assertIn("Өндөр эрсдэлтэй", memo)
        self.assertNotIn("approve", memo.lower())

    def test_profitable_moderate_leverage_conclusion(self) -> None:
        memo = generate_credit_memo_markdown(
            {},
            extraction(),
            audit(ready=True),
            insights(risk_flags=[], positive_signals=["profitable", "positive_equity"], ready=True),
        )
        self.assertIn("Цаашид судлах боломжтой", memo)
        self.assertNotIn("approve", memo.lower())

    def test_mongolian_labels_render_correctly(self) -> None:
        memo = generate_credit_memo_markdown({}, extraction(), audit(), insights())
        self.assertIn("Борлуулалтын орлого", memo)
        self.assertIn("Цэвэр ашиг", memo)
        self.assertIn("Өр / хөрөнгийн харьцаа", memo)
        self.assertIn("Эерэг дохио", memo)


if __name__ == "__main__":
    unittest.main()
