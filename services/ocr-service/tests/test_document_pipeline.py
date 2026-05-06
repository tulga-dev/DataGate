from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from document_pipeline import (
    credit_memo_payload,
    financial_analysis_payload,
    full_pipeline_payload,
    get_document,
    run_document_pipeline,
    run_text_pipeline,
)
from main import default_ocr_engine, _selected_engine
from normalize import NormalizedPage, normalize_ocr_response


FINANCIAL_TEXT = """
Financial statement 2025
Balance sheet and income statement
Revenue: 1,000,000 MNT
Gross profit: 400,000 MNT
Net profit: 100,000 MNT
Total assets: 900,000 MNT
Current assets: 500,000 MNT
Cash: 200,000 MNT
Total liabilities: 300,000 MNT
Short-term debt: 200,000 MNT
Equity: 600,000 MNT
Cash flow from operations: 120,000 MNT
"""


def ocr_runner(warnings: list[str] | None = None, fallback_used: bool = False):
    def run(engine: str, fallback_engine: str, filename: str, content: bytes) -> dict:
        return normalize_ocr_response(
            engine=fallback_engine if fallback_used else engine,
            engine_version="test",
            pages=[NormalizedPage(page_number=1, text=FINANCIAL_TEXT, confidence=0.91)],
            confidence=0.91,
            warnings=warnings or [],
            fallback_used=fallback_used,
            fallback_reason="PaddleOCR package is not installed." if fallback_used else None,
        )

    return run


class DocumentPipelineTests(unittest.TestCase):
    def test_auto_engine_uses_openai_when_api_key_exists(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=True):
            self.assertEqual(default_ocr_engine(), "openai_ocr")
            self.assertEqual(_selected_engine("auto"), "openai_ocr")

    def test_auto_engine_uses_openai_without_openai_key(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(default_ocr_engine(), "openai_ocr")
            self.assertEqual(_selected_engine("auto"), "openai_ocr")

    def test_full_pipeline_payload_for_uploaded_financial_statement(self):
        result = run_document_pipeline(
            filename="statement.png",
            content=b"fake-image",
            engine="paddleocr",
            fallback_engine="mock",
            document_type="unknown",
            run_engine_with_fallback=ocr_runner(),
            borrower_metadata={"company_name": "Altan Trade LLC"},
        )

        payload = full_pipeline_payload(result)

        self.assertEqual(payload["parse_result"]["pages"][0]["strategy"], "ocr")
        self.assertEqual(payload["financial_extraction"]["document_type"], "financial_statement")
        self.assertEqual(payload["financial_extraction"]["income_statement"]["revenue"], 1_000_000)
        self.assertIn("overall_accuracy_score", payload["parser_audit"])
        self.assertIn("key_metrics", payload["lender_insights"])
        self.assertTrue(payload["memo_markdown"].startswith("#"))

    def test_text_pipeline_uses_client_pdf_text_without_binary_upload(self):
        result = run_text_pipeline(
            filename="large-digital.pdf",
            pages=[{"page_number": 1, "raw_text": FINANCIAL_TEXT}],
            document_type="unknown",
            borrower_metadata={"company_name": "Altan Trade LLC"},
        )
        payload = full_pipeline_payload(result)

        self.assertEqual(payload["parse_result"]["parser_version"], "client-digital-text-v1")
        self.assertEqual(payload["parse_result"]["pages"][0]["provenance"]["digital_parser"], "browser-pdfjs")
        self.assertEqual(payload["financial_extraction"]["income_statement"]["revenue"], 1_000_000)
        self.assertIn("client_pdf_text_mode", " ".join(payload["parse_result"]["global_warnings"]))

    def test_document_id_can_be_reused_for_financial_analysis(self):
        result = run_document_pipeline(
            filename="stored-statement.png",
            content=b"stored-image",
            engine="paddleocr",
            fallback_engine="mock",
            document_type="unknown",
            run_engine_with_fallback=ocr_runner(),
        )
        document_id = result["parserResult"]["document_id"]

        stored = get_document(document_id)
        analysis = financial_analysis_payload(stored or {})

        self.assertEqual(analysis["document_type"], "financial_statement")
        self.assertIn("financial_extraction", analysis)
        self.assertIn("parser_audit", analysis)
        self.assertIn("lender_insights", analysis)

    def test_missing_dependency_warning_survives_credit_memo_payload(self):
        result = run_document_pipeline(
            filename="fallback-statement.png",
            content=b"fallback-image",
            engine="paddleocr",
            fallback_engine="mock",
            document_type="unknown",
            run_engine_with_fallback=ocr_runner(["paddleocr_not_installed"], fallback_used=True),
        )

        memo_payload = credit_memo_payload(result)

        self.assertIn("paddleocr_not_installed", memo_payload["warnings"])
        self.assertIn("memo_markdown", memo_payload)
        self.assertGreaterEqual(memo_payload["data_quality"]["overall_accuracy_score"], 0)


if __name__ == "__main__":
    unittest.main()
