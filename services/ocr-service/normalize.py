from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any


@dataclass
class NormalizedPage:
    page_number: int
    text: str
    confidence: float
    markdown: str | None = None
    blocks: list[Any] | None = None
    tables: list[Any] | None = None


def guess_language(text: str) -> str:
    cyrillic = sum(1 for char in text if "\u0400" <= char <= "\u04ff")
    latin = sum(1 for char in text if "a" <= char.lower() <= "z")

    if cyrillic > latin * 0.4:
        return "mn-Cyrl"
    if latin:
        return "en"
    return "unknown"


def average(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def clamp_confidence(value: float | int | None) -> float:
    if value is None:
        return 0.0
    return max(0.0, min(float(value), 1.0))


def markdown_from_text(engine: str, text: str) -> str | None:
    if not text:
        return None
    return f"# OCR result ({engine})\n\n{text}".strip()


def normalize_ocr_response(
    *,
    engine: str,
    engine_version: str | None,
    pages: list[NormalizedPage] | None = None,
    raw_text: str | None = None,
    confidence: float | None = None,
    started_at: float | None = None,
    warnings: list[str] | None = None,
    fallback_used: bool = False,
    fallback_reason: str | None = None,
) -> dict:
    started_at = started_at or perf_counter()
    warnings = warnings or []
    pages = pages or [
        NormalizedPage(
            page_number=1,
            text=raw_text or "",
            confidence=clamp_confidence(confidence),
        )
    ]

    page_payloads = []
    page_texts = []
    page_confidences = []

    for index, page in enumerate(pages, start=1):
        page_text = page.text or ""
        page_confidence = clamp_confidence(page.confidence)
        page_texts.append(page_text)
        page_confidences.append(page_confidence)
        page_markdown = page.markdown if page.markdown is not None else markdown_from_text(engine, page_text)
        page_payloads.append(
            {
                "pageNumber": page.page_number or index,
                "text": page_text,
                "markdown": page_markdown,
                "blocks": page.blocks or [],
                "tables": page.tables or [],
                "confidence": page_confidence,
            }
        )

    merged_text = raw_text if raw_text is not None else "\n\n".join(text for text in page_texts if text).strip()
    normalized_confidence = clamp_confidence(confidence if confidence is not None else average(page_confidences))

    return {
        "engine": engine,
        "engineVersion": engine_version,
        "rawText": merged_text,
        "markdown": markdown_from_text(engine, merged_text),
        "pages": page_payloads,
        "languageGuess": guess_language(merged_text),
        "confidence": normalized_confidence,
        "warnings": warnings,
        "processingTimeMs": int((perf_counter() - started_at) * 1000),
        "fallbackUsed": fallback_used,
        "fallbackReason": fallback_reason,
    }


def result_to_python(value: Any) -> Any:
    if hasattr(value, "json") and isinstance(value.json, dict):
        return value.json
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if hasattr(value, "__dict__") and value.__class__.__module__.startswith(("paddle", "paddlex")):
        return value.__dict__
    return value


def collect_text_and_scores(value: Any) -> tuple[list[str], list[float]]:
    value = result_to_python(value)
    texts: list[str] = []
    scores: list[float] = []

    if isinstance(value, dict):
        for text_key in ("rec_text", "text"):
            text_value = value.get(text_key)
            if isinstance(text_value, str) and text_value.strip():
                texts.append(text_value.strip())

        rec_texts = value.get("rec_texts")
        if isinstance(rec_texts, list):
            texts.extend(str(item).strip() for item in rec_texts if str(item).strip())

        for score_key in ("rec_score", "score", "confidence"):
            score_value = value.get(score_key)
            if isinstance(score_value, int | float):
                scores.append(float(score_value))

        rec_scores = value.get("rec_scores")
        if isinstance(rec_scores, list):
            scores.extend(float(item) for item in rec_scores if isinstance(item, int | float))

        for child in value.values():
            child_texts, child_scores = collect_text_and_scores(child)
            texts.extend(child_texts)
            scores.extend(child_scores)

    elif isinstance(value, list | tuple):
        if len(value) >= 2 and isinstance(value[0], str) and isinstance(value[1], int | float):
            texts.append(value[0].strip())
            scores.append(float(value[1]))
        elif len(value) >= 2 and isinstance(value[1], list | tuple):
            candidate = value[1]
            if len(candidate) >= 2 and isinstance(candidate[0], str) and isinstance(candidate[1], int | float):
                texts.append(candidate[0].strip())
                scores.append(float(candidate[1]))

        for child in value:
            child_texts, child_scores = collect_text_and_scores(child)
            texts.extend(child_texts)
            scores.extend(child_scores)

    return [text for text in texts if text], scores
