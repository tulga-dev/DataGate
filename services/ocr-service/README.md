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
- `paddleocr`: first practical real OCR adapter. If dependencies are missing or inference fails, the response includes warnings and falls back safely.
- `glm_ocr`: optional future adapter path for GLM-OCR when `torch`, compatible `transformers`, and model weights are installed.
- `surya`: placeholder adapter for layout/table fallback.

The heavy adapters intentionally import optional dependencies lazily so local development never breaks.

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

PaddleOCR image files work directly. PDF files require `pdf2image`:

```bash
pip install pdf2image
```

`pdf2image` also requires Poppler to be installed on the host and available on `PATH`. Without `pdf2image` or Poppler, PDF OCR returns a structured warning and falls back safely.

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

## API

`POST /ocr/extract`

Form fields:

- `file`: required multipart file.
- `engine`: optional, defaults to `paddleocr`.
- `fallback_engine`: optional, defaults to `mock`.

Response shape is normalized by `normalize.py` and remains stable across engines.
