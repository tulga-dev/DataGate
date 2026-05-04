from __future__ import annotations

import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from normalize import normalize_ocr_response


def build_ocr_result(
    *,
    engine: str,
    engine_version: str | None,
    raw_text: str,
    confidence: float,
    started_at: float,
    warnings: list[str] | None = None,
    fallback_used: bool = False,
    fallback_reason: str | None = None,
) -> dict:
    return normalize_ocr_response(
        engine=engine,
        engine_version=engine_version,
        raw_text=raw_text,
        confidence=confidence,
        started_at=started_at,
        warnings=warnings,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
    )


@contextmanager
def temp_document_path(filename: str, content: bytes) -> Iterator[Path]:
    suffix = Path(filename).suffix or ".bin"
    handle = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        handle.write(content)
        handle.close()
        yield Path(handle.name)
    finally:
        try:
            os.unlink(handle.name)
        except FileNotFoundError:
            pass
