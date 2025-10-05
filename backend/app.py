import os
import pathlib
import re
import uvicorn
import random
from typing import Optional, List, Dict, Any
from collections import Counter
from datetime import datetime, timezone, timedelta

# feedparser is already used elsewhere; keep it
import feedparser

from fastapi import FastAPI, Query, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response, JSONResponse
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware

from backend.aggregator.fetch import get_news
from backend.aggregator.utils import safe_int, strip_html
from backend.aggregator.summarize import summarize_rule_based

APP_NAME = os.getenv("APP_NAME", "NewsLens")
ENV = os.getenv("ENV", "prod")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

app = FastAPI(title=f"{APP_NAME} API", version="2.4.1")

# ---------- no-cache for static assets ----------
class NoCacheAssets(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        resp = await call_next(request)
        if request.url.path.startswith("/assets/"):
            resp.headers["Cache-Control"] = "no-store"
        return resp

app.add_middleware(NoCacheAssets)

# ---------- static / frontend ----------
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

# ---------- CORS ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_origin_regex=".*",
    allow_credentials=False,
    allow_methods=["GET", "HEAD", "OPTIONS", "POST"],
    allow_headers=["*"],
)

# ---------- models ----------
class NewsResponse(BaseModel):
    items: List[Dict[str, Any]]

class TrendingResponse(BaseModel):
    terms: List[Dict[str, Any]]

class ChatIn(BaseModel):
    message: str

# ---------- health ----------
@app.get("/healthz")
def healthz():
    return {"ok": True, "service": APP_NAME}

# ---------- main news ----------
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

# ---------- discovery endpoints ----------
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
        if len(picked) == 5: break
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
    seen, uniq = set(), []
    for it in hits:
        u = it["url"]
        if u in seen:
            continue
        seen.add(u)
        uniq.append(it)
    return {"items": uniq[:60]}

# ---------- RSS → curated topics ----------
CURATED_FEEDS: Dict[str, List[str]] = {
    "finance": [
        "https://www.moneycontrol.com/rss/MCtopnews.xml",
        "https://www.livemint.com/rss/markets",
        "https://www.financialexpress.com/feed/",
        "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    ],
    "startup": [
        "https://inc42.com/feed/",
        "https://yourstory.com/feed",
        "https://techcrunch.com/startups/feed/",
        "https://the-ken.com/feed/",
    ],
    "ai": [
        "https://www.analyticsindiamag.com/feed/",
        "https://ai.googleblog.com/atom.xml",
        "https://openaccess.thecvf.com/rss.xml",
        "https://arxiv.org/rss/cs.CV",
    ],
}

def _parse_pub(entry):
    t = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if not t: return None
    try:
        return datetime(*t[:6], tzinfo=timezone.utc).isoformat()
    except Exception:
        return None

def _rss_curated(topic: str, days: int, limit: int) -> List[Dict[str, Any]]:
    urls = CURATED_FEEDS.get(topic, [])
    out: List[Dict[str,Any]] = []
    seen = set()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    for url in urls:
        try:
            feed = feedparser.parse(url)
            entries = getattr(feed, "entries", [])[:120]
            src = ""
            try: src = feed.feed.get("title","")
            except: pass
            for e in entries:
                link = (e.get("link") or "").strip()
                title = (e.get("title") or "").strip()
                if not link or not title: continue
                norm = link.split("?",1)[0].rstrip("/")
                if norm in seen: continue
                pub = _parse_pub(e)
                if pub:
                    try:
                        if datetime.fromisoformat(pub.replace("Z","+00:00")) < cutoff:
                            continue
                    except: pass
                desc = strip_html(e.get("summary") or e.get("description") or "")
                summary = summarize_rule_based(title, desc, 900) or desc[:900]
                out.append({
                    "title": title,
                    "url": norm,
                    "published_at": pub,
                    "summary": summary,
                    "source": src,
                    "category": topic
                })
                seen.add(norm)
                if len(out) >= limit: break
        except Exception:
            continue
        if len(out) >= limit: break
    out.sort(key=lambda x: x.get("published_at") or "", reverse=True)
    return out

@app.get("/api/curated", response_model=NewsResponse)
def api_curated(topic: str = Query(..., pattern="^(finance|startup|ai)$"),
                days: int = Query(3, ge=1, le=14),
                limit: int = Query(60, ge=1, le=200)):
    return {"items": _rss_curated(topic, days, limit)}

# ---------- topic RSS feed ----------
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

# ---------- Shloka of the Day (authentic source with cache) ----------
_SHLOKA_CACHE: Dict[str, Any] = {}
@app.get("/api/shloka/daily")
def shloka_daily():
    key = datetime.utcnow().strftime("%Y-%m-%d")
    if key in _SHLOKA_CACHE:
        return _SHLOKA_CACHE[key]
    try:
        ch = random.randint(1, 18)
        v = random.randint(1, 72)
        url = f"https://bhagavadgitaapi.in/slok/{ch}/{v}/"

        try:
            import httpx  # lazy import
            with httpx.Client(timeout=8.0) as client:
                r = client.get(url)
                ok = r.status_code == 200
                data = r.json() if ok else {}
        except Exception:
            # urllib fallback
            import json, urllib.request
            req = urllib.request.Request(url, headers={"User-Agent":"NewsLens/1.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))

        obj = {
            "ref": f"{data.get('chapter')}.{data.get('verse')}",
            "dev": data.get("slok") or "",
            "tr": data.get("te") or data.get("et") or data.get("siva") or data.get("translation") or ""
        }
        if obj["dev"]:
            _SHLOKA_CACHE[key] = obj
            return obj
    except Exception:
        pass
    fallback = {"ref": "2.47", "dev": "कर्मण्येवाधिकारस्ते मा फलेषु कदाचन ।", "tr": "You have a right to action alone, not to its fruits."}
    _SHLOKA_CACHE[key] = fallback
    return fallback

# ---------- Chat (Gemini) ----------
@app.post("/api/chat")
def chat_api(body: ChatIn = Body(...)):
    if not GEMINI_API_KEY:
        return JSONResponse({"text": "Gemini API key missing on server."}, status_code=500)
    try:
        payload = {"contents":[{"parts":[{"text": body.message[:5000]}]}]}
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

        try:
            import httpx  # lazy import
            with httpx.Client(timeout=15.0) as client:
                r = client.post(url, json=payload)
                if r.status_code != 200:
                    return JSONResponse({"text": f"Gemini error: {r.text[:200]}"} , status_code=500)
                data = r.json()
        except Exception:
            # urllib fallback
            import json, urllib.request
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                         headers={"Content-Type":"application/json"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))

        out = (data.get("candidates",[{}])[0]
                  .get("content",{})
                  .get("parts",[{}])[0]
                  .get("text",""))
        return {"text": out or "No response."}
    except Exception as e:
        return JSONResponse({"text": f"Gemini request failed: {e.__class__.__name__}"}, status_code=500)

# ---------- entry ----------
if __name__ == "__main__":
    uvicorn.run(
        "backend.app:app",
        host="0.0.0.0",
        port=safe_int(os.getenv("PORT", 8000)),
        reload=(ENV == "dev"),
    )
