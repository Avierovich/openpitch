"""Auto-discovery — promote AI startups from funding news into the universe.

ponytail: broad Google News RSS + one LLM extraction call, appended to
config/discovered.yaml (the curated watchlist.yaml is never rewritten).
The scoring layer then ranks them with everyone else.
"""

from __future__ import annotations

import re
import urllib.parse
from functools import lru_cache

import yaml

from ..paths import config_dir
from .llm import LLMProvider

# Corporate suffixes/filler stripped before matching a candidate against SEC names,
# so "ZoomInfo" matches "ZOOMINFO TECHNOLOGIES INC.".
_CORP_NOISE = {"inc", "corp", "corporation", "co", "ltd", "limited", "llc", "plc", "lp",
               "holdings", "holding", "technologies", "technology", "labs", "ai", "group",
               "the", "company", "sa", "nv", "ag", "se"}


def _norm_name(name: str) -> str:
    toks = [t for t in re.sub(r"[^a-z0-9 ]+", " ", (name or "").lower()).split()
            if t not in _CORP_NOISE]
    return "".join(toks)


@lru_cache(maxsize=1)
def _public_company_names() -> frozenset:
    """Normalized names of US exchange-listed (public) companies, from SEC's free
    company_tickers.json (no key). Empty set on any failure — fail-open so a network
    blip never blocks discovery; the LLM `status` label remains as a softer backstop.
    """
    import httpx

    from .sources.edgar import sec_headers
    try:
        r = httpx.get("https://www.sec.gov/files/company_tickers.json",
                      headers=sec_headers(), timeout=10.0)
        r.raise_for_status()
        return frozenset(n for v in r.json().values()
                         if (n := _norm_name(v.get("title", ""))))
    except Exception:  # noqa: BLE001 — best-effort; never block discovery on this
        return frozenset()

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
    '("sales" OR "revenue operations" OR RevOps OR "data enrichment" OR CRM) AI startup funding',
    '("AI chip" OR semiconductor OR "AI accelerator" OR inference hardware) startup funding',
]


def _feed(q: str) -> str:
    return "https://news.google.com/rss/search?" + urllib.parse.urlencode(
        {"q": q, "hl": "en-US", "gl": "US", "ceid": "US:en"})


def _sys() -> str:
    from .classify import VOCAB
    vocab = "; ".join(f"{m}: {', '.join(subs)}" for m, subs in VOCAB.items())
    return (
        "Extract companies that are AI-native or meaningfully AI-ENABLED (AI is core "
        "to the product/value), across any vertical — including AI fintech, AI healthcare, and "
        "defense/autonomous AI. Skip companies with no real AI angle and investors/VC firms. "
        "For each give name; domain if obvious; a `status` of exactly 'private', 'public', or "
        "'acquired' (best estimate of the company's current standing); a `category` from this fixed "
        f"list and a matching `subcategory` from its options ({vocab}); a short free-text "
        "`specialty` (<=8 words); and a `summary` of 1-2 plain-English sentences on what the company does."
    )


_SCHEMA = {
    "type": "object",
    "properties": {"companies": {"type": "array", "items": {
        "type": "object", "required": ["name"], "properties": {
            "name": {"type": "string"}, "category": {"type": "string"},
            "status": {"type": "string", "enum": ["private", "public", "acquired"]},
            "subcategory": {"type": "string"}, "specialty": {"type": "string"},
            "summary": {"type": "string"}, "domain": {"type": "string"},
        }}}},
    "required": ["companies"],
}


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def discover(*, llm: LLMProvider, per_query: int = 15, max_chars: int = 24000) -> list[dict]:
    """One LLM call over recent multi-sector funding headlines → candidate companies.

    ponytail: payload bounded to max_chars (~6k tokens) so the single extraction call
    stays under free-tier per-request limits (Groq fallback caps ~12k tokens); each
    headline trimmed since the company name + raise sit at the front. Raise the cap or
    page the LLM call only if a run measurably starves on candidates.
    """
    import feedparser

    seen, headlines, budget = set(), [], max_chars
    for q in _QUERIES:
        for e in feedparser.parse(_feed(q)).entries[:per_query]:
            t = f"{e.get('title', '')}. {e.get('summary', '')}".strip()[:280]
            if t and t not in seen and budget - len(t) > 0:
                seen.add(t)
                headlines.append(t)
                budget -= len(t) + 1
    text = "\n".join(headlines)
    if not text.strip():
        return []
    return _normalize(llm.complete_json(_sys(), text, _SCHEMA))


