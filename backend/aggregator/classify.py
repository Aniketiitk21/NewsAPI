import re
from typing import Dict, List, Optional
from .config import POS_WORDS, NEG_WORDS, RULING_PARTY_BY_STATE

# Generic governance anchors – neutral and widely-used tokens
GOV_TERMS_GENERIC = [
    r"\bgovernment\b", r"\bgovt\b", r"\bstate government\b", r"\badministration\b",
    r"\bchief minister\b", r"\bcm\b", r"\bcabinet\b", r"\bsecretariat\b",
    r"\bministry\b", r"\bdepartment\b"
]

def _window_hits(text: str, center_terms: List[str], cue_words: List[str], win: int = 70) -> int:
    """Count cue words within ±win chars of any governance term."""
    t = text.lower()
    idxs: List[int] = []
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

def stance_for_state_politics(text: str, state: Optional[str]) -> Dict:
    """
    Lightweight, explainable stance around governance mentions.
    Not party-specific; returns a soft 'governance tone' near generic gov anchors.
    """
    ruling = RULING_PARTY_BY_STATE.get(state or "", None)
    if not ruling:
        return {"label": "neutral", "confidence": 0.45}

    tl = text.lower()
    gov_pos = _window_hits(tl, GOV_TERMS_GENERIC, POS_WORDS)
    gov_neg = _window_hits(tl, GOV_TERMS_GENERIC, NEG_WORDS)

    score = 2 * (gov_pos - gov_neg)
    if score >= 2:
        return {"label": "positive", "confidence": 0.7}
    if score <= -2:
        return {"label": "negative", "confidence": 0.7}
    if (gov_pos - gov_neg) == 1:
        return {"label": "positive", "confidence": 0.55}
    if (gov_neg - gov_pos) == 1:
        return {"label": "negative", "confidence": 0.55}
    return {"label": "neutral", "confidence": 0.5}
