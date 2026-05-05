from __future__ import annotations

import base64
import json
import mimetypes
import os
import urllib.error
import urllib.request
from pathlib import Path
from time import perf_counter

from engines.common import build_ocr_result
from engines.mock import extract_with_mock

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"


def _mock_fallback(filename: str, content: bytes, *, warning: str, reason: str) -> dict:
    result = extract_with_mock(filename, content)
    result["engine"] = "openai_ocr"
    result["engineVersion"] = os.getenv("OPENAI_OCR_MODEL", "not-configured")
    result["warnings"] = [warning]
    result["fallbackUsed"] = True
    result["fallbackReason"] = reason
    return result


def _mime_type(filename: str) -> str:
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or "application/octet-stream"


def _input_file_item(filename: str, content: bytes) -> dict:
    encoded = base64.b64encode(content).decode("ascii")
    mime_type = _mime_type(filename)
    suffix = Path(filename).suffix.lower()

    if suffix == ".pdf" or content.startswith(b"%PDF"):
        return {
            "type": "input_file",
            "filename": filename,
            "file_data": f"data:application/pdf;base64,{encoded}",
        }

    return {
        "type": "input_image",
        "image_url": f"data:{mime_type};base64,{encoded}",
        "detail": os.getenv("OPENAI_OCR_IMAGE_DETAIL", "high"),
    }


def _extract_output_text(payload: dict) -> str:
    output_text = payload.get("output_text")
    if isinstance(output_text, str):
        return output_text.strip()

    chunks: list[str] = []
    for item in payload.get("output") or []:
        if not isinstance(item, dict):
            continue
        for content in item.get("content") or []:
            if not isinstance(content, dict):
                continue
            text = content.get("text")
            if isinstance(text, str) and text.strip():
                chunks.append(text.strip())
    return "\n\n".join(chunks).strip()


def extract_with_openai_ocr(filename: str, content: bytes) -> dict:
    started = perf_counter()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _mock_fallback(
            filename,
            content,
            warning="openai_api_key_missing: set OPENAI_API_KEY to enable OpenAI OCR.",
            reason="OpenAI API key is not configured.",
        )

    model = os.getenv("OPENAI_OCR_MODEL", "gpt-4.1-mini")
    prompt = os.getenv(
        "OPENAI_OCR_PROMPT",
        (
            "Extract all visible text from this Mongolian financial document. "
            "Preserve Mongolian Cyrillic exactly. Preserve tables as readable Markdown. "
            "Do not summarize, infer, translate, or add explanations. Return only extracted text."
        ),
    )
    request_payload = {
        "model": model,
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    _input_file_item(filename, content),
                ],
            }
        ],
    }

    try:
        request = urllib.request.Request(
            OPENAI_RESPONSES_URL,
            data=json.dumps(request_payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        timeout_seconds = int(os.getenv("OPENAI_OCR_TIMEOUT_SECONDS", "90"))
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))

        raw_text = _extract_output_text(payload)
        warnings = [] if raw_text else ["openai_ocr_empty_result: OpenAI returned no extracted text."]
        return build_ocr_result(
            engine="openai_ocr",
            engine_version=model,
            raw_text=raw_text,
            confidence=0.86 if raw_text else 0.0,
            started_at=started,
            warnings=warnings,
        )
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:500]
        return _mock_fallback(
            filename,
            content,
            warning=f"openai_ocr_http_error: {error.code} {detail}",
            reason="OpenAI OCR request failed.",
        )
    except Exception as error:
        return _mock_fallback(
            filename,
            content,
            warning=f"openai_ocr_runtime_error: {error}",
            reason="OpenAI OCR failed at runtime.",
        )
