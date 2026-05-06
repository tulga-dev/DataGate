from __future__ import annotations

import sys
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1] / "services" / "ocr-service"
sys.path.insert(0, str(SERVICE_ROOT))

from main import app  # noqa: E402
