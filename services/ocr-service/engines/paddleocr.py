from __future__ import annotations

import importlib.metadata
import os
from pathlib import Path
from time import perf_counter
from typing import Any

from engines.common import temp_document_path
from engines.mock import extract_with_mock
from normalize import NormalizedPage, average, collect_text_and_scores, normalize_ocr_response


def _prepare_paddle_environment() -> None:
    workspace_cache = Path.cwd().parents[1] / ".cache" / "paddlex"
    os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(workspace_cache))
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
    # Windows CPU runs can hit oneDNN PIR conversion gaps in Paddle 3.x.
    # Keep real OCR enabled but prefer the plain CPU executor.
    os.environ.setdefault("FLAGS_use_mkldnn", "0")
    os.environ.setdefault("FLAGS_use_onednn", "0")


def _create_paddleocr():
    _prepare_paddle_environment()
    from paddleocr import PaddleOCR

    options: dict[str, Any] = {
        "use_doc_orientation_classify": False,
        "use_doc_unwarping": False,
        "use_textline_orientation": False,
        "device": os.getenv("PADDLEOCR_DEVICE", "cpu"),
    }
    lang = os.getenv("PADDLEOCR_LANG")
    version = os.getenv("PADDLEOCR_VERSION")

    if lang:
        options["lang"] = lang
    if version:
        options["ocr_version"] = version

    det_model = os.getenv("PADDLEOCR_DET_MODEL", "PP-OCRv5_mobile_det")
    rec_model = os.getenv("PADDLEOCR_REC_MODEL", "PP-OCRv5_mobile_rec")
    options["text_detection_model_name"] = det_model
    options["text_recognition_model_name"] = rec_model

    try:
        return PaddleOCR(**options)
    except TypeError:
        legacy_options: dict[str, Any] = {
            "use_angle_cls": False,
            "lang": lang or "en",
        }
        return PaddleOCR(**legacy_options)


def _is_pdf(filename: str, content: bytes) -> bool:
    return Path(filename).suffix.lower() == ".pdf" or content.startswith(b"%PDF")


def _pdf_pages_to_images(content: bytes) -> tuple[list[Any], list[str]]:
    warnings: list[str] = []

    try:
        from pdf2image import convert_from_bytes

        return convert_from_bytes(content), warnings
    except ImportError:
        warnings.append("pdf2image_not_installed: using pypdfium2 PDF rendering fallback.")
    except Exception as error:
        warnings.append(f"pdf2image_failed: using pypdfium2 PDF rendering fallback. Detail: {error}")

    try:
        import pypdfium2 as pdfium

        document = pdfium.PdfDocument(content)
        images = []
        for page in document:
            bitmap = page.render(scale=2)
            images.append(bitmap.to_pil())
        return images, warnings
    except ImportError as error:
        warnings.append(f"pypdfium2_not_installed: install pdf2image with Poppler or pypdfium2. Detail: {error}")
    except Exception as error:
        warnings.append(f"pypdfium2_pdf_render_failed: {error}")

    return [], warnings


def _run_paddleocr_on_path(ocr: Any, input_path: Path) -> tuple[str, float]:
    if hasattr(ocr, "predict"):
        raw_result = ocr.predict(str(input_path))
    else:
        raw_result = ocr.ocr(str(input_path), cls=False)

    texts, scores = collect_text_and_scores(raw_result)
    deduped_text = "\n".join(dict.fromkeys(texts)).strip()
    return deduped_text, average(scores)


def _mock_fallback(filename: str, content: bytes, *, version: str, warning: str, reason: str) -> dict:
    result = extract_with_mock(filename, content)
    result["engine"] = "paddleocr"
    result["engineVersion"] = version
    result["warnings"] = [warning]
    result["fallbackUsed"] = True
    result["fallbackReason"] = reason
    return result


def extract_with_paddleocr(filename: str, content: bytes) -> dict:
    started = perf_counter()

    try:
        version = importlib.metadata.version("paddleocr")
    except importlib.metadata.PackageNotFoundError:
        return _mock_fallback(
            filename,
            content,
            version="not-installed",
            warning="paddleocr_not_installed: install paddleocr and paddlepaddle to enable real PaddleOCR inference.",
            reason="PaddleOCR package is not installed.",
        )

    try:
        ocr = _create_paddleocr()
        pages: list[NormalizedPage] = []

        if _is_pdf(filename, content):
            images, pdf_warnings = _pdf_pages_to_images(content)
            if not images:
                return _mock_fallback(
                    filename,
                    content,
                    version=version,
                    warning="; ".join(pdf_warnings) or "pdf_conversion_failed: PDF pages could not be rendered for OCR.",
                    reason="PDF conversion failed before PaddleOCR inference.",
                )

            for index, image in enumerate(images, start=1):
                with temp_document_path(f"{Path(filename).stem}-page-{index}.png", b"") as page_path:
                    image.save(page_path, format="PNG")
                    text, page_confidence = _run_paddleocr_on_path(ocr, page_path)
                pages.append(NormalizedPage(page_number=index, text=text, confidence=page_confidence))
        else:
            with temp_document_path(filename, content) as input_path:
                text, page_confidence = _run_paddleocr_on_path(ocr, input_path)
            pages.append(NormalizedPage(page_number=1, text=text, confidence=page_confidence))

        raw_text = "\n\n".join(page.text for page in pages if page.text).strip()
        confidence = average([page.confidence for page in pages])
        warnings: list[str] = []
        if _is_pdf(filename, content):
            warnings.extend(pdf_warnings)

        if not raw_text:
            warnings.append("no_text_detected: PaddleOCR returned no recognized text.")
        if raw_text and confidence < 0.65:
            warnings.append("low_confidence_ocr: PaddleOCR confidence is below 0.65.")

        return normalize_ocr_response(
            engine="paddleocr",
            engine_version=version,
            pages=pages,
            confidence=confidence,
            started_at=started,
            warnings=warnings,
        )
    except Exception as error:
        return _mock_fallback(
            filename,
            content,
            version=version,
            warning=f"paddleocr_runtime_error: {error}",
            reason="PaddleOCR failed at runtime.",
        )
