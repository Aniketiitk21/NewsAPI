# backend/aggregator/fetch.py
import datetime as dt
from typing import List, Optional, Dict
import pytz, feedparser, re, time
from newspaper import Article, Config
from .sources import NATIONAL_FEEDS, STATE_FEEDS
from .config import CATEGORY_KEYWORDS
from .classify import stance_for_state_politics
from .utils import within_days_ist, text_contains_any, summary_from_text, strip_html
from .summarize import summarize_rule_based

IST = pytz.timezone("Asia/Kolkata")

_CACHE: Dict[str, Dict] = {}
_CACHE_TTL_SECONDS = 15 * 60  # 15 minutes

def _cache_key(scope: str, state: Optional[str], category: Optional[str], days: int, limit: int, fetch_mode: str) -> str:
    return f"{scope}|{state or ''}|{category or ''}|{days}|{limit}|{fetch_mode}"

def _get_cached(key: str) -> Optional[List[Dict]]:
    it = _CACHE.get(key)
    if not it:
        return None
    if (dt.datetime.utcnow() - it["ts"]).total_seconds() > _CACHE_TTL_SECONDS:
        _CACHE.pop(key, None)
        return None
    return it["value"]

def _set_cached(key: str, value: List[Dict]):
    _CACHE[key] = {"ts": dt.datetime.utcnow(), "value": value[:]}  # store copy

def _parse_pub_date(entry) -> Optional[dt.datetime]:
    tstruct = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if not tstruct:
        return None
    try:
        return dt.datetime(*tstruct[:6], tzinfo=pytz.UTC).astimezone(IST)
    except Exception:
        return None

def _download_article(url: str, retries: int = 1) -> Dict:
    cfg = Config()
    cfg.browser_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) NewsLens/1.1"
    cfg.request_timeout = 12
    cfg.memoize_articles = False
    cfg.fetch_images = False
    last_err = None
    for i in range(retries + 1):
        try:
            art = Article(url, config=cfg)
            art.download()
            art.parse()
            text = (art.text or "").strip()
            title = (art.title or "").strip()
            pub = None
            try:
                if art.publish_date:
                    pub = art.publish_date.astimezone(IST).isoformat()
            except Exception:
                pub = None
            return {"title": title, "text": text, "published_at": pub}
        except Exception as e:
            last_err = e
            time.sleep(0.5)
    # best-effort fallback
    return {"title": "", "text": "", "published_at": None}

def _match_category(title: str, desc: str, fulltext: str, cat: Optional[str]) -> bool:
    if not cat:
        return True
    keys = CATEGORY_KEYWORDS.get(cat, [])
    blob = " ".join([title or "", desc or "", fulltext or ""])
    return text_contains_any(blob, keys)

def _collect_feeds(scope: str, state: Optional[str]) -> List[str]:
    if scope == "national":
        return NATIONAL_FEEDS
    if scope == "state":
        return STATE_FEEDS.get(state or "", []) or []
    return []

def get_news(
    scope: str,
    state: Optional[str],
    category: Optional[str],
    days: int,
    limit: int,
    fetch_mode: str = "light",
    max_per_feed: int = 80
) -> List[Dict]:
    key = _cache_key(scope, state, category, days, limit, fetch_mode)
    cached = _get_cached(key)
    if cached is not None:
        return cached

    feeds = _collect_feeds(scope, state)
    results: List[Dict] = []
    seen = set()

    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            entries = getattr(feed, "entries", [])[:max_per_feed]
            for entry in entries:
                pub_dt = _parse_pub_date(entry)
                if not within_days_ist(pub_dt, days):
                    continue

                link = (entry.get("link") or "").strip()
                if not link:
                    continue
                norm = link.split("?", 1)[0].rstrip("/")
                if norm in seen:
                    continue

                title = (entry.get("title") or "").strip()
                desc = strip_html(entry.get("description") or "")
                source_title = ""
                try:
                    source_title = feed.feed.get("title", "")
                except Exception:
                    pass

                # LIGHT vs DEEP
                art_title, art_text, art_pub = title, "", None
                if fetch_mode == "deep":
                    a = _download_article(norm, retries=1)
                    art_title = a["title"] or art_title
                    art_text = a["text"] or ""
                    art_pub = a["published_at"]
                else:
                    art_text = desc

                if not _match_category(art_title, desc, art_text, category):
                    continue

                # Summarize (rule-based first, fallback to lead-3)
                summary = summarize_rule_based(art_title, art_text, max_chars=900)
                if not summary:
                    summary = summary_from_text(art_text or desc, art_title, 900)

                item = {
                    "title": art_title or title or "(untitled)",
                    "url": norm,
                    "published_at": art_pub or (pub_dt.isoformat() if pub_dt else None),
                    "summary": summary,
                    "source": source_title,
                    "state": state if scope == "state" else None,
                    "category": category or "all",
                }

                if (category == "politics") and (scope == "state") and state:
                    stance = stance_for_state_politics((art_title or "") + "\n" + (art_text or ""), state)
                    item["stance"] = stance["label"]
                    item["confidence"] = stance["confidence"]

                results.append(item)
                seen.add(norm)
                if len(results) >= limit:
                    break
        except Exception:
            # Skip broken feeds cleanly
            continue
        if len(results) >= limit:
            break

    results.sort(key=lambda x: x.get("published_at") or "", reverse=True)
    _set_cached(key, results)
    return results