def _normalize(data: dict | None) -> list[dict]:
    """LLM extraction dict -> candidate rows, forcing categories into the controlled VOCAB."""
    from .classify import VOCAB

    out = []
    for c in (data or {}).get("companies", []):
        name = (c.get("name") or "").strip()
        if not name:
            continue
        # Scope: private companies only. The LLM is unreliable at OMITTING public/acquired
        # names, so we have it LABEL status and drop here in code (unlabeled => assume private).
        if (c.get("status") or "private").strip().lower() in ("public", "acquired"):
            continue
        cat = c.get("category") if c.get("category") in VOCAB else "vertical-app"
        sub = c.get("subcategory") if c.get("subcategory") in VOCAB.get(cat, []) else None
        out.append({"id": _slug(name), "name": name, "category": cat,
                    "subcategory": sub, "specialty": (c.get("specialty") or None),
                    "summary": (c.get("summary") or None),
                    "domain": (c.get("domain") or "").strip().strip(",").strip() or None,
                    "segment": "global"})
    return out


# Sectors OpenPitch wants RELIABLY covered. News discovery only catches a company the week
# it's in a funding headline, so established names whose raise is months old (Clay, Apollo,
# Gong, Cerebras...) never reappear. Backfill enumerates them from the LLM's own knowledge.
_BACKFILL_SECTORS = [
    "sales tech, RevOps, and go-to-market automation",
    "data enrichment and sales intelligence",
    "AI chips, semiconductors, and inference hardware",
    "defense and autonomous systems",
    "AI infrastructure, inference, and model serving",
    "AI developer tools and coding agents",
    "vertical AI for legal, healthcare, and finance",
    "generative media — AI video, image, voice, and music",
]


def backfill(*, llm: LLMProvider, per_sector: int = 12) -> list[dict]:
    """Knowledge-backfill: ask the LLM to enumerate established PRIVATE companies per sector,
    so names absent from this week's news still enter systematically. Same VOCAB normalization
    and the same downstream corroboration as news discovery — a candidate with no real funding
    source never becomes a profile, so a stale/wrong enumeration is harmless until corroborated.

    ponytail: LLM enumeration over a fixed sector list (no flaky article scraping). Add a sector
    when coverage misses one; swap to a real registry only if hallucinated names become a problem.
    """
    out = []
    for sector in _BACKFILL_SECTORS:
        prompt = (f"List up to {per_sector} of the most notable PRIVATE, still-independent "
                  f"(not public, not acquired) companies in: {sector}.")
        out.extend(_normalize(llm.complete_json(_sys(), prompt, _SCHEMA)))
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

    Dedups against BOTH discovered.yaml and the curated watchlist, drops obvious junk
    (no/blank name, single generic word with no domain), and drops US-listed PUBLIC
    companies (out of scope) via an authoritative SEC company_tickers.json match.
    """
    path = config_dir() / "discovered.yaml"
    data = (yaml.safe_load(path.read_text()) if path.exists() else None) or {"companies": []}
    have = {c["id"] for c in data["companies"]} | _curated_ids()
    public = _public_company_names()  # one network fetch per run; {} if unavailable
    new = []
    for c in found:
        cid = c.get("id", "")
        if not cid or cid in have:
            continue
        # junk gate: a bare single-word name with no domain is usually a mis-extraction.
        if not c.get("domain") and "-" not in cid and len(cid) <= 4:
            continue
        # scope gate: SEC-listed name => public, out of scope (catches ZoomInfo/Palantir
        # that the LLM `status` label misses). ponytail: exact normalized-name match, so a
        # private startup sharing a public co's exact core name is a rare false drop.
        if (nm := _norm_name(c.get("name", ""))) and nm in public:
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
    # _normalize forces an out-of-vocab category back into the controlled list,
    # keeps private (incl. unlabeled), and drops public/acquired.
    row = _normalize({"companies": [{"name": "Clay", "category": "made-up"}]})[0]
    assert row["id"] == "clay" and row["category"] == "vertical-app"
    assert _normalize({"companies": [{"name": "ZoomInfo", "status": "public"}]}) == []
    assert _normalize({"companies": [{"name": "Clearbit", "status": "acquired"}]}) == []
    # SEC name normalization strips corporate noise so candidate <-> filing names match.
    assert _norm_name("ZOOMINFO TECHNOLOGIES INC.") == _norm_name("ZoomInfo") == "zoominfo"
    # Public-gate: a SEC-listed name is dropped even when the LLM mislabels it private.
    globals()["_public_company_names"] = lambda: frozenset({"zoominfo"})
    assert merge_discovered([{"id": "zoominfo", "name": "ZoomInfo", "domain": "zoominfo.com"}]) == 0
    assert merge_discovered([{"id": "clay", "name": "Clay", "domain": "clay.com"}]) == 1
    print("ok")
