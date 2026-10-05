import os


def _as_bool(value: str) -> bool:
    return value.strip().lower() in ("1", "true", "yes", "on")


USE_GPU = _as_bool(os.getenv("USE_GPU", "false"))
PORT = int(os.getenv("PORT", "8000"))
# When set, /ocr/scan requires this value on the X-API-Key header — this
# service is server-to-server only (called by collegium-server) and has no
# other access control, so a public deploy without this is open to anyone.
OCR_API_KEY = os.getenv("OCR_API_KEY", "")
