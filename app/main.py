import secrets

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile

from .config import OCR_API_KEY, USE_GPU
from .engine import load_image, run_ocr
from .parsers import GAMES, parse
from .schemas import ScanResult

app = FastAPI(title="Collegium OCR", version="0.1.0")


def require_api_key(x_api_key: str = Header(default="")):
    if OCR_API_KEY and not secrets.compare_digest(x_api_key, OCR_API_KEY):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@app.get("/health")
def health():
    return {"status": "ok", "gpu": USE_GPU}


@app.post("/ocr/scan", response_model=ScanResult, dependencies=[Depends(require_api_key)])
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
        image = load_image(data)
        items = run_ocr(image)
        players = parse(normalized, items, image)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"OCR failed: {exc}") from exc

    return ScanResult(game=normalized, players=players)
