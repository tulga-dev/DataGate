import json
from typing import Any, Callable

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from document_pipeline import (
    collect_warnings,
    credit_memo_payload,
    financial_analysis_payload,
    full_pipeline_payload,
    get_document,
    placeholder_pipeline_result,
    run_document_pipeline,
)
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
    warnings: list[str] = Field(default_factory=list)
    strategy: str | None = None
    metadata: dict | None = None


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
    parserResult: dict | None = None
    parserVersion: str | None = None
    financialExtraction: dict | None = None
    parserAudit: dict | None = None
    lenderInsights: dict | None = None
    creditMemoMarkdown: str | None = None


class FinancialAnalysisResponse(BaseModel):
    document_type: str
    financial_extraction: dict = Field(default_factory=dict)
    parser_audit: dict = Field(default_factory=dict)
    lender_insights: dict = Field(default_factory=dict)


class CreditMemoResponse(BaseModel):
    memo_markdown: str
    data_quality: dict = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class FullPipelineResponse(BaseModel):
    parse_result: dict = Field(default_factory=dict)
    financial_extraction: dict = Field(default_factory=dict)
    parser_audit: dict = Field(default_factory=dict)
    lender_insights: dict = Field(default_factory=dict)
    memo_markdown: str


app = FastAPI(title="DataGate OCR Service", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3020",
        "http://127.0.0.1:3020",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


def run_engine_with_fallback(engine: str, fallback_engine: str, filename: str, content: bytes) -> dict:
    selected_engine = engine if engine in ENGINES else "mock"
    selected_fallback = fallback_engine if fallback_engine in ENGINES else "mock"
    primary = run_engine(selected_engine, filename, content)

    if primary.get("fallbackUsed") and selected_fallback != selected_engine:
        fallback = run_engine(selected_fallback, filename, content)
        return merge_fallback_result(primary, fallback, selected_fallback)

    return primary


def _selected_engine(engine: str) -> str:
    return engine if engine in ENGINES else "mock"


def _selected_fallback(fallback_engine: str) -> str:
    return fallback_engine if fallback_engine in ENGINES else "mock"


def _parse_metadata_json(raw_metadata: str | None) -> tuple[dict[str, Any], list[str]]:
    if not raw_metadata:
        return {}, []
    try:
        value = json.loads(raw_metadata)
    except json.JSONDecodeError:
        return {}, ["borrower_metadata_invalid_json"]
    if isinstance(value, dict):
        return value, []
    return {}, ["borrower_metadata_must_be_json_object"]


async def _pipeline_from_upload(
    file: UploadFile,
    *,
    engine: str,
    fallback_engine: str,
    document_type: str,
    borrower_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    content = await file.read()
    filename = file.filename or "document"
    return run_document_pipeline(
        filename=filename,
        content=content,
        engine=_selected_engine(engine),
        fallback_engine=_selected_fallback(fallback_engine),
        document_type=document_type,
        run_engine_with_fallback=run_engine_with_fallback,
        borrower_metadata=borrower_metadata,
    )


async def _pipeline_from_file_or_store(
    *,
    file: UploadFile | None,
    document_id: str | None,
    engine: str,
    fallback_engine: str,
    document_type: str,
    borrower_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if file is not None:
        return await _pipeline_from_upload(
            file,
            engine=engine,
            fallback_engine=fallback_engine,
            document_type=document_type,
            borrower_metadata=borrower_metadata,
        )

    stored = get_document(document_id)
    if stored is not None:
        return stored

    reason = "missing_file_or_document_id" if not document_id else f"document_not_found: {document_id}"
    return placeholder_pipeline_result(reason)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ocr/extract", response_model=OcrResult)
async def extract_ocr(
    file: UploadFile = File(...),
    engine: str = Form(default="paddleocr"),
    fallback_engine: str = Form(default="mock"),
    document_type: str = Form(default="unknown"),
):
    return await _pipeline_from_upload(
        file,
        engine=engine,
        fallback_engine=fallback_engine,
        document_type=document_type,
    )


@app.post("/documents/parse")
async def parse_document(
    file: UploadFile = File(...),
    engine: str = Form(default="paddleocr"),
    fallback_engine: str = Form(default="mock"),
    document_type: str = Form(default="unknown"),
):
    try:
        result = await _pipeline_from_upload(
            file,
            engine=engine,
            fallback_engine=fallback_engine,
            document_type=document_type,
        )
        return result.get("parserResult") or {}
    except Exception as exc:
        return placeholder_pipeline_result(f"pipeline_error: {type(exc).__name__}: {exc}")["parserResult"]


@app.post("/documents/analyze-financials", response_model=FinancialAnalysisResponse)
async def analyze_financials(
    file: UploadFile | None = File(default=None),
    document_id: str | None = Form(default=None),
    engine: str = Form(default="paddleocr"),
    fallback_engine: str = Form(default="mock"),
    document_type: str = Form(default="unknown"),
):
    try:
        result = await _pipeline_from_file_or_store(
            file=file,
            document_id=document_id,
            engine=engine,
            fallback_engine=fallback_engine,
            document_type=document_type,
        )
    except Exception as exc:
        result = placeholder_pipeline_result(f"pipeline_error: {type(exc).__name__}: {exc}")
    return financial_analysis_payload(result)


@app.post("/documents/generate-credit-memo", response_model=CreditMemoResponse)
async def generate_credit_memo(
    file: UploadFile | None = File(default=None),
    document_id: str | None = Form(default=None),
    borrower_metadata: str | None = Form(default=None),
    engine: str = Form(default="paddleocr"),
    fallback_engine: str = Form(default="mock"),
    document_type: str = Form(default="unknown"),
):
    metadata, metadata_warnings = _parse_metadata_json(borrower_metadata)
    try:
        result = await _pipeline_from_file_or_store(
            file=file,
            document_id=document_id,
            engine=engine,
            fallback_engine=fallback_engine,
            document_type=document_type,
            borrower_metadata=metadata,
        )
    except Exception as exc:
        result = placeholder_pipeline_result(f"pipeline_error: {type(exc).__name__}: {exc}")
    return credit_memo_payload(result, metadata, metadata_warnings)


@app.post("/documents/full-pipeline", response_model=FullPipelineResponse)
async def full_pipeline(
    file: UploadFile = File(...),
    borrower_metadata: str | None = Form(default=None),
    engine: str = Form(default="paddleocr"),
    fallback_engine: str = Form(default="mock"),
    document_type: str = Form(default="unknown"),
):
    metadata, metadata_warnings = _parse_metadata_json(borrower_metadata)
    try:
        result = await _pipeline_from_upload(
            file,
            engine=engine,
            fallback_engine=fallback_engine,
            document_type=document_type,
            borrower_metadata=metadata,
        )
        if metadata_warnings:
            result["warnings"] = collect_warnings(result) + metadata_warnings
    except Exception as exc:
        result = placeholder_pipeline_result(f"pipeline_error: {type(exc).__name__}: {exc}")
    return full_pipeline_payload(result)
