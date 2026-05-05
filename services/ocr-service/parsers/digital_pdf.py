from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from typing import Any

from normalize import clamp_confidence


@dataclass
class DigitalPdfPage:
    page_number: int
    raw_text: str
    text_blocks: list[dict[str, Any]] = field(default_factory=list)
    image_area_ratio: float = 0.0
    extraction_confidence: float = 0.0
    warnings: list[str] = field(default_factory=list)


@dataclass
class DigitalPdfResult:
    pages: list[DigitalPdfPage] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    parser_name: str = "pymupdf"
    parser_version: str | None = None


def is_pdf(filename: str, content: bytes) -> bool:
    return filename.lower().endswith(".pdf") or content.startswith(b"%PDF")


def _confidence_for_text(text: str, image_area_ratio: float) -> float:
    char_count = len(text.strip())
    word_count = len(text.split())

    if char_count >= 500 and word_count >= 60:
        base = 0.95
    elif char_count >= 160 and word_count >= 20:
        base = 0.86
    elif char_count >= 50 and word_count >= 8:
        base = 0.66
    elif char_count > 0:
        base = 0.38
    else:
        base = 0.0

    if image_area_ratio > 0.8 and char_count < 80:
        base -= 0.25

    return clamp_confidence(base)


def _extract_image_area_ratio(page: Any) -> float:
    try:
        page_area = max(float(page.rect.width * page.rect.height), 1.0)
        image_area = 0.0
        for image in page.get_images(full=True):
            xref = image[0]
            for rect in page.get_image_rects(xref):
                image_area += float(rect.width * rect.height)
        return clamp_confidence(image_area / page_area)
    except Exception:
        return 0.0


def extract_digital_pdf(filename: str, content: bytes) -> DigitalPdfResult:
    try:
        import fitz
    except Exception:
        return DigitalPdfResult(
            pages=[],
            warnings=[
                "pymupdf_not_installed: install PyMuPDF to enable digital PDF text extraction without OCR."
            ],
            parser_name="pymupdf",
            parser_version=None,
        )

    warnings: list[str] = []
    pages: list[DigitalPdfPage] = []

    try:
        document = fitz.open(stream=BytesIO(content), filetype="pdf")
    except Exception as error:
        return DigitalPdfResult(
            pages=[],
            warnings=[f"digital_pdf_open_failed: {error}"],
            parser_name="pymupdf",
            parser_version=getattr(fitz, "__doc__", None),
        )

    for index, page in enumerate(document, start=1):
        page_warnings: list[str] = []
        try:
            raw_text = page.get_text("text").strip()
        except Exception as error:
            raw_text = ""
            page_warnings.append(f"digital_text_failed: {error}")

        text_blocks: list[dict[str, Any]] = []
        try:
            for block in page.get_text("blocks"):
                if len(block) >= 5:
                    text_blocks.append(
                        {
                            "bbox": [float(block[0]), float(block[1]), float(block[2]), float(block[3])],
                            "text": str(block[4]).strip(),
                            "source": "pymupdf",
                        }
                    )
        except Exception as error:
            page_warnings.append(f"digital_blocks_failed: {error}")

        image_area_ratio = _extract_image_area_ratio(page)
        pages.append(
            DigitalPdfPage(
                page_number=index,
                raw_text=raw_text,
                text_blocks=text_blocks,
                image_area_ratio=image_area_ratio,
                extraction_confidence=_confidence_for_text(raw_text, image_area_ratio),
                warnings=page_warnings,
            )
        )

    if not pages:
        warnings.append("digital_pdf_no_pages: PyMuPDF opened the PDF but returned no pages.")

    return DigitalPdfResult(
        pages=pages,
        warnings=warnings,
        parser_name="pymupdf",
        parser_version=getattr(fitz, "VersionBind", None),
    )
