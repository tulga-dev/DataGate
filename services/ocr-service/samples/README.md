# DataGate OCR Samples

Place sample PDF or image files in this folder to run OCR benchmarks.

Recommended sample categories:

- Mongolian loan agreement
- Mongolian bank statement
- Mongolian salary statement
- Mongolian invoice or receipt
- Company certificate
- Collateral document

Supported file types:

- `.pdf`
- `.png`
- `.jpg`
- `.jpeg`
- `.tif`
- `.tiff`
- `.bmp`
- `.webp`

Run:

```bash
python benchmark.py --engine paddleocr
python benchmark.py --engine mock
```
