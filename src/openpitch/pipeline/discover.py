"""Auto-discovery — promote AI startups from funding news into the universe.

ponytail: broad Google News RSS + one LLM extraction call, appended to
config/discovered.yaml (the curated watchlist.yaml is never rewritten).
The scoring layer then ranks them with everyone else.
"""

from __future__ import annotations

import re
import urllib.parse

import yaml

from ..paths import config_dir
from .llm import LLMProvider

# AI-enabled across verticals — AI-native plus AI-applied (AI fintech, AI health,
# defense AI like Anduril). NOT generic non-AI startups.
# Mix of (a) fresh-funding queries that catch companies the day they raise, and
# (b) ranking/listicle queries that backfill ESTABLISHED unicorns whose raise is
# months old and so absent from today's news (e.g. Higgsfield's Jan-2026 round).
_QUERIES = [
    'AI startup ("Series" OR raises OR "funding round") valuation',
    '"AI" (fintech OR healthcare OR legal OR security) startup funding',
    '(defense OR autonomous OR "dual-use") AI startup funding',
    '("AI agents" OR "AI infrastructure" OR "applied AI" OR "enterprise AI") funding round',
    '("most valuable" OR "top" OR unicorn) AI startups valuation 2026',
    '("generative" OR "AI video" OR "AI image" OR "AI voice") startup valuation',
]


def _feed(q: str) -> str:
    return "https://news.google.com/rss/search?" + urllib.parse.urlencode(
        {"q": q, "hl": "en-US", "gl": "US", "ceid": "US:en"})


def _sys() -> str:
    from .classify import VOCAB
    vocab = "; ".join(f"{m}: {', '.join(subs)}" for m, subs in VOCAB.items())
    return (
        "Extract private companies that are AI-native or meaningfully AI-ENABLED (AI is core "
        "to the product/value), across any vertical — including AI fintech, AI healthcare, and "
        "defense/autonomous AI. Skip companies with no real AI angle, public companies, and "
        "investors/VC firms. For each give name; domain if obvious; a `category` from this fixed "
        f"list and a matching `subcategory` from its options ({vocab}); a short free-text "
        "`specialty` (<=8 words); and a `summary` of 1-2 plain-English sentences on what the company does."
    )


_SCHEMA = {
    "type": "object",
    "properties": {"companies": {"type": "array", "items": {
        "type": "object", "required": ["name"], "properties": {
            "name": {"type": "string"}, "category": {"type": "string"},
            "subcategory": {"type": "string"}, "specialty": {"type": "string"},
            "summary": {"type": "string"}, "domain": {"type": "string"},
        }}}},
    "required": ["companies"],
}


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def discover(*, llm: LLMProvider, per_query: int = 15) -> list[dict]:
    """One LLM call over recent multi-sector funding headlines → candidate companies."""
    import feedparser

    seen, headlines = set(), []
    for q in _QUERIES:
        for e in feedparser.parse(_feed(q)).entries[:per_query]:
            t = f"{e.get('title', '')}. {e.get('summary', '')}".strip()
            if t and t not in seen:
                seen.add(t)
                headlines.append(t)
    text = "\n".join(headlines)
    if not text.strip():
        return []
    from .classify import VOCAB
    data = llm.complete_json(_sys(), text, _SCHEMA) or {}
    out = []
    for c in data.get("companies", []):
        name = (c.get("name") or "").strip()
        if not name:
            continue
        cat = c.get("category") if c.get("category") in VOCAB else "vertical-app"
        sub = c.get("subcategory") if c.get("subcategory") in VOCAB.get(cat, []) else None
        out.append({"id": _slug(name), "name": name, "category": cat,
                    "subcategory": sub, "specialty": (c.get("specialty") or None),
                    "summary": (c.get("summary") or None),
                    "domain": c.get("domain") or None, "segment": "global"})
    return out


def _curated_ids() -> set[str]:
    """Ids already in the hand-curated watchlist.yaml (companies + mena), [] if absent.

    Read directly (not via load_watchlist, which merges discovered.yaml back in) so
    discovery never re-adds a curated name — that was how Anthropic/Harvey dups crept
    into discovered.yaml.
    """
    path = config_dir() / "watchlist.yaml"
    if not path.exists():
        return set()
    data = yaml.safe_load(path.read_text()) or {}
    return {c["id"] for grp in ("companies", "mena") for c in (data.get(grp) or []) if c.get("id")}


def merge_discovered(found: list[dict]) -> int:
    """Append genuinely-new candidates to config/discovered.yaml. Returns count added.

    Dedups against BOTH discovered.yaml and the curated watchlist, and drops obvious
    junk (no/blank name, single generic word with no domain).
    """
    path = config_dir() / "discovered.yaml"
    data = (yaml.safe_load(path.read_text()) if path.exists() else None) or {"companies": []}
    have = {c["id"] for c in data["companies"]} | _curated_ids()
    new = []
    for c in found:
        cid = c.get("id", "")
        if not cid or cid in have:
            continue
        # junk gate: a bare single-word name with no domain is usually a mis-extraction.
        if not c.get("domain") and "-" not in cid and len(cid) <= 4:
            continue
        have.add(cid)
        new.append(c)
    if new:
        data["companies"].extend(new)
        path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    return len(new)


if __name__ == "__main__":  # ponytail: dedup self-check, no network
    import tempfile, os
    os.environ["OPENPITCH_CONFIG_DIR"] = tempfile.mkdtemp()
    assert merge_discovered([{"id": "factory", "name": "Factory"}]) == 1
    assert merge_discovered([{"id": "factory", "name": "Factory"}]) == 0
    print("ok")
