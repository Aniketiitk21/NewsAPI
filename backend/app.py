# backend/app.py

import os
import pathlib
import uvicorn
from typing import Optional, List, Dict

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware

from backend.aggregator.fetch import get_news
from backend.aggregator.utils import safe_int

APP_NAME = os.getenv("APP_NAME", "NewsLens")
ENV = os.getenv("ENV", "prod")

app = FastAPI(title=f"{APP_NAME} API", version="1.1.1")

# ---- Disable cache for /assets so app.js updates always load ----
class NoCacheAssets(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        resp = await call_next(request)
        if request.url.path.startswith("/assets/"):
            resp.headers["Cache-Control"] = "no-store"
        return resp

app.add_middleware(NoCacheAssets)

# ---- Serve the frontend ----
ROOT = pathlib.Path(__file__).resolve().parents[1] / "frontend"
ASSETS_DIR = ROOT / "assets"
INDEX_HTML = ROOT / "index.html"
FAVICON = ROOT / "favicon.ico"

if ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

@app.get("/", include_in_schema=False)
def index():
    if INDEX_HTML.exists():
        return FileResponse(INDEX_HTML)
    return {"message": "Frontend not found. Put index.html in /frontend."}

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    if FAVICON.exists():
        return FileResponse(FAVICON)
    return FileResponse(INDEX_HTML) if INDEX_HTML.exists() else {"ok": True}

# ---- CORS: allow everything (safe for GET-only API). Tighten later if needed. ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],            # wide open for simplicity
    allow_origin_regex=".*",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Models ----
class NewsResponse(BaseModel):
    items: List[Dict]

# ---- Health ----
@app.get("/healthz")
def healthz():
    return {"ok": True, "service": APP_NAME}

# ---- API ----
@app.get("/api/news", response_model=NewsResponse)
def api_news(
    scope: str = Query("national", pattern="^(national|state)$"),
    state: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    days: int = Query(2, ge=1, le=7),
    limit: int = Query(60, ge=1, le=120),
    fetch_mode: str = Query("light", pattern="^(light|deep)$"),
):
    try:
        if scope == "state" and not state:
            raise HTTPException(status_code=400, detail="Provide 'state' when scope='state'.")
        items = get_news(scope, state, category, days, limit, fetch_mode)
        return {"items": items}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch news") from e

if __name__ == "__main__":
    uvicorn.run(
        "backend.app:app",
        host="0.0.0.0",
        port=safe_int(os.getenv("PORT", 8000)),
        reload=(ENV == "dev"),
    )
