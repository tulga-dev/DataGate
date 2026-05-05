from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from financial.lender_insights import generate_lender_insights


def extraction(**overrides):
    data = {
        "period": {"start_date": None, "end_date": None, "fiscal_year": 2025},
        "currency": "MNT",
        "income_statement": {
            "revenue": 1000,
            "cost_of_goods_sold": None,
            "gross_profit": 400,
            "operating_expenses": None,
            "operating_profit": None,
            "net_profit": 100,
        },
        "balance_sheet": {
            "total_assets": 1000,
            "current_assets": 300,
            "cash": 80,
            "inventory": None,
            "receivables": None,
            "total_liabilities": 400,
            "short_term_debt": 150,
            "long_term_debt": None,
            "equity": 600,
        },
        "cash_flow": {
            "operating_cash_flow": None,
            "investing_cash_flow": None,
            "financing_cash_flow": None,
            "ending_cash": None,
        },
    }
    for group, values in overrides.items():
        if group in data and isinstance(data[group], dict) and isinstance(values, dict):
            data[group].update(values)
        else:
            data[group] = values
    return data


def audit(score=0.91, ready=True):
    return {
        "overall_accuracy_score": score,
        "red_flags": [],
        "warnings": [],
        "recommended_manual_review_fields": [],
        "lender_insight_readiness": {
            "ready_for_credit_memo": ready,
            "minimum_required_fields_present": ready,
            "reason": "ok" if ready else "not ready",
        },
    }


class LenderInsightTests(unittest.TestCase):
    def test_ratios_calculate_correctly(self) -> None:
        result = generate_lender_insights(extraction(), audit())
        metrics = result["key_metrics"]
        self.assertEqual(metrics["gross_margin"], 0.4)
        self.assertEqual(metrics["net_margin"], 0.1)
        self.assertEqual(metrics["debt_to_assets"], 0.4)
        self.assertEqual(metrics["debt_to_equity"], 0.6667)
        self.assertEqual(metrics["current_ratio"], 2.0)
        self.assertEqual(metrics["return_on_assets"], 0.1)
        self.assertEqual(metrics["equity_ratio"], 0.6)

    def test_division_by_zero_does_not_crash(self) -> None:
        result = generate_lender_insights(
            extraction(
                income_statement={"revenue": 0},
                balance_sheet={"total_assets": 0, "short_term_debt": 0, "equity": 0},
            ),
            audit(),
        )
        self.assertIsNone(result["key_metrics"]["net_margin"])
        self.assertIsNone(result["key_metrics"]["debt_to_assets"])
        self.assertIsNone(result["key_metrics"]["current_ratio"])

    def test_missing_fields_produce_questions(self) -> None:
        result = generate_lender_insights(
            extraction(income_statement={"revenue": None}, balance_sheet={"cash": None}),
            audit(ready=False),
        )
        self.assertIn("missing_revenue", result["risk_flags"])
        self.assertIn("missing_cash", result["risk_flags"])
        joined_questions = " ".join(result["questions_for_borrower"])
        self.assertIn("bank statements", joined_questions)
        self.assertIn("cash", joined_questions.lower())

    def test_high_leverage_produces_risk_flag(self) -> None:
        result = generate_lender_insights(
            extraction(balance_sheet={"total_liabilities": 800, "total_assets": 1000, "equity": 200}),
            audit(),
        )
        self.assertIn("high_leverage_debt_to_assets", result["risk_flags"])
        self.assertIn("breakdown of liabilities", " ".join(result["questions_for_borrower"]))

    def test_low_parser_confidence_blocks_automatic_recommendation(self) -> None:
        result = generate_lender_insights(extraction(), audit(score=0.42, ready=False))
        self.assertIn("low_parser_confidence", result["risk_flags"])
        self.assertIn("document_not_ready_for_memo", result["risk_flags"])
        self.assertFalse(result["credit_memo_inputs"]["data_quality"]["ready_for_credit_memo"])
        self.assertIn("manual review", " ".join(result["credit_memo_inputs"]["recommended_next_steps"]))

    def test_positive_signals_are_deterministic(self) -> None:
        result = generate_lender_insights(extraction(), audit(score=0.9, ready=True))
        self.assertIn("profitable", result["positive_signals"])
        self.assertIn("positive_equity", result["positive_signals"])
        self.assertIn("low_leverage", result["positive_signals"])
        self.assertIn("current_ratio_above_1_5", result["positive_signals"])
        self.assertIn("cash_balance_available", result["positive_signals"])
        self.assertIn("parser_confidence_high", result["positive_signals"])


if __name__ == "__main__":
    unittest.main()
