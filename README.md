# DataGate — Mongolian Financial Document Intelligence

DataGate is a financial document intelligence layer for Mongolia. The MVP lets banks, NBFIs, fintechs, leasing teams, accountants, and SMEs upload financial documents, run OCR through a clean engine abstraction, classify document type, extract structured fields, review low-confidence outputs, save corrections, and export JSON.

## MVP scope

- Upload PDF, PNG, JPG, and JPEG documents up to 20MB.
- Run OCR through an engine router with local mock fallback.
- Classify loan agreements, bank statements, salary statements, company certificates, collateral documents, identity documents, invoices/receipts, and unknown documents.
- Extract structured financial fields with rule-based regex logic.
- Show confidence, warnings, OCR metadata, raw OCR text, review status, and editable fields.
- Save results to Supabase when configured, otherwise use in-memory mock storage.
- Approve, send to human review, patch corrected extracted data, and export JSON.

## Architecture

- `app/`: Next.js App Router pages and API routes.
- `components/datagate/`: DataGate UI components.
- `lib/document-processing/`: OCR abstraction, classifier, extractor, schemas, and processing router.
- `lib/storage/`: Supabase client and mock storage fallback.
- `services/ocr-service/`: FastAPI OCR microservice skeleton.
- `supabase/migrations/`: Database schema for documents, reviews, and events.

## OCR strategy

The Next.js API calls `extractTextFromDocument(file, options)`. If `OCR_SERVICE_URL` is configured, it posts the document to the FastAPI OCR service. If the service is missing or fails, it returns a valid mock OCR result so local development remains usable.

Engine routing:

1. Local development with no `OCR_SERVICE_URL`: mock OCR
2. OCR service default: PaddleOCR
3. Advanced optional request: GLM-OCR
4. Fallback: mock OCR

## Hybrid PDF parser

PDF documents now use a digital-first parser before OCR. DataGate checks whether each PDF page has extractable text with PyMuPDF, calculates page-level quality metrics, and only calls OCR for scanned/image-heavy pages or weak digital extraction.

Each parsed page records:

- selected strategy: `digital`, `ocr`, `hybrid`, or `failed`
- text character count and word count
- table candidate count
- image area ratio
- extraction confidence
- page warnings

If digital text and OCR text are both available, DataGate merges them and keeps provenance metadata in the normalized parser result. Missing optional parser/OCR dependencies return warnings instead of crashing.

## Financial statement extraction

DataGate now adds a financial extraction layer on top of parsed text and tables. For financial statements, it normalizes Mongolian and English accounting labels into lending-ready JSON:

- income statement
- balance sheet
- cash flow
- missing fields
- source references with page number and raw source text/table cell

It handles comma-separated numbers, spaced numbers, negative values in parentheses, and scale words like `мянга`, `сая`, `thousand`, and `million`.

## Why GLM-OCR remains optional

GLM-OCR remains strategically interesting because it is a multimodal OCR/document-understanding model suited to complex scanned documents, mixed layouts, and financial-document semantics. It is not the default practical path yet because local use requires `torch`, compatible `transformers`, model weights, and likely GPU or large-memory CPU execution.

## Why PaddleOCR first

PaddleOCR is mature, open source, and practical for broad OCR/document parsing coverage. DataGate now treats it as the first practical real OCR engine when the OCR service is configured, while still falling back safely when dependencies are missing.

## Why Surya for layout/table fallback

Surya is useful when reading order, layout detection, tables, and low-quality scans matter. DataGate keeps it separate so layout-heavy paths can be routed without forcing every document through a heavier pipeline.

## Setup instructions

Install dependencies with npm:

```bash
npm install
```

## Environment variables

Create `.env.local` when you want real services:

```bash
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
OCR_SERVICE_URL=
OPENAI_API_KEY=
```

`OPENAI_API_KEY` is reserved for future structured extraction. No API key is required for mock mode.

## Running locally

```bash
npm run dev
```

Open `http://localhost:3000`. Without Supabase or OCR env vars, the app runs in local mock mode with demo documents.

## Running OCR microservice

```bash
cd services/ocr-service
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Then set `OCR_SERVICE_URL=http://localhost:8000`.

Install the first real OCR engine path with PaddleOCR:

```bash
cd services/ocr-service
pip install paddleocr paddlepaddle
```

Optional PDF support for PaddleOCR:

```bash
pip install pdf2image
```

`pdf2image` requires Poppler on the host. If PaddleOCR, pdf2image, Poppler, GLM dependencies, or model weights are missing, DataGate returns a normalized fallback response instead of crashing.

Run OCR benchmarks:

```bash
cd services/ocr-service
python benchmark.py --engine paddleocr
python benchmark.py --engine mock
```

Add sample files under `services/ocr-service/samples` first. The benchmark reports filename, engine, processing time, confidence, detected language, text length, warnings, and the first 500 characters of OCR text.

Run fake field extraction evaluation:

```bash
python evaluate_extraction.py --engine mock
python evaluate_extraction.py --engine paddleocr
```

## Supabase setup

1. Create a Supabase project.
2. Run `supabase/migrations/001_init_datagate.sql`.
3. Add `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, and `SUPABASE_SERVICE_ROLE_KEY` to `.env.local`.
4. Restart the Next.js dev server.

The MVP currently stores document metadata and extracted data. File bucket upload is intentionally left as the next integration step.

## Current limitations

- GLM-OCR remains dependency-gated and requires `torch`, compatible `transformers`, and model weights.
- PaddleOCR is integrated as the first real OCR engine path, but local inference requires installing `paddleocr` and `paddlepaddle`.
- Surya remains a placeholder adapter.
- Mock OCR returns deterministic fake Mongolian financial text.
- Supabase file storage bucket upload is not implemented yet.
- Structured extraction is rule-based and tuned to the mock/demo examples.
- Human review is a foundation: status changes and corrected JSON are stored, but reviewer assignment UI is not built yet.

## Mongolian OCR evaluation plan

- Collect 50–100 test documents first.
- Include loan agreements, salary statements, bank statements, invoices, company certificates, and collateral documents.
- Measure character error rate for Mongolian Cyrillic.
- Measure field extraction accuracy for names, amounts, dates, register numbers, company names, account numbers, and interest rates.
- Compare GLM-OCR vs PaddleOCR vs Surya.
- Store human corrections as labels.
- Later fine-tune or build a post-OCR correction model.

## Future roadmap

- Real GLM-OCR integration.
- Real PaddleOCR integration.
- Real Surya integration.
- Mongolian Cyrillic OCR benchmark.
- Human labeling workflow.
- OpenAI-compatible structured extraction.
- Field verification.
- Fraud/anomaly detection.
- Bank/NBFI integrations.
- Underwriting agent integration.
- Enterprise API.
- Audit trail and compliance dashboard.
