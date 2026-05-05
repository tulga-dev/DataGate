# DataGate Parser Benchmark Fixtures

Place real benchmark documents in this folder as they become available.

Target real PDF filenames:

- `digital_financial_statement_mn.pdf`
- `scanned_financial_statement_mn.pdf`
- `bank_statement_mn.pdf`
- `bad_quality_scan.pdf`

The repository currently includes lightweight `.mock.json` fixtures so the benchmark can run without OCR, PyMuPDF, Poppler, or PaddleOCR dependencies. Each mock fixture contains the normalized parser pages DataGate expects after parsing/OCR.

Mock fixture format:

```json
{
  "document_name": "digital_financial_statement_mn",
  "parser_result": {
    "document_id": "fixture:digital_financial_statement_mn",
    "document_type": "financial_statement",
    "pages": [
      {
        "page_number": 1,
        "strategy": "digital",
        "text_blocks": [],
        "tables": [],
        "raw_text": "Revenue: 1000000 MNT",
        "confidence": 0.95,
        "warnings": [],
        "metrics": {}
      }
    ],
    "global_warnings": [],
    "parser_version": "fixture-v1"
  }
}
```
