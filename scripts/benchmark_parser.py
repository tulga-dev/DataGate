from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from time import perf_counter
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
OCR_SERVICE_ROOT = REPO_ROOT / "services" / "ocr-service"
sys.path.append(str(OCR_SERVICE_ROOT))

from document_pipeline import run_document_pipeline
from engines.mock import extract_with_mock
from financial.statement_extractor import extract_financial_statement

SUPPORTED_REAL_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}


def _fixture_name(path: Path) -> str:
    if path.name.endswith(".mock.json"):
        return path.name.removesuffix(".mock.json")
    return path.stem


def _expected_path_for(fixture_path: Path, expected_dir: Path) -> Path:
    return expected_dir / f"{_fixture_name(fixture_path)}.expected.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _mock_engine_runner(engine: str, fallback_engine: str, filename: str, content: bytes) -> dict[str, Any]:
    return extract_with_mock(filename, content)


def _load_mock_fixture(path: Path) -> dict[str, Any]:
    data = _load_json(path)
    parser_result = data.get("parser_result") or {}
    raw_text = "\n\n".join(str(page.get("raw_text") or "") for page in parser_result.get("pages") or [])
    return {
        "engine": "fixture",
        "engineVersion": "fixture-v1",
        "rawText": raw_text,
        "markdown": None,
        "pages": [],
        "languageGuess": "unknown",
        "confidence": max([float(page.get("confidence") or 0.0) for page in parser_result.get("pages") or []] or [0.0]),
        "warnings": parser_result.get("global_warnings") or [],
        "processingTimeMs": 0,
        "fallbackUsed": False,
        "fallbackReason": None,
        "parserResult": parser_result,
        "parserVersion": parser_result.get("parser_version") or "fixture-v1",
    }


def _parse_fixture(path: Path, engine: str, fallback_engine: str) -> dict[str, Any]:
    if path.name.endswith(".mock.json"):
        return _load_mock_fixture(path)

    content = path.read_bytes()
    return run_document_pipeline(
        filename=path.name,
        content=content,
        engine=engine,
        fallback_engine=fallback_engine,
        document_type="unknown",
        run_engine_with_fallback=_mock_engine_runner,
    )


def _field_value(extraction: dict[str, Any], field: str) -> Any:
    if field == "document_type":
        return extraction.get("document_type")
    for group in ("income_statement", "balance_sheet", "cash_flow"):
        values = extraction.get(group) or {}
        if field in values:
            return values.get(field)
    period = extraction.get("period") or {}
    if field in period:
        return period.get(field)
    return extraction.get(field)


def _values_match(actual: Any, expected: Any) -> bool:
    if actual is None:
        return expected is None
    if isinstance(expected, int | float) and isinstance(actual, int | float):
        tolerance = max(abs(float(expected)), 1.0) * 0.001
        return abs(float(actual) - float(expected)) <= tolerance
    return str(actual).strip().lower() == str(expected).strip().lower()


def _compare_fields(extraction: dict[str, Any], expected: dict[str, Any]) -> tuple[float, list[str], list[str]]:
    expected_fields = expected.get("fields") or {}
    if expected.get("document_type"):
        expected_fields = {"document_type": expected["document_type"], **expected_fields}

    if not expected_fields:
        return 0.0, [], []

    missing_fields: list[str] = []
    wrong_fields: list[str] = []

    for field, expected_value in expected_fields.items():
        actual_value = _field_value(extraction, field)
        if actual_value is None:
            missing_fields.append(field)
        elif not _values_match(actual_value, expected_value):
            wrong_fields.append(field)

    correct = len(expected_fields) - len(missing_fields) - len(wrong_fields)
    return round(correct / len(expected_fields), 4), missing_fields, wrong_fields


def _parser_strategy(parsed_document: dict[str, Any]) -> str:
    parser_result = parsed_document.get("parserResult") or {}
    strategies = [
        str(page.get("strategy"))
        for page in parser_result.get("pages") or []
        if page.get("strategy")
    ]
    if not strategies:
        return "unknown"
    unique = list(dict.fromkeys(strategies))
    return unique[0] if len(unique) == 1 else "+".join(unique)


def discover_fixtures(fixtures_dir: Path) -> list[Path]:
    candidates = []
    for path in fixtures_dir.iterdir():
        if path.is_dir() or path.name.startswith(".") or path.name.upper() == "README.MD":
            continue
        if path.name.endswith(".mock.json") or path.suffix.lower() in SUPPORTED_REAL_EXTENSIONS:
            candidates.append(path)
    return sorted(candidates, key=lambda item: item.name)


def benchmark_fixture(path: Path, expected_dir: Path, engine: str, fallback_engine: str) -> dict[str, Any]:
    started_at = perf_counter()
    parsed_document = _parse_fixture(path, engine, fallback_engine)
    extraction = extract_financial_statement(parsed_document)
    runtime_ms = int((perf_counter() - started_at) * 1000)

    expected_path = _expected_path_for(path, expected_dir)
    expected = _load_json(expected_path) if expected_path.exists() else {"fields": {}}
    field_accuracy, missing_fields, wrong_fields = _compare_fields(extraction, expected)

    result = {
        "document_name": _fixture_name(path),
        "field_accuracy": field_accuracy,
        "missing_fields": missing_fields,
        "wrong_fields": wrong_fields,
        "parser_strategy": _parser_strategy(parsed_document),
        "runtime_ms": runtime_ms,
    }
    if not expected_path.exists():
        result["expected_available"] = False
    return result


def run_benchmark(fixtures_dir: Path, expected_dir: Path, engine: str, fallback_engine: str) -> list[dict[str, Any]]:
    return [
        benchmark_fixture(path, expected_dir, engine, fallback_engine)
        for path in discover_fixtures(fixtures_dir)
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark DataGate parser and financial extraction accuracy.")
    parser.add_argument("--fixtures", default=str(REPO_ROOT / "tests" / "fixtures" / "documents"))
    parser.add_argument("--expected", default=None)
    parser.add_argument("--output", default=str(REPO_ROOT / "benchmark_results.json"))
    parser.add_argument("--engine", default="mock")
    parser.add_argument("--fallback-engine", default="mock")
    args = parser.parse_args()

    fixtures_dir = Path(args.fixtures).resolve()
    expected_dir = Path(args.expected).resolve() if args.expected else fixtures_dir.parent / "expected"
    output_path = Path(args.output).resolve()

    results = run_benchmark(fixtures_dir, expected_dir, args.engine, args.fallback_engine)
    payload = {
        "fixture_count": len(results),
        "results": results,
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
