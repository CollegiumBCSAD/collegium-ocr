import os


def _as_bool(value: str) -> bool:
    return value.strip().lower() in ("1", "true", "yes", "on")


USE_GPU = _as_bool(os.getenv("USE_GPU", "false"))
PORT = int(os.getenv("PORT", "8000"))
