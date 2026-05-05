from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable

sys.path.append(str(Path(__file__).parent))

from engines.glm_ocr import extract_with_glm_ocr  # noqa: E402
from engines.mock import extract_with_mock  # noqa: E402
from engines.openai_ocr import extract_with_openai_ocr  # noqa: E402
from engines.paddleocr import extract_with_paddleocr  # noqa: E402
from engines.surya import extract_with_surya  # noqa: E402

ENGINES: dict[str, Callable[[str, bytes], dict]] = {
    "glm_ocr": extract_with_glm_ocr,
    "mock": extract_with_mock,
    "openai_ocr": extract_with_openai_ocr,
    "paddleocr": extract_with_paddleocr,
    "surya": extract_with_surya,
}

SUPPORTED_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}


def sample_files(samples_dir: Path) -> list[Path]:
    if not samples_dir.exists():
        return []
    return sorted(path for path in samples_dir.rglob("*") if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES)


def run_benchmark(engine_name: str, samples_dir: Path, output_json: Path | None = None) -> list[dict]:
    engine = ENGINES[engine_name]
    results = []

    for path in sample_files(samples_dir):
        result = engine(path.name, path.read_bytes())
        raw_text = result.get("rawText") or ""
        item = {
            "filename": str(path),
            "engine": result.get("engine"),
            "engineVersion": result.get("engineVersion"),
            "processingTimeMs": result.get("processingTimeMs"),
            "confidence": result.get("confidence"),
            "languageGuess": result.get("languageGuess"),
            "textLength": len(raw_text),
            "warnings": result.get("warnings", []),
            "fallbackUsed": result.get("fallbackUsed"),
            "fallbackReason": result.get("fallbackReason"),
            "textPreview": raw_text[:500],
        }
        results.append(item)

    if output_json:
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    return results


def print_results(results: list[dict], samples_dir: Path) -> None:
    if not results:
        print(f"No sample OCR files found in {samples_dir}.")
        print("Add PDF/PNG/JPG samples under services/ocr-service/samples and rerun the benchmark.")
        return

    for item in results:
        print(f"filename: {item['filename']}")
        print(f"engine: {item['engine']} ({item['engineVersion']})")
        print(f"processing time: {item['processingTimeMs']}ms")
        print(f"confidence: {item['confidence']}")
        print(f"detected language: {item['languageGuess']}")
        print(f"text length: {item['textLength']}")
        print(f"warnings: {json.dumps(item['warnings'], ensure_ascii=False)}")
        if item["fallbackUsed"]:
            print(f"fallback reason: {item['fallbackReason']}")
        print("text preview:")
        print((item["textPreview"] or "").replace("\r", "")[:500])
        print("-" * 80)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Benchmark DataGate OCR engines against files in samples/.")
    parser.add_argument("--engine", choices=sorted(ENGINES), default="openai_ocr")
    parser.add_argument("--samples-dir", default=str(Path(__file__).parent / "samples"))
    parser.add_argument("--output-json", default=None)
    args = parser.parse_args()

    samples_dir = Path(args.samples_dir)
    output_json = Path(args.output_json) if args.output_json else None
    results = run_benchmark(args.engine, samples_dir, output_json)
    print_results(results, samples_dir)


if __name__ == "__main__":
    main()
