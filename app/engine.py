import io
from functools import lru_cache

import numpy as np
from PIL import Image

from .config import USE_GPU


@lru_cache(maxsize=1)
def get_engine():
    from rapidocr_onnxruntime import RapidOCR

    if USE_GPU:
        for kwargs in (
            {"det_use_cuda": True, "cls_use_cuda": True, "rec_use_cuda": True},
            {"use_cuda": True},
        ):
            try:
                return RapidOCR(**kwargs)
            except TypeError:
                continue
    return RapidOCR()


def load_image(image_bytes: bytes) -> np.ndarray:
    return np.array(Image.open(io.BytesIO(image_bytes)).convert("RGB"))


def run_ocr(image: np.ndarray):
    result, _ = get_engine()(image)
    items = []
    for entry in result or []:
        box = entry[0]
        text = entry[1]
        score = entry[2] if len(entry) > 2 else 1.0
        items.append((box, text, score))
    return items


def read_text(image: np.ndarray) -> str:
    result, _ = get_engine()(image, use_det=False, use_cls=False, use_rec=True)
    return result[0][0] if result else ""
