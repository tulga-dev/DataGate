from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from financial.parser_audit import audit_financial_extraction


def parsed_document(text: str = "Financial statement 2025") -> dict:
    return {
        "parserResult": {
            "document_id": "audit-test",
            "document_type": "financial_statement",
            "pages": [
                {
                    "page_number": 1,
                    "raw_text": text,
                    "tables": [],
                    "confidence": 0.9,
                }
            ],
            "global_warnings": [],
            "parser_version": "hybrid-v1",
        }
    }


def extraction(
    *,
    revenue: int | None = 1000,
    net_profit: int | None = 100,
    total_assets: int | None = 1000,
    total_liabilities: int | None = 400,
    equity: int | None = 600,
    fiscal_year: int | None = 2025,
    references: list[dict] | None = None,
) -> dict:
    values = {
        "revenue": revenue,
        "net_profit": net_profit,
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "equity": equity,
    }
    source_references = references
    if source_references is None:
        source_references = [
            {
                "field": field,
                "value": value,
                "raw_value": str(value),
                "page_number": 1,
                "source": "table",
                "raw_label": field,
                "confidence": 0.9,
            }
            for field, value in values.items()
            if value is not None
        ]

    return {
        "period": {"start_date": None, "end_date": None, "fiscal_year": fiscal_year},
        "currency": "MNT",
        "income_statement": {
            "revenue": revenue,
            "cost_of_goods_sold": None,
            "gross_profit": None,
            "operating_expenses": None,
            "operating_profit": None,
            "net_profit": net_profit,
        },
        "balance_sheet": {
            "total_assets": total_assets,
            "current_assets": None,
            "cash": None,
            "inventory": None,
            "receivables": None,
            "total_liabilities": total_liabilities,
            "short_term_debt": None,
            "long_term_debt": None,
            "equity": equity,
        },
        "cash_flow": {
            "operating_cash_flow": None,
            "investing_cash_flow": None,
            "financing_cash_flow": None,
            "ending_cash": None,
        },
        "extraction_confidence": {reference["field"]: reference["confidence"] for reference in source_references},
        "missing_fields": [],
        "source_references": source_references,
    }


class ParserAuditTests(unittest.TestCase):
    def test_valid_balance_sheet_passes(self) -> None:
        report = audit_financial_extraction(parsed_document(), extraction())
        self.assertEqual(report["red_flags"], [])
        self.assertTrue(report["lender_insight_readiness"]["ready_for_credit_memo"])
        self.assertGreater(report["overall_accuracy_score"], 0.8)

    def test_broken_balance_sheet_gets_red_flag(self) -> None:
        report = audit_financial_extraction(parsed_document(), extraction(total_assets=900, total_liabilities=500, equity=600))
        self.assertIn("balance_sheet_mismatch", " ".join(report["red_flags"]))
        self.assertIn("total_assets", report["recommended_manual_review_fields"])
        self.assertFalse(report["lender_insight_readiness"]["ready_for_credit_memo"])

    def test_missing_required_fields_makes_credit_memo_not_ready(self) -> None:
        report = audit_financial_extraction(parsed_document(), extraction(revenue=None, fiscal_year=None))
        self.assertFalse(report["lender_insight_readiness"]["ready_for_credit_memo"])
        self.assertFalse(report["lender_insight_readiness"]["minimum_required_fields_present"])
        self.assertIn("revenue", report["recommended_manual_review_fields"])

    def test_conflicting_values_trigger_manual_review(self) -> None:
        refs = [
            {
                "field": "revenue",
                "value": 1000,
                "raw_value": "1000",
                "page_number": 1,
                "source": "table",
                "raw_label": "revenue",
                "confidence": 0.9,
            },
            {
                "field": "revenue",
                "value": 2000,
                "raw_value": "2000",
                "page_number": 2,
                "source": "table",
                "raw_label": "revenue",
                "confidence": 0.85,
            },
            *[
                {
                    "field": field,
                    "value": value,
                    "raw_value": str(value),
                    "page_number": 1,
                    "source": "table",
                    "raw_label": field,
                    "confidence": 0.9,
                }
                for field, value in {
                    "net_profit": 100,
                    "total_assets": 1000,
                    "total_liabilities": 400,
                    "equity": 600,
                }.items()
            ],
        ]
        report = audit_financial_extraction(parsed_document(), extraction(references=refs))
        revenue_score = next(item for item in report["field_scores"] if item["field"] == "revenue")
        self.assertIn("conflicting_values_across_sources", revenue_score["issues"])
        self.assertIn("revenue", report["recommended_manual_review_fields"])

    def test_lender_flags_profit_loss_conflict_and_liabilities(self) -> None:
        report = audit_financial_extraction(
            parsed_document("The company reported a loss and алдагдал in 2025."),
            extraction(net_profit=100, total_assets=1000, total_liabilities=1200, equity=-200),
        )
        joined = " ".join(report["red_flags"])
        self.assertIn("profit_sign_conflict", joined)
        self.assertIn("liabilities_exceed_assets", joined)

    def test_historical_reference_year_does_not_trigger_period_conflict(self) -> None:
        report = audit_financial_extraction(
            parsed_document("Financial statement 2024. Company certificate reference year 1917."),
            extraction(fiscal_year=2024),
        )
        self.assertFalse(any("period_conflict" in warning for warning in report["warnings"]))

    def test_multiple_recent_reporting_years_still_trigger_period_conflict(self) -> None:
        report = audit_financial_extraction(
            parsed_document("Financial statement includes 2024, 2023, and 2022 comparative columns."),
            extraction(fiscal_year=None),
        )
        self.assertTrue(any("period_conflict" in warning for warning in report["warnings"]))

    def test_non_period_date_years_do_not_trigger_period_conflict(self) -> None:
        report = audit_financial_extraction(
            parsed_document("Loan opened 2021. Statement year 2024. Contract date 2025. Maturity 2028."),
            extraction(fiscal_year=2024),
        )
        self.assertFalse(any("period_conflict" in warning for warning in report["warnings"]))


if __name__ == "__main__":
    unittest.main()
