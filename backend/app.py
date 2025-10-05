# backend/app.py
import os
import pathlib
import re
import uvicorn
from typing import Optional, List, Dict, Any
from collections import Counter
from datetime import datetime, timezone

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware

from backend.aggregator.fetch import get_news
from backend.aggregator.utils import safe_int

# ---- NEW: httpx for live Shloka fetch ----
import httpx

APP_NAME = os.getenv("APP_NAME", "NewsLens")
ENV = os.getenv("ENV", "prod")

app = FastAPI(title=f"{APP_NAME} API", version="2.3.0")

# ---- No-cache assets (so app.js & CSS refresh instantly) --------------------
class NoCacheAssets(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        resp = await call_next(request)
        if request.url.path.startswith("/assets/"):
            resp.headers["Cache-Control"] = "no-store"
        return resp

app.add_middleware(NoCacheAssets)

# ---- Serve the frontend -----------------------------------------------------
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

# ---- CORS (GET-only; safe for public) --------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_origin_regex=".*",
    allow_credentials=False,
    allow_methods=["GET", "HEAD", "OPTIONS"],
    allow_headers=["*"],
)

# ---- Models -----------------------------------------------------------------
class NewsResponse(BaseModel):
    items: List[Dict[str, Any]]

class TrendingResponse(BaseModel):
    terms: List[Dict[str, Any]]

# ---- Health -----------------------------------------------------------------
@app.get("/healthz")
def healthz():
    return {"ok": True, "service": APP_NAME}

# ---- Main news API ----------------------------------------------------------
@app.get("/api/news", response_model=NewsResponse)
def api_news(
    scope: str = Query("national", pattern="^(national|state)$"),
    state: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    days: int = Query(2, ge=1, le=14),
    limit: int = Query(60, ge=1, le=200),
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

# ========== Discovery endpoints used by the new UI ===========================
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
def api_top5(days: int = Query(2, ge=1, le=14)):
    """Pick a diversified 5 from national feed for Home."""
    base = get_news("national", None, None, days, 150, "light")
    buckets = {"finance": [], "education": [], "sports": [], "tech": [], "general": []}
    for it in base:
        title = (it.get("title") or "").lower()
        cat = (it.get("category") or "all").lower()
        if "business" in cat or "finance" in cat or "ipo" in title or "rbi" in title:
            buckets["finance"].append(it)
        elif "education" in cat or "exam" in title or "jee" in title or "neet" in title:
            buckets["education"].append(it)
        elif "sport" in cat or "cricket" in title or "match" in title:
            buckets["sports"].append(it)
        elif "science" in cat or "tech" in cat or " ai " in f" {title} " or "isro" in title:
            buckets["tech"].append(it)
        else:
            buckets["general"].append(it)

    picked: List[Dict[str,Any]] = []
    for key in ["finance","education","sports","tech","general"]:
        if buckets[key]:
            picked.append(buckets[key][0])
        if len(picked) == 5:
            break

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
def api_search(q: str = Query(..., min_length=2), days: int = Query(7, ge=1, le=14), limit: int = 150):
    base = get_news("national", None, None, days, limit, "light")
    out = _filter_items(base, q)
    return {"items": out[:80]}

@app.get("/api/trending", response_model=TrendingResponse)
def api_trending(days: int = Query(2, ge=1, le=14), limit: int = 150):
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
    return {"items": out[:100]}

@app.get("/api/digest", response_model=NewsResponse)
def api_digest(follow: str = Query("", description="Comma separated follow terms"),
               days: int = Query(2, ge=1, le=14), limit: int = 200):
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
    seen, uniq = set(), []
    for it in hits:
        u = it["url"]
        if u in seen:
            continue
        seen.add(u)
        uniq.append(it)
    return {"items": uniq[:60]}

# ---- Topic feeds (RSS) ------------------------------------------------------
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

# ---- Shloka of the Day from authentic source -------------------------------
# We cycle deterministically through all 700 verses to avoid 404s on chapters
# with fewer verses, then fetch the selected verse from bhagavadgitaapi.in.
# Optional override:
#   SHLOKA_API_URL = "https://bhagavadgitaapi.in/slok"
SHLOKA_API_BASE = os.getenv("SHLOKA_API_URL", "https://bhagavadgitaapi.in/slok")

# Verses per chapter (1..18) = 700 total
CH_VERSE_COUNTS = [
    47, 72, 43, 42, 29, 47, 30, 28, 34,
    42, 55, 20, 35, 27, 20, 24, 28, 78
]
CH_CUMSUM = []
_total = 0
for c in CH_VERSE_COUNTS:
    _total += c
    CH_CUMSUM.append(_total)  # cumulative totals; last == 700

def _pick_daily_chapter_verse(day_index: int) -> (int, int):
    """Map a day index -> (chapter, verse), covering all 700 verses in a loop."""
    total = CH_CUMSUM[-1]  # 700
    # 1..700
    k = (day_index % total) + 1
    # find chapter
    ch = 1
    prev = 0
    for i, csum in enumerate(CH_CUMSUM, start=1):
        if k <= csum:
            ch = i
            prev = CH_CUMSUM[i-2] if i > 1 else 0
            break
    v = k - prev
    return ch, v

@app.get("/api/shloka/daily")
def shloka_daily():
    """
    Deterministic daily shloka:
      - Computes (chapter, verse) from current day number covering all 700 verses.
      - Fetches verse from bhagavadgitaapi.in (authentic source).
      - Gracefully falls back by trying next verses if a particular verse 404s.
    """
    try:
        # Day index based on UTC days since epoch (stable across users)
        day_index = int(datetime.now(timezone.utc).timestamp()) // 86400
        ch, v = _pick_daily_chapter_verse(day_index)

        # Try up to 3 consecutive verses in case one endpoint is missing
        for offset in range(3):
            ch_try, v_try = ch, v + offset
            # if verse exceeds the chapter's verse count, wrap to next chapter
            if v_try > CH_VERSE_COUNTS[ch_try - 1]:
                ch_try += 1
                if ch_try > 18:
                    ch_try = 1
                v_try = 1

            url = f"{SHLOKA_API_BASE}/{ch_try}/{v_try}/"
            r = httpx.get(url, timeout=8.0)
            if r.status_code == 200:
                data = r.json()
                # translation keys can vary; prefer 'translation', fallback to others if present
                tr = (
                    data.get("translation")
                    or data.get("en")
                    or data.get("tej")
                    or data.get("siva")
                    or "—"
                )
                return {
                    "ref": f"{data.get('chapter', ch_try)}.{data.get('verse', v_try)}",
                    "dev": data.get("slok"),
                    "tr": tr
                }

        # Upstream failed repeatedly
        raise RuntimeError("shloka upstream unavailable")
    except Exception:
        # Soft fallback: a very common verse; still avoid hardcoding list
        return {
            "ref": "2.47",
            "dev": "कर्मण्येवाधिकारस्ते मा फलेषु कदाचन ।",
            "tr": "You have a right to action alone, not to its fruits."
        }

# ---- Entrypoint -------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run(
        "backend.app:app",
        host="0.0.0.0",
        port=safe_int(os.getenv("PORT", 8000)),
        reload=(ENV == "dev"),
    )
