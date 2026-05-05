from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from financial.classifier import classify_financial_document
from financial.label_mapping import map_label_to_field
from financial.numbers import parse_number
from financial.statement_extractor import extract_financial_statement


def parsed_document_with_text(text: str) -> dict:
    return {
        "parserResult": {
            "document_id": "test",
            "document_type": "unknown",
            "pages": [
                {
                    "page_number": 1,
                    "strategy": "digital",
                    "text_blocks": [],
                    "tables": [],
                    "raw_text": text,
                    "confidence": 0.9,
                    "warnings": [],
                }
            ],
            "global_warnings": [],
            "parser_version": "hybrid-v1",
        },
        "pages": [{"pageNumber": 1, "text": text, "confidence": 0.9}],
    }


class FinancialExtractionTests(unittest.TestCase):
    def test_mongolian_labels_map_correctly(self) -> None:
        self.assertEqual(map_label_to_field("борлуулалтын орлого").field, "revenue")
        self.assertEqual(map_label_to_field("нийт хөрөнгө").field, "total_assets")
        self.assertEqual(map_label_to_field("цэвэр ашиг").field, "net_profit")
        self.assertEqual(map_label_to_field("мөнгөн хөрөнгө").field, "cash")

    def test_parentheses_parse_as_negative(self) -> None:
        parsed = parse_number("(1,250,000)", "")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.value, -1_250_000)

    def test_scale_detection_for_millions(self) -> None:
        parsed = parse_number("125", "сая төгрөг")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.value, 125_000_000)

    def test_missing_values_are_listed(self) -> None:
        text = """
        Баланс
        Орлогын тайлан
        Нийт хөрөнгө: 50,000,000 MNT
        Нийт өр төлбөр: 20,000,000 MNT
        """
        result = extract_financial_statement(parsed_document_with_text(text))
        self.assertEqual(result["document_type"], "financial_statement")
        self.assertEqual(result["balance_sheet"]["total_assets"], 50_000_000)
        self.assertIn("revenue", result["missing_fields"])
        self.assertIn("net_profit", result["missing_fields"])

    def test_extracted_values_include_source_references(self) -> None:
        document = {
            "parserResult": {
                "document_id": "table-test",
                "document_type": "unknown",
                "pages": [
                    {
                        "page_number": 2,
                        "strategy": "digital",
                        "text_blocks": [],
                        "tables": [
                            {
                                "page_number": 2,
                                "rows": [["Цэвэр ашиг", "12,500,000"]],
                                "columns": [],
                                "bbox": None,
                                "confidence": None,
                                "source": "pdfplumber",
                            }
                        ],
                        "raw_text": "Орлогын тайлан\nБаланс\nМөнгөн гүйлгээ\nЦэвэр ашиг 12,500,000 MNT\nНийт хөрөнгө 20,000,000 MNT",
                        "confidence": 0.9,
                        "warnings": [],
                    }
                ],
                "global_warnings": [],
                "parser_version": "hybrid-v1",
            }
        }
        result = extract_financial_statement(document)
        reference = next(item for item in result["source_references"] if item["field"] == "net_profit")
        self.assertEqual(reference["page_number"], 2)
        self.assertEqual(reference["source"], "table")
        self.assertEqual(reference["raw_label"], "Цэвэр ашиг")
        self.assertEqual(reference["value"], 12_500_000)

    def test_unknown_document_does_not_crash(self) -> None:
        result = extract_financial_statement(parsed_document_with_text("Hello this is not a financial report."))
        self.assertEqual(result["document_type"], "unknown")
        self.assertIn("revenue", result["missing_fields"])
        self.assertEqual(result["source_references"], [])

    def test_classifier_detects_financial_statement(self) -> None:
        classification = classify_financial_document(
            "balance sheet assets liabilities equity revenue net profit cash flow"
        )
        self.assertEqual(classification.document_type, "financial_statement")
        self.assertGreater(classification.confidence, 0.7)


if __name__ == "__main__":
    unittest.main()
