# -*- coding: utf-8 -*-
"""
AP Political News → (Today+Yesterday by default, IST) → Summary + TDP stance → HTML (Dark)
- Strict Andhra Pradesh filtering (title/desc/link path + AP district/city list)
- Robust date parsing for RSS (IST window)
- Dedup + domain/path whitelisting for AP sections
- Newspaper3k extraction with sane timeouts
- NEW: Government-aligned TDP stance (Gov≡TDP): govt/CM positivity → TDP positive; govt/CM negativity → TDP negative; else neutral
- Context + proximity + policy verbs + rival-target context (optional Zero-Shot tie-break)
- Party tags (other parties mentioned)
- Cross-platform (prints file:// URL)
"""

import os, re, html as htmlmod, argparse, datetime as dt, sys
from typing import Dict, List, Optional, Tuple, Set
import pytz
import feedparser

# --- Optional heavy deps guarded ---
USE_TRANSFORMERS_DEFAULT = False
try:
    from newspaper import Article, Config
except Exception:
    print("ERROR: newspaper3k not installed. pip install newspaper3k", file=sys.stderr)
    raise

# ---- (Optional) Zero-shot model bits (loaded only if flag is on) ----
def _lazy_load_zshot(model_id="joeddav/xlm-roberta-large-xnli"):
    from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
    tok = AutoTokenizer.from_pretrained(model_id, use_fast=False)
    mdl = AutoModelForSequenceClassification.from_pretrained(model_id)
    return pipeline(task="zero-shot-classification", model=mdl, tokenizer=tok)

OUT_HTML = "ap_politics_today.html"
IST = pytz.timezone("Asia/Kolkata")

# ---- Sources: AP-specific sections preferred ----
NEWS_FEEDS = [
    # Core AP feeds
    "https://www.thehindu.com/news/national/andhra-pradesh/feeder/default.rss",
    "https://www.newindianexpress.com/States/Andhra-Pradesh/rssfeed/?id=170&getXmlFeed=true",
    "https://www.deccanchronicle.com/rss/andhra-pradesh.xml",
    "https://timesofindia.indiatimes.com/rssfeeds/-2128540748.cms",
    "https://english.sakshi.com/rss.xml",

    # Extra AP-relevant feeds (script skips quietly if any break)
    "https://www.thehansindia.com/rss/andhra-pradesh",        # The Hans India - AP
    "https://www.thenewsminute.com/andhra-pradesh/rss",       # The News Minute - AP
    "https://feeds.feedburner.com/andhrajyothy/english",      # Andhra Jyothy - English (if available)
]

# ---- AP districts/cities & political keywords ----
AP_LOCS = [
    "andhra pradesh", "amaravati", "visakhapatnam", "vizag", "vishakhapatnam",
    "vijayawada", "guntur", "tirupati", "nellore", "kurnool", "kadapa",
    "ananthapur", "anantapur", "ongole", "rajahmundry", "rajamahendravaram",
    "tenali", "eluru", "srikakulam", "vizianagaram", "east godavari",
    "west godavari", "ntr district", "konaseema", "palnadu", "bapatla",
    "parvathipuram", "manyam", "alluri sitarama raju", "ananthapuramu",
    "ysr kadapa", "chittoor", "prakasam",
]
POLITICS = [
    "tdp", "telugu desam", "chandrababu", "naidu", "cbn",
    "ysrcp", "ys jagan", "jagan mohan reddy", "pawan kalyan", "jsp", "jana sena",
    "bjp", "congress", "inc",
    "mla", "mp", "mla seat", "assembly", "cabinet", "minister",
    "opposition", "ruling", "yatra", "alliance", "coalition", "election", "poll",
    "manifesto", "model code", "constituency", "governor", "cm", "chief minister",
    "government", "govt", "administration", "secretariat"  # ensure we keep govt context in filter
]

# Party aliases for detection
PARTY_ALIASES = {
    "TDP": [r"\btdp\b", r"telugu desam", r"chandrababu", r"\bnaidu\b", r"\bcbn\b"],
    "YSRCP": [r"\bysrcp\b", r"\bys jagan\b", r"jagan mohan reddy"],
    "JSP": [r"\bjsp\b", r"\bjana\s*sena\b", r"pawan kalyan"],
    "BJP": [r"\bbjp\b"],
    "INC": [r"\binc\b", r"\bcongress\b"],
}

