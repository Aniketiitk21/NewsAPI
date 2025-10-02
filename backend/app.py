# backend/app.py

import os
import pathlib
import re
import uvicorn
from typing import Optional, List, Dict, Any
from collections import Counter

from fastapi import FastAPI, Query, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware

from backend.aggregator.fetch import get_news
from backend.aggregator.utils import safe_int

APP_NAME = os.getenv("APP_NAME", "NewsLens")
ENV = os.getenv("ENV", "prod")

app = FastAPI(title=f"{APP_NAME} API", version="2.0.0")

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

# ---- CORS (wide-open; safe as we only expose GETs) ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_origin_regex=".*",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Models ----
class NewsResponse(BaseModel):
    items: List[Dict[str, Any]]

# ---- Health ----
@app.get("/healthz")
def healthz():
    return {"ok": True, "service": APP_NAME}

# ---- Existing API (kept as-is) ----
@app.get("/api/news", response_model=NewsResponse)
def api_news(
    scope: str = Query("national", pattern="^(national|state)$"),
    state: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    days: int = Query(2, ge=1, le=7),
    limit: int = Query(60, ge=1, le=120),
    fetch_mode: str = Query("light", pattern="^(light|deep)$")
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

# ========== New endpoints powering Home / Search / Trending / Entity / Digest ==========

STOPWORDS = set("""
a an and are as at be by for from has have he her his i in is it its of on or our so
that the their them there they this to was were will with you your
""".split())

WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9\-\&]{2,}")

def _extract_terms(title: str, summary: str) -> List[str]:
    blob = f"{title or ''} {summary or ''}"
    words = WORD_RE.findall(blob)
    terms = []
    for w in words:
        u = w.strip().title()
        if len(u) < 3: 
            continue
        if u.lower() in STOPWORDS:
            continue
        terms.append(u)
    return terms

def _filter_items(items: List[Dict[str, Any]], q: Optional[str]) -> List[Dict[str, Any]]:
    if not q:
        return items
    needle = q.strip().lower()
    out = []
    for it in items:
        txt = f"{it.get('title','')} {it.get('summary','')} {it.get('source','')}".lower()
        if needle in txt:
            out.append(it)
    return out

@app.get("/api/signals/top5", response_model=NewsResponse)
def api_top5(days: int = Query(2, ge=1, le=7)):
    """
    Pick the most important 5 signals from national feed for the given window.
    Heuristics: recency + light category diversity if possible.
    """
    base = get_news("national", None, None, days, 120, "light")  # wide, then select
    # group by simple buckets to diversify
    buckets = {
        "finance": [],
        "education": [],
        "sports": [],
        "tech": [],
        "general": [],
    }
    for it in base:
        cat = (it.get("category") or "all").lower()
        if "business" in cat or "finance" in cat or "ipo" in it.get("title","").lower():
            buckets["finance"].append(it)
        elif "education" in cat or "exam" in it.get("title","").lower():
            buckets["education"].append(it)
        elif "sport" in cat or "cricket" in it.get("title","").lower():
            buckets["sports"].append(it)
        elif "science" in cat or "tech" in cat or "ai " in it.get("title","").lower():
            buckets["tech"].append(it)
        else:
            buckets["general"].append(it)
    # build top5 with diversity
    order = ["finance","education","sports","tech","general"]
    picked: List[Dict[str,Any]] = []
    # one pass to ensure 1 per bucket if available
    for key in order:
        if buckets[key]:
            picked.append(buckets[key][0])
        if len(picked) == 5: break
    # fill remaining by recency
    if len(picked) < 5:
        seen = set(x["url"] for x in picked)
        for it in base:
            if it["url"] in seen: 
                continue
            picked.append(it)
            if len(picked) == 5:
                break
    return {"items": picked}

@app.get("/api/search", response_model=NewsResponse)
def api_search(q: str = Query(..., min_length=2), days: int = Query(7, ge=1, le=14), limit: int = 120):
    base = get_news("national", None, None, days, limit, "light")
    out = _filter_items(base, q)
    return {"items": out[:60]}

class TrendingResponse(BaseModel):
    terms: List[Dict[str, Any]]

@app.get("/api/trending", response_model=TrendingResponse)
def api_trending(days: int = Query(2, ge=1, le=7), limit: int = 120):
    base = get_news("national", None, None, days, limit, "light")
    c = Counter()
    for it in base:
        terms = _extract_terms(it.get("title",""), it.get("summary",""))
        c.update(terms)
    top = [{"term": k, "count": v} for k, v in c.most_common(25)]
    return {"terms": top}

@app.get("/api/entity", response_model=NewsResponse)
def api_entity(term: str = Query(..., min_length=2), days: int = Query(14, ge=1, le=30), limit: int = 200):
    base = get_news("national", None, None, days, limit, "light")
    out = _filter_items(base, term)
    # sort by published_at desc (already), return up to 80
    return {"items": out[:80]}

@app.get("/api/digest", response_model=NewsResponse)
def api_digest(follow: str = Query("", description="Comma separated terms user follows"),
               days: int = Query(2, ge=1, le=14), limit: int = 200):
    """
    Personalized digest based on a simple 'follow' list passed by the client (localStorage).
    No auth, privacy-friendly. If empty, return top recent items.
    """
    base = get_news("national", None, None, days, limit, "light")
    follows = [t.strip() for t in follow.split(",") if t.strip()]
    if not follows:
        return {"items": base[:30]}
    hits: List[Dict[str,Any]] = []
    lo = [f.lower() for f in follows]
    for it in base:
        blob = f"{it.get('title','')} {it.get('summary','')} {it.get('source','')}".lower()
        if any(t in blob for t in lo):
            hits.append(it)
    # de-dupe by url
    seen = set()
    uniq = []
    for it in hits:
        u = it["url"]
        if u in seen: 
            continue
        seen.add(u)
        uniq.append(it)
    return {"items": uniq[:40]}

# ---- Optional: topic RSS feed (kept from earlier suggestion) ----
from datetime import datetime, timezone
@app.get("/feed/{topic}.xml", include_in_schema=False)
def feed(topic: str):
    items = get_news("national", None, topic if topic!="all" else None, days=2, limit=50, fetch_mode="light")
    xml_items = []
    for it in items:
        pub = it.get("published_at") or datetime.now(timezone.utc).isoformat()
        xml_items.append(f"""
        <item>
          <title>{it['title']}</title>
          <link>{it['url']}</link>
          <pubDate>{pub}</pubDate>
          <description><![CDATA[{it.get('summary','')}]]></description>
        </item>""")
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0"><channel>
      <title>NewsLens – {topic}</title>
      <link>/feed/{topic}.xml</link>
      <description>Latest summaries for {topic}</description>
      {''.join(xml_items)}
    </channel></rss>"""
    return Response(content=xml, media_type="application/rss+xml")

# ---- Entrypoint ----
if __name__ == "__main__":
    uvicorn.run(
        "backend.app:app",
        host="0.0.0.0",
        port=safe_int(os.getenv("PORT", 8000)),
        reload=(ENV == "dev"),
    )
