# DataGate OCR Service

FastAPI OCR extraction service behind the Next.js app. The service defaults to PaddleOCR when called without an engine and falls back safely to mock OCR when heavy dependencies are missing.

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
- `paddleocr`: first practical real OCR adapter. If dependencies are missing or inference fails, the response includes warnings and falls back safely.
- `glm_ocr`: optional future adapter path for GLM-OCR when `torch`, compatible `transformers`, and model weights are installed.
- `surya`: placeholder adapter for layout/table fallback.

The heavy adapters intentionally import optional dependencies lazily so local development never breaks.

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

The digital parser uses PyMuPDF and is included in the base requirements. PaddleOCR image files work directly. OCR for image-only PDF files requires `pdf2image`:

```bash
pip install pdf2image
```

`pdf2image` also requires Poppler to be installed on the host and available on `PATH`. Without `pdf2image` or Poppler, PDF OCR returns a structured warning and falls back safely.

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

## API

`POST /ocr/extract`

Form fields:

- `file`: required multipart file.
- `engine`: optional, defaults to `paddleocr`.
- `fallback_engine`: optional, defaults to `mock`.

Response shape is normalized by `normalize.py` and remains stable across engines.