# Path hints that strongly suggest AP section
AP_PATH_HINTS = [
    "/andhra-pradesh", "/news/national/andhra-pradesh", "/state/andhra-pradesh",
    "/andhra/", "/ap/", "/amaravati", "/visakhapatnam", "/vijayawada",
]

# ---- Simple utils ----
def _now_ist() -> dt.datetime:
    return dt.datetime.now(IST)

def parse_pub_date(entry) -> Optional[dt.datetime]:
    tstruct = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if not tstruct:
        return None
    try:
        dt_utc = dt.datetime(*tstruct[:6], tzinfo=pytz.UTC)
        return dt_utc.astimezone(IST)
    except Exception:
        return None

def within_days_ist(pub_dt: Optional[dt.datetime], days: int) -> bool:
    if not pub_dt:
        return False
    now = _now_ist()
    floor = (now - dt.timedelta(days=days-1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return pub_dt >= floor

def normalize_url(u: str) -> str:
    if "?" in u:
        base, _q = u.split("?", 1)
        return base
    return u

def looks_ap_path(url: str) -> bool:
    u = url.lower()
    return any(h in u for h in AP_PATH_HINTS)

def text_contains_any(text: str, keys: List[str]) -> bool:
    t = text.lower()
    return any(k in t for k in keys)

def is_ap_politics(title: str, desc: str, url: str) -> bool:
    blob = f"{title} {desc}".lower()
    has_ap = text_contains_any(blob, AP_LOCS) or looks_ap_path(url)
    has_pol = text_contains_any(blob, POLITICS)
    return has_ap and has_pol

# ---- Party extraction ----
def extract_parties(text: str) -> List[str]:
    found: Set[str] = set()
    tl = text.lower()
    for party, pats in PARTY_ALIASES.items():
        for pat in pats:
            if re.search(pat, tl):
                found.add(party)
                break
    return sorted(found)

# ---- TDP stance (Gov≡TDP) ----
# General polarity words
POS_WORDS = [
    "support", "supports", "backs", "praised", "lauded", "ally", "clean chit",
    "acquitted", "cleared", "vindicated", "won", "victory", "favour", "favorable",
    "favourable", "appreciated", "commended", "applauded", "benefit", "relief",
    "development", "boost"
]
NEG_WORDS = [
    "slam", "slams", "critic", "criticise", "criticized", "attack", "attacks",
    "probe", "arrest", "arrested", "scam", "corruption", "blame", "charges",
    "fir", "raid", "anti-tdp", "accused", "allegation", "allegations",
    "controversy", "irregularities", "violations", "protest", "strike", "boycott",
    "backlash", "setback", "flak", "censure", "rebuke"
]

# Policy/action verbs & outcomes (for govt/CM context)
POS_POLICY = [
    "launched", "inaugurated", "approved", "cleared", "sanctioned", "released",
    "implemented", "rolled out", "kickstarted", "commissioned", "opened",
    "granted", "allotted", "allocated", "reduced rates", "cut taxes"
]
NEG_POLICY = [
    "stalled", "scrapped", "halted", "suspended", "delayed", "denied",
    "withheld", "stayed", "quashed", "cancelled", "rollback", "rollback of"
]

# Target clusters
TDP_TERMS = [r"\btdp\b", "telugu desam", "chandrababu", r"\bnaidu\b", r"\bcbn\b"]
# Govt terms (Gov≡TDP). Include CM, Cabinet, administration and explicit AP govt mentions.
GOV_TERMS = [
    r"\bap government\b", r"\bandhra pradesh government\b", r"\bstate government\b",
    r"\bgovt\b", r"\bgovernment\b", r"\badministration\b", r"\bcabinet\b",
    r"\bchief minister\b", r"\bcm\b", "chandrababu", r"\bnaidu\b", r"\bcbn\b",
    r"\bsecretariat\b", r"\bstate cabinet\b"
]
# Rivals (as "opponent" signal)
RIVAL_PATTERNS = PARTY_ALIASES["YSRCP"] + PARTY_ALIASES["BJP"] + PARTY_ALIASES["INC"] + PARTY_ALIASES["JSP"]

def _window_hits(text: str, center_terms: List[str], cue_words: List[str], win: int = 60) -> int:
    """
    Count cue words appearing within +/- win characters of any center term (approx. proximity).
    """
    t = text.lower()
    idxs = []
    for c in center_terms:
        for m in re.finditer(c, t):
            idxs.append(m.start())
    hits = 0
    for pos in idxs:
        left = max(0, pos - win)
        right = min(len(t), pos + win)
        window = t[left:right]
        for w in cue_words:
            if w in window:
                hits += 1
    return hits

def _polarity_counts(text: str, lex: List[str]) -> int:
    tl = text.lower()
    return sum(tl.count(w) for w in lex)

def stance_tdp_gov_aligned(text: str) -> Dict:
    """
    Government-aligned stance:
      - Treat Andhra Government/CM as TDP (Gov≡TDP).
      - If news is positive near TDP or Govt/CM → Positive.
      - If news is negative near TDP or Govt/CM → Negative.
      - Rival negativity supports Positive (secondary).
      - Rival positivity supports Negative (secondary).
      - If no clear pull → Neutral.
    """
    tl = text.lower()

    has_tdp = any(re.search(p, tl) for p in TDP_TERMS)
    has_gov = any(re.search(p, tl) for p in GOV_TERMS)

    # Proximity signals
    pos_near_tdp = _window_hits(tl, TDP_TERMS, POS_WORDS, win=70)
    neg_near_tdp = _window_hits(tl, TDP_TERMS, NEG_WORDS, win=70)

    # Policy/action signals near Govt/CM
    pos_near_gov = _window_hits(tl, GOV_TERMS, POS_WORDS + POS_POLICY, win=70)
    neg_near_gov = _window_hits(tl, GOV_TERMS, NEG_WORDS + NEG_POLICY, win=70)

    # Rival context (secondary)
    neg_near_rival = _window_hits(tl, RIVAL_PATTERNS, NEG_WORDS + NEG_POLICY, win=70)
    pos_near_rival = _window_hits(tl, RIVAL_PATTERNS, POS_WORDS + POS_POLICY, win=70)

    # Global polarity (light tiebreak)
    global_pos = _polarity_counts(tl, POS_WORDS + POS_POLICY)
    global_neg = _polarity_counts(tl, NEG_WORDS + NEG_POLICY)

    # If neither TDP nor Govt/CM appears, infer from rivals only (weak inference)
    if not has_tdp and not has_gov:
        if neg_near_rival - pos_near_rival >= 2:
            return {"label": "positive", "confidence": 0.6}  # rivals in trouble → good for TDP
        if pos_near_rival - neg_near_rival >= 2:
            return {"label": "negative", "confidence": 0.6}  # rivals doing well → bad for TDP
        # fallback to global
        if global_pos - global_neg >= 5:
            return {"label": "positive", "confidence": 0.55}
        if global_neg - global_pos >= 5:
            return {"label": "negative", "confidence": 0.55}
        return {"label": "neutral", "confidence": 0.4}

    # Core Gov≡TDP scoring
    # Strong local pull near TDP/Gov terms dominates
    primary = 2.0 * ((pos_near_tdp + pos_near_gov) - (neg_near_tdp + neg_near_gov))
    secondary = 1.0 * (neg_near_rival - pos_near_rival)
    tertiary = 0.25 * (global_pos - global_neg)

    score = primary + secondary + tertiary

    # Thresholds tuned for clarity (Gov≡TDP)
    if score >= 1.0:
        conf = min(0.9, 0.6 + 0.08 * (score))
        return {"label": "positive", "confidence": float(f"{conf:.2f}")}
    if score <= -1.0:
        conf = min(0.9, 0.6 + 0.08 * (-score))
        return {"label": "negative", "confidence": float(f"{conf:.2f}")}

    # Within band → look for explicit govt/CM positives/negatives to break tie
    if (pos_near_gov + pos_near_tdp) - (neg_near_gov + neg_near_tdp) >= 1:
        return {"label": "positive", "confidence": 0.55}
    if (neg_near_gov + neg_near_tdp) - (pos_near_gov + pos_near_tdp) >= 1:
        return {"label": "negative", "confidence": 0.55}

    # Final fallback
    if global_pos - global_neg >= 6:
        return {"label": "positive", "confidence": 0.52}
    if global_neg - global_pos >= 6:
        return {"label": "negative", "confidence": 0.52}
    return {"label": "neutral", "confidence": 0.5}

def stance_tdp_zshot(text: str, zshot) -> Dict:
    hypos = [
        "This article is supportive of the Telugu Desam Party (TDP).",
        "This article is critical of the Telugu Desam Party (TDP).",
        "This article is neutral about the Telugu Desam Party (TDP).",
    ]
    res = zshot(text[:1400], hypos)
    last = res["labels"][0].split()[-1].lower()
    label = {"supportive": "positive", "critical": "negative", "neutral": "neutral"}[last]
    return {"label": label, "confidence": float(f"{res['scores'][0]:.3f}")}

# ---- Fetch recent URLs ----
def fetch_recent_ap_news(feeds: List[str], days: int) -> List[Tuple[str, str, dt.datetime]]:
    seen = set()
    urls: List[Tuple[str, str, dt.datetime]] = []
    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in getattr(feed, "entries", []):
                pub_dt = parse_pub_date(entry)
                if not within_days_ist(pub_dt, days):
                    continue
                title = entry.get("title", "")
                desc = entry.get("description", "")
                link = entry.get("link", "")
                if not link:
                    continue
                if not is_ap_politics(title, desc, link):
                    continue
                norm = normalize_url(link)
                if norm in seen:
                    continue
                seen.add(norm)
                urls.append((norm, title, pub_dt))
        except Exception as e:
            print(f"[WARN] Error parsing feed {feed_url}: {e}", file=sys.stderr)
            continue
    return urls

# ---- Download & analyze one article ----
def fetch_and_analyze(url: str, use_zshot: bool, zshot=None) -> Optional[Dict]:
    cfg = Config()
    cfg.browser_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AP-NewsBot/3.0"
    cfg.request_timeout = 20
    cfg.memoize_articles = False
    cfg.keep_article_html = False
    cfg.fetch_images = False

    art = Article(url, config=cfg)
    art.download()
    art.parse()

    title = (art.title or "").strip()
    text = (art.text or "").strip()
    if len(text) < 300:
        return None

    # Cross-check AP-politics again on full text
    if not (text_contains_any(title + " " + text, AP_LOCS) and text_contains_any(text, POLITICS)):
        return None

    # Summary = first ~3-4 sentences limited length
    paras = re.split(r"(?<=[.?!])\s+", text)
    summary = " ".join(paras[:4])[:1100]

    # Parties present
    parties = extract_parties(title + "\n" + text)

    # Stance (Gov≡TDP; optional ZS tie-break)
    stance = stance_tdp_gov_aligned(title + "\n" + text)
    if use_zshot:
        try:
            if zshot is None:
                zshot = _lazy_load_zshot()
            stance_z = stance_tdp_zshot(title + "\n" + text, zshot)
            # Tie-break: if our gov-aligned stance is neutral but ZS is non-neutral, adopt ZS
            if stance["label"] == "neutral" and stance_z["label"] != "neutral":
                stance = stance_z
        except Exception as e:
            print(f"[WARN] Zero-shot failed ({e}); keeping gov-aligned stance.", file=sys.stderr)

    pub_iso = None
    try:
        if art.publish_date:
            pub_iso = art.publish_date.astimezone(IST).isoformat()
    except Exception:
        pub_iso = None

    return {
        "url": url,
        "title": title or "(untitled)",
        "published_at": pub_iso,  # may be None
        "summary": summary,
        "stance": stance["label"],
        "confidence": float(stance["confidence"]),
        "parties": parties,
    }

# ---- HTML rendering (Dark Theme) ----
def render_html(items: List[Dict], days: int) -> str:
    def party_badges(p: List[str]) -> str:
        if not p: return ""
        chips = "".join(f"<span class='chip'>{htmlmod.escape(x)}</span>" for x in p)
        return f"<div class='tags'>{chips}</div>"

    cards = []
    for it in items:
        date_html = it.get("published_at") or "—"
        cards.append(f"""
        <article class="card">
            <h3><a href="{htmlmod.escape(it['url'])}" target="_blank" rel="noopener">{htmlmod.escape(it['title'])}</a></h3>
            <div class="date">{date_html}</div>
            {party_badges(it.get('parties', []))}
            <p>{htmlmod.escape(it['summary'])}</p>
            <div class="stance {it['stance']}">TDP Stance: {it['stance'].title()} ({it['confidence']:.2f})</div>
        </article>
        """)

    html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<title>AP Political News Analysis</title>
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
:root {{
  --bg: #0b1020;        /* deep navy */
  --panel: #121833;     /* card bg */
  --muted: #9aa3b2;
  --fg: #e7eaf3;
  --link: #7aa2ff;
  --border: #1a2349;
  --chip: #1e2752;
  --pos-bg: #163d2b;    --pos-fg: #9ef0b8;
  --neg-bg: #3b1b1b;    --neg-fg: #ffb3b3;
  --neu-bg: #1f2746;    --neu-fg: #c6ccdb;
}}
* {{ box-sizing: border-box; }}
body {{ font-family: system-ui,-apple-system,Segoe UI,Roboto,sans-serif; background: var(--bg); color: var(--fg);
        max-width: 1080px; margin: 2rem auto; padding: 0 1rem; }}
h1 {{ margin: 0 0 0.25rem 0; font-weight: 700; }}
.sub {{ color: var(--muted); margin-bottom: 1rem; }}
.grid {{ display:grid; grid-template-columns: repeat(auto-fill, minmax(320px,1fr)); gap: 16px; }}
.card {{ background: var(--panel); border: 1px solid var(--border); padding: 1rem; border-radius: 14px;
         box-shadow: 0 8px 20px rgba(0,0,0,0.25); }}
.card h3 {{ margin: 0 0 .25rem 0; font-size: 1.08rem; line-height: 1.35; }}
.card a {{ color: var(--link); text-decoration: none; }}
.card a:hover {{ text-decoration: underline; }}
.date {{ color: var(--muted); font-size: .85rem; margin: .25rem 0 .65rem 0; }}
.tags {{ margin: 0 0 .6rem 0; }}
.chip {{ display:inline-block; padding:.24rem .5rem; margin: 0 .35rem .35rem 0; border-radius: 999px;
         background: var(--chip); color: #cfe0ff; font-size:.78rem; border:1px solid var(--border); }}
.stance {{ margin-top: .75rem; padding: .55rem .7rem; border-radius: 10px; font-weight: 700; display:inline-block; }}
.positive {{ background: var(--pos-bg); color: var(--pos-fg); }}
.negative {{ background: var(--neg-bg); color: var(--neg-fg); }}
.neutral  {{ background: var(--neu-bg); color: var(--neu-fg); }}
.empty {{ color: var(--muted); padding:1rem; border:1px dashed var(--border); border-radius: 12px; background: var(--panel); }}
.footer {{ color: var(--muted); font-size:.85rem; margin-top:1rem; }}
</style>
</head>
<body>
  <h1>Andhra Pradesh Political News</h1>
  <div class="sub">Window: last {days} day(s), IST • Generated: {_now_ist().strftime('%Y-%m-%d %H:%M IST')}</div>
  {"<div class='grid'>" + "".join(cards) + "</div>" if items else "<div class='empty'>No AP politics articles found in the selected window.</div>"}
  <div class="footer">Filters: AP locations + AP section paths + politics keywords • Stance uses Gov≡TDP rule with proximity and rival context.</div>
</body>
</html>
"""
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_content)
    return os.path.abspath(OUT_HTML)

# ---- main ----
def main():
    ap = argparse.ArgumentParser(description="AP Political News (Andhra-only) → HTML (Dark)")
    ap.add_argument("--days", type=int, default=2, help="Lookback window in days (IST). Default=2 (today+yesterday)")
    ap.add_argument("--use-zero-shot", type=int, default=1 if USE_TRANSFORMERS_DEFAULT else 0,
                    help="1 to use transformers zero-shot for TDP stance (slow/heavy), 0 for gov-aligned heuristic. Default=0")
    args = ap.parse_args()
    days = max(1, args.days)
    use_zshot = bool(args.use_zero_shot)

    print(f"[i] Fetching recent AP politics (last {days} day(s), IST) ...")
    candidates = fetch_recent_ap_news(NEWS_FEEDS, days)
    print(f"[i] RSS candidates (after AP+politics filter): {len(candidates)}")

    zshot = None
    if use_zshot:
        try:
            print("[i] Loading zero-shot model (first run may take long) ...")
            zshot = _lazy_load_zshot()
        except Exception as e:
            print(f"[WARN] Could not load transformers model: {e}. Falling back to gov-aligned stance.", file=sys.stderr)
            use_zshot = False

    results: List[Dict] = []
    for url, title, pdt in candidates:
        print(f" • Analyzing: {url}")
        try:
            item = fetch_and_analyze(url, use_zshot, zshot)
            if item:
                if not item.get("published_at") and isinstance(pdt, dt.datetime):
                    item["published_at"] = pdt.isoformat()
                results.append(item)
                print(f"   ✓ {item['title'][:100]}")
            else:
                print("   ✗ Skipped (not AP-politics on full text / too short)")
        except Exception as e:
            print(f"   ✗ Error: {e}", file=sys.stderr)

    out_path = render_html(results, days)
    uri = "file://" + out_path.replace("\\", "/")
    print(f"\n[i] Generated report with {len(results)} article(s):\n    {uri}")

if __name__ == "__main__":
    main()
