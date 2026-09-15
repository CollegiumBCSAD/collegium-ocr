from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from .config import USE_GPU
from .engine import run_ocr
from .parsers import GAMES, parse
from .schemas import ScanResult

app = FastAPI(title="Collegium OCR", version="0.1.0")


@app.get("/health")
def health():
    return {"status": "ok", "gpu": USE_GPU}


@app.post("/ocr/scan", response_model=ScanResult)
async def scan(game: str = Form(...), image: UploadFile = File(...)):
    normalized = game.strip().upper()
    if normalized not in GAMES:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported game '{game}'. Expected one of {sorted(GAMES)}.",
        )

    content_type = image.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="Uploaded file must be an image")

    data = await image.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded image is empty")

    try:
        items = run_ocr(data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"OCR failed: {exc}") from exc

    return ScanResult(game=normalized, players=parse(normalized, items))
