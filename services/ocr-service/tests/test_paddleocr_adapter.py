from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from engines import paddleocr


class PaddleOcrAdapterTests(unittest.TestCase):
    def tearDown(self):
        paddleocr._PADDLE_DISABLED_REASON = None

    def test_windows_cpu_runtime_error_disables_paddle_for_session(self):
        paddleocr._PADDLE_DISABLED_REASON = None
        runtime_error = RuntimeError(
            "(Unimplemented) ConvertPirAttribute2RuntimeAttribute not support "
            "[pir::ArrayAttribute<pir::DoubleAttribute>] "
            "(at ..\\paddle\\fluid\\framework\\new_executor\\instruction\\onednn\\onednn_instruction.cc:118)"
        )

        with patch("engines.paddleocr._create_paddleocr", side_effect=runtime_error) as create_ocr:
            first = paddleocr.extract_with_paddleocr("scan.png", b"fake-image")
            second = paddleocr.extract_with_paddleocr("scan.png", b"fake-image")

        self.assertTrue(first["fallbackUsed"])
        self.assertTrue(second["fallbackUsed"])
        self.assertIn("paddleocr_windows_cpu_runtime_unsupported", first["warnings"][0])
        self.assertIn("paddleocr_disabled_after_runtime_error", second["warnings"][0])
        self.assertEqual(create_ocr.call_count, 1)


if __name__ == "__main__":
    unittest.main()
