# DataGate OCR Service

FastAPI OCR extraction service behind the Next.js app. The service uses an `auto` OCR engine by default. `auto` routes to OpenAI OCR, with safe fallback behavior when the API key is missing or optional local dependencies are unavailable.

## Basic OCR Service

```bash
cd services/ocr-service
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Then set:

```bash
OCR_SERVICE_URL=http://localhost:8000
```

## Engines

- `mock`: implemented and dependency-free.
- `hybrid PDF parser`: digital-first parser for PDFs. It uses PyMuPDF before OCR and records per-page strategy metadata.
- `openai_ocr`: optional cloud OCR adapter using OpenAI vision/PDF inputs through the Responses API.
- `paddleocr`: first practical real OCR adapter. If dependencies are missing or inference fails, the response includes warnings and falls back safely.
- `glm_ocr`: optional future adapter path for GLM-OCR when `torch`, compatible `transformers`, and model weights are installed.
- `surya`: placeholder adapter for layout/table fallback.

The heavy adapters intentionally import optional dependencies lazily so local development never breaks.

## OCR Provider Routing

Endpoint form field `engine` defaults to `auto`.

`auto` selects:

1. `openai_ocr` as the primary OCR provider.
2. `mock` only as the final safe fallback.

PaddleOCR remains available as an explicit engine, but it is not the default demo path on Windows because some PaddlePaddle CPU builds can fail inside the native runtime before DataGate receives OCR output.

## Optional OpenAI OCR

OpenAI OCR is dependency-free in this service because it calls the HTTPS Responses API directly.

```bash
OPENAI_API_KEY=...
OPENAI_OCR_MODEL=gpt-4.1-mini
DATAGATE_DEFAULT_OCR_ENGINE=auto
```

The adapter supports:

- PDFs as `input_file`
- PNG/JPG/JPEG/WebP images as `input_image`

If `OPENAI_API_KEY` is missing or the API request fails, the engine returns a structured warning and the router can fall back safely. For uploaded PDFs, DataGate does not use mock OCR text as real document evidence when a real OCR provider fails.

## Hybrid PDF Routing

PDF uploads go through `hybrid-v1` before OCR:

1. Detect whether the file is a PDF.
2. Try digital text extraction with PyMuPDF.
3. Calculate page metrics: text character count, word count, table candidate count, image area ratio, extraction confidence, and selected strategy.
4. Use digital extraction when the page has enough text and confidence.
5. Use OCR only for scanned/image-heavy pages or low-quality digital extraction.
6. Merge digital text and OCR text when both are available, preserving provenance in `parserResult`.

The OCR response remains backward-compatible. Additional metadata appears in:

- `parserVersion`
- `parserResult`
- `pages[].strategy`
- `pages[].metadata`
- `pages[].warnings`

Digital PDFs do not require PaddleOCR. If PyMuPDF is missing, the service returns `pymupdf_not_installed` as a warning and attempts the configured OCR fallback.

## Financial Statement Extraction

The OCR service adds a lending-ready `financialExtraction` object on top of parsed text and tables. It is rule-based for now and focuses on `financial_statement`.

Supported financial document classes:

- `financial_statement`
- `bank_statement`
- `tax_report`
- `loan_contract`
- `unknown`

The extractor maps Mongolian and English accounting labels into a stable JSON schema for:

- income statement
- balance sheet
- cash flow
- missing fields
- source references

Every extracted value includes provenance when possible:

- field name
- normalized value
- raw value
- page number
- source: `text` or `table`
- raw label
- confidence

Numeric normalization handles comma separators, spaces, parentheses for negatives, and thousand/million scale words such as `мянга`, `сая`, `thousand`, and `million`.

## Parser Accuracy Audit

The OCR service also returns `parserAudit`, a lender-facing quality report produced entirely from parser output and financial extraction output. It does not depend on a specific OCR engine.

The audit includes:

- overall accuracy score
- per-field confidence and evidence status
- page-level evidence references
- red flags
- warnings
- recommended manual review fields
- credit memo readiness

Current red flags include:

- balance sheet mismatch: assets do not approximately equal liabilities plus equity
- profit/loss sign conflict
- revenue missing while profit exists
- liabilities exceeding assets
- conflicting periods across pages

Minimum fields for credit memo readiness are revenue, net profit, total assets, total liabilities, equity, and period or fiscal year.

## Lender Insights

The OCR service returns deterministic `lenderInsights` before any LLM generation. It calculates ratios, risk flags, positive signals, borrower questions, and credit memo inputs from `financialExtraction` and `parserAudit`.

Key metrics include:

- gross margin
- net margin
- debt to assets
- debt to equity
- current ratio
- return on assets
- equity ratio

Risk flags include negative profit, negative equity, liabilities exceeding assets, high leverage, weak current ratio, missing revenue, missing cash, low parser confidence, and documents not ready for memo generation.

The output is ready to feed into Mongolian credit memo generation as structured deterministic context.

## Credit Memo Markdown

The OCR service returns deterministic `creditMemoMarkdown` for a concise Mongolian lender memo. It does not include raw OCR text or internal parser logs.

Memo sections:

- Зээл хүсэгчийн товч мэдээлэл
- Санхүүгийн гол үзүүлэлтүүд
- Гол харьцаа үзүүлэлтүүд
- Эерэг дохио
- Эрсдэлийн дохио
- Зээл олгохоос өмнө тодруулах асуултууд
- Урьдчилсан дүгнэлт

The conclusion is deterministic and never auto-approves a loan. It uses document readiness, leverage, equity, profitability, and data quality to choose a conservative preliminary conclusion.

## Optional PaddleOCR

```bash
pip install paddleocr paddlepaddle
```

Useful PaddleOCR environment variables:

```bash
PADDLEOCR_DEVICE=cpu
PADDLEOCR_LANG=en
PADDLEOCR_VERSION=PP-OCRv5
```

## Optional PDF Support

The digital parser uses PyMuPDF and is included in the base requirements. PaddleOCR image files work directly. OCR for image-only PDF files can use `pdf2image` or the Poppler-free `pypdfium2` fallback:

```bash
pip install pdf2image
pip install pypdfium2
```

`pdf2image` also requires Poppler to be installed on the host and available on `PATH`. If Poppler is unavailable, DataGate attempts `pypdfium2`. If neither PDF rendering path is available, PDF OCR returns a structured warning and falls back safely.

## Optional Table Extraction

Table extraction hooks are dependency-aware:

```bash
pip install pdfplumber
```

Camelot can also be added later. If no table extraction dependency is installed, table output is empty and the parser returns a warning instead of raising an exception.

## Optional GLM-OCR

GLM-OCR requires `torch`, compatible `transformers`, model weights, and likely GPU or large-memory CPU execution. Keep it as an explicit advanced engine request rather than the default local path.

```bash
GLM_OCR_MODEL_ID=zai-org/GLM-OCR
GLM_OCR_DEVICE_MAP=auto
GLM_OCR_MAX_NEW_TOKENS=1024
```

## Benchmark

Add sample files under `services/ocr-service/samples`, then run:

```bash
python benchmark.py --engine paddleocr
python benchmark.py --engine openai_ocr
python benchmark.py --engine mock
python benchmark.py --engine glm_ocr
python benchmark.py --engine surya
```

The benchmark prints filename, engine, processing time, confidence, detected language, text length, warnings, and the first 500 characters of extracted text.

## Extraction Evaluation

Run the fake expected-field evaluator:

```bash
python evaluate_extraction.py --engine mock
python evaluate_extraction.py --engine paddleocr
```

It reports field presence, exact matches, partial matches, and a simple field accuracy percentage.

Run parser tests:

```bash
python -m unittest discover -s tests
```

## Parser Accuracy Benchmark

The repository includes a benchmark harness for tracking parser and financial extraction accuracy over time.

```bash
python scripts/benchmark_parser.py --fixtures tests/fixtures/documents
```

The script:

- loads real PDFs/images or lightweight `.mock.json` parser fixtures
- runs the parser output through the financial statement extractor
- compares extracted values against `tests/fixtures/expected/*.expected.json`
- prints JSON results
- saves the same payload to `benchmark_results.json`

Current mock fixtures run without OCR dependencies. Place real gold-standard PDFs in `tests/fixtures/documents` using names such as `digital_financial_statement_mn.pdf` and add manually verified expected values in `tests/fixtures/expected`.

## API

`POST /ocr/extract`

Form fields:

- `file`: required multipart file.
- `engine`: optional, defaults to `auto`.
- `fallback_engine`: optional, defaults to `mock`.

Response shape is normalized by `normalize.py` and remains stable across engines.

### Financial Document Intelligence API

These endpoints expose the full lender workflow while keeping `/ocr/extract` unchanged. All heavy parser/OCR dependencies are optional. If PaddleOCR, PyMuPDF, PDF rendering dependencies, table parsers, or GLM-OCR dependencies are missing, the response includes warnings and falls back where possible.

#### POST `/documents/parse`

Input: multipart upload with `file`.

Optional form fields:

- `engine`: defaults to `auto`
- `fallback_engine`: defaults to `mock`
- `document_type`: defaults to `unknown`

Example:

```bash
curl -X POST http://localhost:8000/documents/parse \
  -F "file=@samples/financial_statement.pdf"
```

Response example:

```json
{
  "document_id": "financial_statement.pdf:abc123",
  "document_type": "unknown",
  "pages": [
    {
      "page_number": 1,
      "strategy": "digital",
      "text_blocks": [],
      "tables": [],
      "raw_text": "...",
      "confidence": 0.91,
      "warnings": [],
      "metrics": {
        "text_char_count": 1200,
        "word_count": 180,
        "table_candidate_count": 2,
        "image_area_ratio": 0.05,
        "extraction_confidence": 0.91,
        "selected_strategy": "digital"
      }
    }
  ],
  "global_warnings": [],
  "parser_version": "hybrid-v1"
}
```

#### POST `/documents/analyze-financials`

Input: either multipart `file` or `document_id` from `/documents/parse`.

Example:

```bash
curl -X POST http://localhost:8000/documents/analyze-financials \
  -F "file=@samples/financial_statement.pdf"
```

Response example:

```json
{
  "document_type": "financial_statement",
  "financial_extraction": {},
  "parser_audit": {},
  "lender_insights": {}
}
```

#### POST `/documents/generate-credit-memo`

Input: either multipart `file` or `document_id`, with optional JSON string `borrower_metadata`.

Example:

```bash
curl -X POST http://localhost:8000/documents/generate-credit-memo \
  -F "file=@samples/financial_statement.pdf" \
  -F "borrower_metadata={\"company_name\":\"Altan Trade LLC\"}"
```

Response example:

```json
{
  "memo_markdown": "# Зээлийн шинжилгээний товч мемо\n\n...",
  "data_quality": {
    "overall_accuracy_score": 0.88,
    "recommended_manual_review_fields": [],
    "lender_insight_readiness": {
      "ready_for_credit_memo": true
    }
  },
  "warnings": []
}
```

#### POST `/documents/full-pipeline`

Input: multipart `file`, with optional JSON string `borrower_metadata`.

Example:

```bash
curl -X POST http://localhost:8000/documents/full-pipeline \
  -F "file=@samples/financial_statement.pdf" \
  -F "borrower_metadata={\"company_name\":\"Altan Trade LLC\"}"
```

Response example:

```json
{
  "parse_result": {},
  "financial_extraction": {},
  "parser_audit": {},
  "lender_insights": {},
  "memo_markdown": "# Зээлийн шинжилгээний товч мемо\n\n..."
}
```

For scanned PDFs without installed OCR dependencies, the service returns fallback warnings such as `paddleocr_not_installed` or `openai_api_key_missing` and still produces a stable response. For uploaded PDFs, mock OCR text is not treated as real document evidence when a real OCR provider fails.
