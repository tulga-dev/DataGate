from __future__ import annotations

import importlib.metadata
import os
from io import BytesIO
from time import perf_counter

from PIL import Image

from engines.common import build_ocr_result
from engines.mock import extract_with_mock


def extract_with_glm_ocr(filename: str, content: bytes) -> dict:
    started = perf_counter()
    try:
        import torch
        from transformers import AutoModelForImageTextToText, AutoProcessor

        transformers_version = importlib.metadata.version("transformers")
    except Exception:
        result = extract_with_mock(filename, content)
        result["engine"] = "glm_ocr"
        result["engineVersion"] = "not-installed"
        result["warnings"] = [
            "glm_ocr_not_installed: GLM-OCR requires torch, compatible transformers, and model weights."
        ]
        result["fallbackUsed"] = True
        result["fallbackReason"] = "GLM-OCR dependencies are not installed."
        return result

    try:
        image = Image.open(BytesIO(content)).convert("RGB")
        model_id = os.getenv("GLM_OCR_MODEL_ID", "zai-org/GLM-OCR")
        prompt = os.getenv("GLM_OCR_PROMPT", "Text Recognition:")
        processor = AutoProcessor.from_pretrained(model_id)
        model = AutoModelForImageTextToText.from_pretrained(
            model_id,
            torch_dtype="auto",
            device_map=os.getenv("GLM_OCR_DEVICE_MAP", "auto"),
        )
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": prompt},
                ],
            }
        ]
        inputs = processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt",
        ).to(model.device)
        inputs.pop("token_type_ids", None)
        output = model.generate(**inputs, max_new_tokens=int(os.getenv("GLM_OCR_MAX_NEW_TOKENS", "1024")))
        prompt_length = inputs["input_ids"].shape[1]
        raw_text = processor.decode(output[0][prompt_length:], skip_special_tokens=True).strip()

        return build_ocr_result(
            engine="glm_ocr",
            engine_version=f"transformers-{transformers_version}",
            raw_text=raw_text,
            confidence=0.82 if raw_text else 0.0,
            started_at=started,
            warnings=[] if raw_text else ["ocr_empty_result: GLM-OCR returned no text."],
        )
    except Exception as error:
        result = extract_with_mock(filename, content)
        result["engine"] = "glm_ocr"
        result["engineVersion"] = f"transformers-{transformers_version}"
        result["warnings"] = [f"glm_ocr_runtime_error: {error}"]
        result["fallbackUsed"] = True
        result["fallbackReason"] = "GLM-OCR failed at runtime; returned mock OCR text."
        return result
