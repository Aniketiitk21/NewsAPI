# backend/aggregator/utils.py
import datetime as dt
import pytz, re
from typing import Optional, List

IST = pytz.timezone("Asia/Kolkata")

def now_ist() -> dt.datetime:
    return dt.datetime.now(IST)

def within_days_ist(pub_dt: Optional[dt.datetime], days: int) -> bool:
    if not pub_dt:
        return False
    floor = (now_ist() - dt.timedelta(days=days-1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return pub_dt >= floor

def text_contains_any(text: str, keys: List[str]) -> bool:
    if not text or not keys: return False
    t = text.lower()
    return any(k in t for k in keys)

def safe_int(v, default=0):
    try:
        return int(v)
    except Exception:
        return default

def strip_html(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()

def summary_from_text(text: str, title: str = "", max_chars: int = 900) -> str:
    """
    Fallback: simple lead-3 (kept for reliability).
    Called by fetch if rule-based returns empty.
    """
    if not text:
        return ""
    parts = re.split(r'(?<=[.!?])\s+', strip_html(text))
    s = " ".join(parts[:3])[:max_chars]
    return s
