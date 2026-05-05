from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from normalize import NormalizedPage, normalize_ocr_response
from parsers.digital_pdf import DigitalPdfPage, DigitalPdfResult
from parsers.hybrid_pdf import parse_pdf_hybrid
from parsers.tables import TableExtractionResult


def digital_result(page: DigitalPdfPage) -> DigitalPdfResult:
    return DigitalPdfResult(pages=[page], parser_name="test-digital", parser_version="test")


def no_tables() -> TableExtractionResult:
    return TableExtractionResult(tables_by_page={1: []})


def ocr_result(text: str = "OCR text from scanned PDF", fallback: bool = False) -> dict:
    result = normalize_ocr_response(
        engine="paddleocr",
        engine_version="test",
        pages=[NormalizedPage(page_number=1, text=text, confidence=0.81)],
        confidence=0.81,
        warnings=["paddleocr_not_installed"] if fallback else [],
        fallback_used=fallback,
        fallback_reason="PaddleOCR package is not installed." if fallback else None,
    )
    return result


class HybridPdfParserTests(unittest.TestCase):
    def test_digital_pdf_does_not_call_ocr_when_quality_is_good(self) -> None:
        calls: list[str] = []
        page = DigitalPdfPage(
            page_number=1,
            raw_text="Digital loan agreement text " * 20,
            extraction_confidence=0.9,
            image_area_ratio=0.05,
        )

        with patch("parsers.hybrid_pdf.extract_digital_pdf", return_value=digital_result(page)), patch(
            "parsers.hybrid_pdf.extract_tables", return_value=no_tables()
        ):
            result = parse_pdf_hybrid(
                "digital.pdf",
                b"%PDF digital",
                selected_engine="paddleocr",
                ocr_handler=lambda _name, _content: calls.append("ocr") or ocr_result(),
            )

        self.assertEqual(calls, [])
        self.assertEqual(result["pages"][0]["strategy"], "digital")
        self.assertEqual(result["parserResult"]["pages"][0]["strategy"], "digital")

    def test_scanned_pdf_calls_ocr_adapter(self) -> None:
        calls: list[str] = []
        page = DigitalPdfPage(page_number=1, raw_text="", extraction_confidence=0.0, image_area_ratio=0.95)

        with patch("parsers.hybrid_pdf.extract_digital_pdf", return_value=digital_result(page)), patch(
            "parsers.hybrid_pdf.extract_tables", return_value=no_tables()
        ):
            result = parse_pdf_hybrid(
                "scanned.pdf",
                b"%PDF scanned",
                selected_engine="paddleocr",
                ocr_handler=lambda _name, _content: calls.append("ocr") or ocr_result(),
            )

        self.assertEqual(calls, ["ocr"])
        self.assertEqual(result["pages"][0]["strategy"], "ocr")

    def test_missing_ocr_dependency_does_not_crash(self) -> None:
        page = DigitalPdfPage(page_number=1, raw_text="", extraction_confidence=0.0, image_area_ratio=0.95)

        with patch("parsers.hybrid_pdf.extract_digital_pdf", return_value=digital_result(page)), patch(
            "parsers.hybrid_pdf.extract_tables", return_value=no_tables()
        ):
            result = parse_pdf_hybrid(
                "missing-ocr.pdf",
                b"%PDF scanned",
                selected_engine="paddleocr",
                ocr_handler=lambda _name, _content: ocr_result(fallback=True),
            )

        self.assertTrue(result["fallbackUsed"])
        self.assertIn("paddleocr_not_installed", " ".join(result["warnings"]))

    def test_low_quality_digital_extraction_triggers_ocr_fallback(self) -> None:
        calls: list[str] = []
        page = DigitalPdfPage(
            page_number=1,
            raw_text="too short",
            extraction_confidence=0.3,
            image_area_ratio=0.2,
        )

        with patch("parsers.hybrid_pdf.extract_digital_pdf", return_value=digital_result(page)), patch(
            "parsers.hybrid_pdf.extract_tables", return_value=no_tables()
        ):
            result = parse_pdf_hybrid(
                "low-quality.pdf",
                b"%PDF low",
                selected_engine="paddleocr",
                ocr_handler=lambda _name, _content: calls.append("ocr") or ocr_result("better OCR text"),
            )

        self.assertEqual(calls, ["ocr"])
        self.assertEqual(result["pages"][0]["strategy"], "hybrid")

    def test_response_includes_page_level_strategy_and_warnings(self) -> None:
        page = DigitalPdfPage(
            page_number=1,
            raw_text="Digital text " * 20,
            extraction_confidence=0.9,
            image_area_ratio=0.0,
            warnings=["digital_blocks_failed"],
        )

        with patch("parsers.hybrid_pdf.extract_digital_pdf", return_value=digital_result(page)), patch(
            "parsers.hybrid_pdf.extract_tables", return_value=no_tables()
        ):
            result = parse_pdf_hybrid(
                "warnings.pdf",
                b"%PDF warnings",
                selected_engine="paddleocr",
                ocr_handler=lambda _name, _content: ocr_result(),
            )

        self.assertEqual(result["pages"][0]["strategy"], "digital")
        self.assertIn("digital_blocks_failed", result["pages"][0]["warnings"])
        self.assertEqual(result["parserResult"]["parser_version"], "hybrid-v1")
        self.assertIn("metrics", result["parserResult"]["pages"][0])


if __name__ == "__main__":
    unittest.main()
