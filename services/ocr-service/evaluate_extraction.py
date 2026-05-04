from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Callable

sys.path.append(str(Path(__file__).parent))

from engines.glm_ocr import extract_with_glm_ocr  # noqa: E402
from engines.mock import extract_with_mock  # noqa: E402
from engines.paddleocr import extract_with_paddleocr  # noqa: E402
from engines.surya import extract_with_surya  # noqa: E402

ENGINES: dict[str, Callable[[str, bytes], dict]] = {
    "glm_ocr": extract_with_glm_ocr,
    "mock": extract_with_mock,
    "paddleocr": extract_with_paddleocr,
    "surya": extract_with_surya,
}

EXPECTED_FIELDS = {
    "borrowerName": "Bat-Erdene Bold",
    "lenderName": "Khan Bank",
    "loanAmount": "50000000",
    "currency": "MNT",
    "interestRate": "2.2%",
    "termMonths": "24",
    "employeeName": "Bat-Erdene Bold",
    "monthlySalary": "3500000",
    "bankName": "Khan Bank",
    "companyName": "Altan Trade LLC",
    "invoiceTotal": "1250000",
}

SUPPORTED_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}


def normalize_value(value: str | None) -> str | None:
    if value is None:
        return None
    return re.sub(r"[\s,]+", "", value).lower()


def first_match(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    return match.group(1).strip() if match else None


def amount_after(text: str, label: str) -> str | None:
    value = first_match(text, rf"{re.escape(label)}[^\d]*(\d[\d,\s]*)\s*(?:MNT|₮)?")
    return value.replace(",", "").replace(" ", "") if value else None


def extract_fake_fields(text: str) -> dict[str, str | None]:
    has_bat = "Bat-Erdene Bold" in text or "Бат-Эрдэнэ Болд" in text
    has_khan = "Khan Bank" in text
    has_altan = "Altan Trade LLC" in text

    return {
        "borrowerName": "Bat-Erdene Bold" if has_bat else first_match(text, r"Borrower[^:]*:\s*([^\n]+)"),
        "lenderName": "Khan Bank" if has_khan else first_match(text, r"Lender[^:]*:\s*([^\n]+)"),
        "loanAmount": amount_after(text, "Loan amount"),
        "currency": "MNT" if "MNT" in text else None,
        "interestRate": first_match(text, r"(2\.2%)"),
        "termMonths": first_match(text, r"(?:Term|Хугацаа)[^:]*:\s*(\d+)"),
        "employeeName": "Bat-Erdene Bold" if has_bat else first_match(text, r"Employee:\s*([^\n]+)"),
        "monthlySalary": amount_after(text, "Monthly salary"),
        "bankName": "Khan Bank" if has_khan else first_match(text, r"Bank name:\s*([^\n]+)"),
        "companyName": "Altan Trade LLC" if has_altan else first_match(text, r"Company:\s*([^\n]+)"),
        "invoiceTotal": amount_after(text, "Invoice total"),
    }


def compare_fields(extracted: dict[str, str | None]) -> list[dict]:
    rows = []
    for field, expected in EXPECTED_FIELDS.items():
        actual = extracted.get(field)
        expected_norm = normalize_value(expected)
        actual_norm = normalize_value(actual)
        present = actual not in (None, "")
        exact_match = present and actual_norm == expected_norm
        partial_match = False
        if present and expected_norm and actual_norm:
            partial_match = expected_norm in actual_norm or actual_norm in expected_norm
        rows.append(
            {
                "field": field,
                "expected": expected,
                "actual": actual,
                "present": present,
                "exactMatch": exact_match,
                "partialMatch": partial_match,
            }
        )
    return rows


def sample_files(samples_dir: Path) -> list[Path]:
    if not samples_dir.exists():
        return []
    return sorted(path for path in samples_dir.rglob("*") if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES)


def evaluate(engine_name: str, samples_dir: Path) -> dict:
    engine = ENGINES[engine_name]
    files = sample_files(samples_dir)

    if not files:
        files = [Path("mock-datagate-fixture.txt")]

    documents = []
    all_rows = []

    for path in files:
        content = path.read_bytes() if path.exists() else b"mock"
        result = engine(path.name, content)
        extracted = extract_fake_fields(result.get("rawText", ""))
        rows = compare_fields(extracted)
        all_rows.extend(rows)
        documents.append(
            {
                "filename": str(path),
                "engine": result.get("engine"),
                "confidence": result.get("confidence"),
                "warnings": result.get("warnings", []),
                "fields": rows,
            }
        )

    scored = [row for row in all_rows if row["present"]]
    exact_matches = sum(1 for row in all_rows if row["exactMatch"])
    partial_matches = sum(1 for row in all_rows if row["partialMatch"])
    total = len(all_rows)

    return {
        "engine": engine_name,
        "documentsEvaluated": len(documents),
        "fieldAccuracyPercent": round((exact_matches / total) * 100, 2) if total else 0,
        "partialFieldAccuracyPercent": round((partial_matches / total) * 100, 2) if total else 0,
        "fieldPresencePercent": round((len(scored) / total) * 100, 2) if total else 0,
        "documents": documents,
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Evaluate DataGate OCR/extraction output against fake expected fields.")
    parser.add_argument("--engine", choices=sorted(ENGINES), default="mock")
    parser.add_argument("--samples-dir", default=str(Path(__file__).parent / "samples"))
    parser.add_argument("--output-json", default=None)
    args = parser.parse_args()

    report = evaluate(args.engine, Path(args.samples_dir))
    print(json.dumps(report, indent=2, ensure_ascii=False))

    if args.output_json:
        output_path = Path(args.output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
