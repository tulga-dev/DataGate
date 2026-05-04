from typing import Callable

from fastapi import FastAPI, File, Form, UploadFile
from pydantic import BaseModel, Field

from engines.glm_ocr import extract_with_glm_ocr
from engines.mock import extract_with_mock
from engines.paddleocr import extract_with_paddleocr
from engines.surya import extract_with_surya


class OcrPage(BaseModel):
    pageNumber: int
    text: str
    markdown: str | None = None
    blocks: list = Field(default_factory=list)
    tables: list = Field(default_factory=list)
    confidence: float


class OcrResult(BaseModel):
    engine: str
    engineVersion: str | None = None
    rawText: str
    markdown: str | None = None
    pages: list[OcrPage]
    languageGuess: str
    confidence: float
    warnings: list[str] = Field(default_factory=list)
    processingTimeMs: int
    fallbackUsed: bool
    fallbackReason: str | None = None


app = FastAPI(title="DataGate OCR Service", version="0.1.0")

EngineHandler = Callable[[str, bytes], dict]

ENGINES: dict[str, EngineHandler] = {
    "glm_ocr": extract_with_glm_ocr,
    "mock": extract_with_mock,
    "paddleocr": extract_with_paddleocr,
    "surya": extract_with_surya,
}


def run_engine(engine: str, filename: str, content: bytes) -> dict:
    handler = ENGINES.get(engine, extract_with_mock)
    return handler(filename, content)


def merge_fallback_result(primary: dict, fallback: dict, fallback_engine: str) -> dict:
    primary_warnings = primary.get("warnings") or []
    fallback_warnings = fallback.get("warnings") or []
    primary_engine = primary.get("engine") or "unknown"
    primary_reason = primary.get("fallbackReason") or "Primary OCR engine failed."

    fallback["warnings"] = [
        *primary_warnings,
        *fallback_warnings,
        f"fallback_engine_used: {primary_engine} failed; {fallback_engine} produced the final OCR result.",
    ]
    fallback["fallbackUsed"] = True
    fallback["fallbackReason"] = f"{primary_engine} failed: {primary_reason}"
    return fallback


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ocr/extract", response_model=OcrResult)
async def extract_ocr(
    file: UploadFile = File(...),
    engine: str = Form(default="paddleocr"),
    fallback_engine: str = Form(default="mock"),
):
    content = await file.read()
    filename = file.filename or "document"
    selected_engine = engine if engine in ENGINES else "mock"
    selected_fallback = fallback_engine if fallback_engine in ENGINES else "mock"

    primary = run_engine(selected_engine, filename, content)

    if primary.get("fallbackUsed") and selected_fallback != selected_engine:
        fallback = run_engine(selected_fallback, filename, content)
        return merge_fallback_result(primary, fallback, selected_fallback)

    return primary
