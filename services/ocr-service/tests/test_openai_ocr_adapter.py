from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from engines.openai_ocr import extract_with_openai_ocr


class OpenAiOcrAdapterTests(unittest.TestCase):
    @patch.dict("os.environ", {}, clear=True)
    def test_missing_api_key_returns_safe_fallback(self):
        result = extract_with_openai_ocr("statement.pdf", b"%PDF fake")

        self.assertTrue(result["fallbackUsed"])
        self.assertEqual(result["engine"], "openai_ocr")
        self.assertIn("openai_api_key_missing", result["warnings"][0])

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key", "OPENAI_OCR_MODEL": "test-model"}, clear=True)
    @patch("urllib.request.urlopen")
    def test_pdf_request_extracts_output_text(self, urlopen):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({"output_text": "Борлуулалтын орлого 100 MNT"}).encode(
            "utf-8"
        )
        urlopen.return_value = response

        result = extract_with_openai_ocr("statement.pdf", b"%PDF fake")

        self.assertFalse(result["fallbackUsed"])
        self.assertEqual(result["engine"], "openai_ocr")
        self.assertEqual(result["engineVersion"], "test-model")
        self.assertIn("Борлуулалтын орлого", result["rawText"])
        request = urlopen.call_args.args[0]
        body = json.loads(request.data.decode("utf-8"))
        file_item = body["input"][0]["content"][1]
        self.assertEqual(file_item["type"], "input_file")
        self.assertTrue(file_item["file_data"].startswith("data:application/pdf;base64,"))

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=True)
    @patch("urllib.request.urlopen")
    def test_image_request_uses_input_image(self, urlopen):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({"output_text": "Invoice total 100 MNT"}).encode(
            "utf-8"
        )
        urlopen.return_value = response

        result = extract_with_openai_ocr("invoice.png", b"fake-image")

        self.assertFalse(result["fallbackUsed"])
        request = urlopen.call_args.args[0]
        body = json.loads(request.data.decode("utf-8"))
        image_item = body["input"][0]["content"][1]
        self.assertEqual(image_item["type"], "input_image")
        self.assertTrue(image_item["image_url"].startswith("data:image/png;base64,"))


if __name__ == "__main__":
    unittest.main()
