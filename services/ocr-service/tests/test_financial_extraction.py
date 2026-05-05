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


def parsed_document_with_text(text: str, document_type: str = "unknown") -> dict:
    return {
        "parserResult": {
            "document_id": "test",
            "document_type": document_type,
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
        self.assertEqual(map_label_to_field("богино хугацаат өр төлбөр").field, "short_term_debt")

    def test_parentheses_parse_as_negative(self) -> None:
        parsed = parse_number("(1,250,000)", "")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.value, -1_250_000)

    def test_scale_detection_for_millions(self) -> None:
        parsed = parse_number("125", "сая төгрөг")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.value, 125_000_000)

    def test_extracts_real_cyrillic_financial_statement_fields(self) -> None:
        text = """
        Санхүүгийн тайлан 2024
        Орлогын тайлан
        Борлуулалтын орлого: 100,000,000 төгрөг
        Нийт ашиг: 40,000,000 төгрөг
        Үйл ажиллагааны зардал: 12,000,000 төгрөг
        Үйл ажиллагааны ашиг: 28,000,000 төгрөг
        Цэвэр ашиг: 20,000,000 төгрөг
        Баланс
        Нийт хөрөнгө: 150,000,000 төгрөг
        Эргэлтийн хөрөнгө: 80,000,000 төгрөг
        Мөнгөн хөрөнгө: 30,000,000 төгрөг
        Бараа материал: 15,000,000 төгрөг
        Авлага: 20,000,000 төгрөг
        Нийт өр төлбөр: 60,000,000 төгрөг
        Богино хугацаат өр төлбөр: 25,000,000 төгрөг
        Урт хугацаат өр төлбөр: 35,000,000 төгрөг
        Өөрийн хөрөнгө: 90,000,000 төгрөг
        Үйл ажиллагааны мөнгөн гүйлгээ: 18,000,000 төгрөг
        Хөрөнгө оруулалтын мөнгөн гүйлгээ: (5,000,000) төгрөг
        Санхүүгийн мөнгөн гүйлгээ: 3,000,000 төгрөг
        Эцсийн мөнгөн хөрөнгө: 30,000,000 төгрөг
        """
        result = extract_financial_statement(parsed_document_with_text(text))

        self.assertEqual(result["document_type"], "financial_statement")
        self.assertEqual(result["currency"], "MNT")
        self.assertEqual(result["income_statement"]["revenue"], 100_000_000)
        self.assertEqual(result["income_statement"]["net_profit"], 20_000_000)
        self.assertEqual(result["balance_sheet"]["total_assets"], 150_000_000)
        self.assertEqual(result["balance_sheet"]["cash"], 30_000_000)
        self.assertEqual(result["balance_sheet"]["total_liabilities"], 60_000_000)
        self.assertEqual(result["balance_sheet"]["equity"], 90_000_000)
        self.assertEqual(result["cash_flow"]["investing_cash_flow"], -5_000_000)
        self.assertNotIn("revenue", result["missing_fields"])
        self.assertNotIn("equity", result["missing_fields"])

    def test_parser_financial_statement_hint_allows_extraction(self) -> None:
        text = "Борлуулалтын орлого: 10,000\nЦэвэр ашиг: 1,000\nНийт хөрөнгө: 20,000"
        result = extract_financial_statement(parsed_document_with_text(text, document_type="financial_statement"))

        self.assertEqual(result["document_type"], "financial_statement")
        self.assertEqual(result["income_statement"]["revenue"], 10_000)

    def test_extracts_when_label_and_value_are_split_across_lines(self) -> None:
        text = """
        Борлуулалтын орлого
        10,000,000
        Цэвэр ашиг
        1,500,000
        Нийт хөрөнгө
        25,000,000
        Нийт өр төлбөр
        8,000,000
        Өөрийн хөрөнгө
        17,000,000
        """
        result = extract_financial_statement(parsed_document_with_text(text))

        self.assertEqual(result["document_type"], "financial_statement")
        self.assertEqual(result["income_statement"]["revenue"], 10_000_000)
        self.assertEqual(result["income_statement"]["net_profit"], 1_500_000)
        self.assertEqual(result["balance_sheet"]["equity"], 17_000_000)

    def test_extracts_table_label_when_not_first_cell(self) -> None:
        document = {
            "parserResult": {
                "document_id": "table-offset",
                "document_type": "unknown",
                "pages": [
                    {
                        "page_number": 1,
                        "strategy": "digital",
                        "text_blocks": [],
                        "tables": [
                            {
                                "rows": [
                                    ["1", "Борлуулалтын орлого", "2024", "15,000,000"],
                                    ["2", "Нийт хөрөнгө", "2024", "40,000,000"],
                                    ["3", "Нийт өр төлбөр", "2024", "10,000,000"],
                                ],
                                "columns": [],
                            }
                        ],
                        "raw_text": "Санхүүгийн тайлан",
                        "confidence": 0.9,
                    }
                ],
                "global_warnings": [],
                "parser_version": "hybrid-v1",
            }
        }
        result = extract_financial_statement(document)

        self.assertEqual(result["document_type"], "financial_statement")
        self.assertEqual(result["income_statement"]["revenue"], 15_000_000)
        self.assertEqual(result["balance_sheet"]["total_assets"], 40_000_000)
        self.assertEqual(result["balance_sheet"]["total_liabilities"], 10_000_000)

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
            "санхүүгийн тайлан баланс хөрөнгө өр төлбөр орлого цэвэр ашиг мөнгөн гүйлгээ"
        )
        self.assertEqual(classification.document_type, "financial_statement")
        self.assertGreater(classification.confidence, 0.7)


if __name__ == "__main__":
    unittest.main()
