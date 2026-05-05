from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from typing import Any

from engines.common import temp_document_path


@dataclass
class TableExtractionResult:
    tables_by_page: dict[int, list[dict[str, Any]]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def _normalized_table(page_number: int, rows: list[list[Any]], source: str) -> dict[str, Any]:
    columns = [str(value) if value is not None else "" for value in rows[0]] if rows else []
    data_rows = rows[1:] if rows else []
    return {
        "page_number": page_number,
        "rows": data_rows,
        "columns": columns,
        "bbox": None,
        "confidence": None,
        "source": source,
    }


def extract_tables(filename: str, content: bytes) -> TableExtractionResult:
    try:
        import pdfplumber
    except Exception:
        return TableExtractionResult(
            warnings=[
                "table_extractor_unavailable: install pdfplumber or Camelot to enable table extraction hooks."
            ]
        )

    try:
        tables_by_page: dict[int, list[dict[str, Any]]] = {}
        with pdfplumber.open(BytesIO(content)) as pdf:
            for index, page in enumerate(pdf.pages, start=1):
                normalized_tables = []
                for table in page.extract_tables() or []:
                    normalized_tables.append(_normalized_table(index, table or [], "pdfplumber"))
                tables_by_page[index] = normalized_tables
        return TableExtractionResult(tables_by_page=tables_by_page)
    except Exception as pdfplumber_error:
        try:
            import camelot
        except Exception:
            return TableExtractionResult(
                warnings=[
                    f"table_extraction_failed: pdfplumber failed ({pdfplumber_error}); Camelot is unavailable."
                ]
            )

        try:
            tables_by_page: dict[int, list[dict[str, Any]]] = {}
            with temp_document_path(filename, content) as pdf_path:
                camelot_tables = camelot.read_pdf(str(pdf_path), pages="all")
                for table in camelot_tables:
                    page_number = int(getattr(table, "page", 1))
                    rows = table.df.values.tolist()
                    tables_by_page.setdefault(page_number, []).append(_normalized_table(page_number, rows, "camelot"))
            return TableExtractionResult(tables_by_page=tables_by_page)
        except Exception as camelot_error:
            return TableExtractionResult(
                warnings=[
                    f"table_extraction_failed: pdfplumber failed ({pdfplumber_error}); Camelot failed ({camelot_error})."
                ]
            )
