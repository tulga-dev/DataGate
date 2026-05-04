from engines.mock import extract_with_mock


def extract_with_surya(filename: str, content: bytes) -> dict:
    # TODO: Integrate Surya for layout, table recognition, and reading-order fallback.
    # Surya remains optional because model downloads are too heavy for first-pass local setup.
    result = extract_with_mock(filename, content)
    result["engine"] = "surya"
    result["engineVersion"] = "placeholder"
    result["warnings"] = [
        "engine_not_installed: Surya adapter is a placeholder; returned mock OCR text."
    ]
    result["fallbackUsed"] = True
    result["fallbackReason"] = "Surya dependencies are not installed."
    return result
