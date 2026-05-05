from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.append(str(REPO_ROOT / "scripts"))

from benchmark_parser import run_benchmark


class BenchmarkParserTests(unittest.TestCase):
    def test_mock_fixture_benchmark_runs_without_ocr_dependencies(self):
        fixtures_dir = REPO_ROOT / "tests" / "fixtures" / "documents"
        expected_dir = REPO_ROOT / "tests" / "fixtures" / "expected"

        results = run_benchmark(fixtures_dir, expected_dir, "mock", "mock")
        by_name = {result["document_name"]: result for result in results}

        self.assertEqual(len(results), 4)
        self.assertEqual(by_name["digital_financial_statement_mn"]["field_accuracy"], 1.0)
        self.assertEqual(by_name["scanned_financial_statement_mn"]["parser_strategy"], "ocr")
        self.assertFalse(by_name["bank_statement_mn"]["expected_available"])


if __name__ == "__main__":
    unittest.main()
