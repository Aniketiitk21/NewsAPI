import re
from collections import Counter
from typing import List, Tuple

CUE_POS = {"announced","launched","approved","said","stated","will","today","plans","rolled","released","inaugurated","issued"}
CUE_NEU = {"according","report","reports","sources","officials","added","stated"}
STOPLIKE = set("a an the and or if to from by on in with of for as at is are was were it this that those these be been being can may might would could will shall".split())

def _sentences(text: str) -> List[str]:
    t = re.sub(r"<[^>]+>", " ", text or "")
    t = re.sub(r"\s+", " ", t).strip()
    if not t:
        return []
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", t)
    seen, out = set(), []
    for s in parts:
        k = re.sub(r"[^a-z0-9]+","", s.lower())[:120]
        if k and k not in seen:
            out.append(s.strip())
            seen.add(k)
    return out

def _keywords(blob: str, top_k=20) -> Counter:
    toks = [w for w in re.findall(r"[a-zA-Z0-9']+", blob.lower()) if w not in STOPLIKE and len(w) > 2]
    return Counter(toks).most_common(top_k)

def _score_sentence(s: str, kw: Counter, title_kw: Counter, idx: int) -> float:
    toks = [w.lower() for w in re.findall(r"[a-zA-Z0-9']+", s)]
    if not toks: return 0.0
    bag = Counter(toks)
    kscore = sum((kw.get(k,0) for k in bag)) / (len(toks) + 1)     # body keyword density
    tover = sum((title_kw.get(k,0) for k in bag)) / (len(toks) + 1) # title overlap
    cues = len(set(toks) & CUE_POS) * 0.4 + len(set(toks) & CUE_NEU) * 0.2
    pos = 1.2 if idx == 0 else (1.05 if idx == 1 else 1.0)
    L = len(toks); length = 1.0 if 10 <= L <= 40 else (0.7 if L < 10 else 0.8)
    return (kscore*1.6 + tover*0.8 + cues) * pos * length

def summarize_rule_based(title: str, text: str, max_chars: int = 900) -> str:
    sents = _sentences(text)
    if not sents:
        return ""
    if len(sents) <= 3:
        return " ".join(sents)[:max_chars]

    kw = Counter(dict(_keywords(" ".join(sents))))
    title_kw = Counter(dict(_keywords(title or "")))

    scored: List[Tuple[float,int,str]] = [(_score_sentence(s, kw, title_kw, i), i, s) for i, s in enumerate(sents)]
    top = sorted(sorted(scored, key=lambda x: x[0], reverse=True)[:6], key=lambda x: x[1])

    out, total = [], 0
    for _, _, s in top:
        if total + len(s) + 1 > max_chars: break
        out.append(s); total += len(s) + 1

    if len(" ".join(out)) < 140:  # strong fallback: lead-3
        out = sents[:3]
    return " ".join(out)[:max_chars]
