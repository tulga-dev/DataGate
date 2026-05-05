from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedNumber:
    value: int | float
    raw_value: str
    scale: int


def detect_scale(context: str) -> int:
    lowered = context.lower()
    if any(token in lowered for token in ["сая", "million", "millions"]):
        return 1_000_000
    if any(token in lowered for token in ["мянга", "thousand", "thousands"]):
        return 1_000
    return 1


def parse_number(raw_value: str, context: str = "") -> ParsedNumber | None:
    raw = raw_value.strip()
    if not raw:
        return None

    negative = raw.startswith("(") and raw.endswith(")")
    cleaned = raw.strip("()")
    cleaned = cleaned.replace(",", "").replace(" ", "")
    cleaned = re.sub(r"[^0-9.\-]", "", cleaned)

    if cleaned in ("", "-", "."):
        return None

    try:
        number: int | float
        number = float(cleaned) if "." in cleaned else int(cleaned)
    except ValueError:
        return None

    if negative:
        number = -abs(number)

    scale = detect_scale(f"{context} {raw_value}")
    number = number * scale

    if isinstance(number, float) and number.is_integer():
        number = int(number)

    return ParsedNumber(value=number, raw_value=raw_value, scale=scale)


def find_number(text: str) -> ParsedNumber | None:
    match = re.search(r"\(?-?\d[\d,\s]*(?:\.\d+)?\)?", text)
    if not match:
        return None
    return parse_number(match.group(0), text)
