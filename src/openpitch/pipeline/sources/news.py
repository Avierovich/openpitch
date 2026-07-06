"""News adapter via Google News RSS (FRD §7).

Free, no API key. We bias the query toward money/growth language so the feed
surfaces funding- and metric-relevant coverage rather than generic mentions.

`parse_feed` is pure (takes a parsed feedparser object); `fetch` does network.
"""

from __future__ import annotations

import re
import urllib.parse

from .base import RawItem, parse_date
from .company_site import extract_text
from ...models import Company, SourceType

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"
QUERY_TERMS = "funding OR raises OR valuation OR ARR OR revenue OR Series"
# A second, metric-specific angle surfaces DIFFERENT articles (and outlets) than the
# broad funding query — more independent sources => more corroboration (WS2).
METRIC_TERMS = '"revenue run rate" OR "annual recurring" OR "post-money" OR "raised at"'


def build_query_url(name: str, terms: str = QUERY_TERMS) -> str:
    q = f'"{name}" ({terms})'
    params = urllib.parse.urlencode({"q": q, "hl": "en-US", "gl": "US", "ceid": "US:en"})
    return f"{GOOGLE_NEWS_RSS}?{params}"


def parse_feed(parsed, company_id: str) -> list[RawItem]:
    """Pure: feedparser result -> RawItems."""
    items: list[RawItem] = []
    for entry in getattr(parsed, "entries", []):
        title = entry.get("title")
        # Google News summaries are redirect-stub anchor tags that just echo the title —
        # strip markup and drop the echo so no stub HTML wastes the extractor's budget.
        summary = extract_text(entry.get("summary", ""), limit=500)
        text = title if not summary or (title and title in summary) else f"{title}. {summary}"
        source_name = (entry.get("source", {}) or {}).get("title") or "Google News"
        items.append(
            RawItem(
                company_id=company_id,
                source_type=SourceType.NEWS,
                source_name=source_name,
                title=title,
                text=text,
                url=entry.get("link"),
                published_at=parse_date(entry.get("published")),
            ).finalize()
        )
    return items


# ── signal ranking (the anti-headline-lottery) ────────────────────────────────
# Google News returns ~100 recency-ordered entries; only `limit` survive. Recency
# order let "$950M raise" echoes crowd out the one headline stating the valuation
# (the Sierra failure). Rank by metric signal instead; stable sort keeps recency
# within ties.

_VALUATION_RE = re.compile(r"\bvaluation\b|valued at|post-money|worth \$", re.I)
_MONEY_RE = re.compile(r"\$\s?\d[\d,.]*\s*(?:billion|bn|million|mn|[bm])\b", re.I)
_REVENUE_RE = re.compile(r"\bARR\b|annual recurring|run[- ]rate|revenue", re.I)
_FUNDING_RE = re.compile(r"\braises?\b|\braised\b|series [a-k]\b|funding round|seed round", re.I)

# Tokens that legitimately follow a company name without changing which entity it is.
_ENTITY_ALLOW = {"AI", "Inc", "Inc.", "Labs", "Lab", "Technologies", "Technology", "Co", "Co.", "HQ"}
# Headline verbs/connectors marking the name as standalone even in Title Case
# ("Sierra Raises $350M"). Checked case-insensitively.
_CONNECTORS = {
    "raises", "raised", "raising", "hits", "hit", "reaches", "reached", "nears",
    "secures", "secured", "lands", "gets", "closes", "eyes", "tops", "crosses",
    "doubles", "triples", "valued", "seeks", "seeking", "says", "said", "is", "was",
    "has", "will", "could", "may", "set", "now", "to", "at", "in", "on", "and",
    "the", "its", "just", "reportedly", "officially",
}


def entity_mismatch(text: str, name: str, aliases: list[str] = ()) -> bool:
    """True when EVERY occurrence of the company name reads as part of a larger
    proper-noun entity ("Sierra Space", "American Sierra Gold") — a different company.

    ponytail: known ceiling — a Title-Case headline with an off-list adverb
    ("Sierra Poised To…") is wrongly demoted; it only costs a ranking slot, and the
    extraction prompt's company context is the correctness backstop.
    """
    names = [n for n in (name, *aliases) if n]
    allow = _ENTITY_ALLOW | {t for n in names for t in n.split()}
    saw = standalone = False
    for n in names:
        for m in re.finditer(rf"(?<![\w'’]){re.escape(n)}(?=\W|$)", text):
            saw = True
            tail = text[m.end():]
            if re.match(r"['’]s\b", tail):                       # "Sierra's valuation"
                standalone = True
                continue
            nxt = re.match(r"\s+([A-Za-z][\w.&-]*)", tail)
            if not nxt:                                          # end / "," / "$"
                standalone = True
                continue
            tok = nxt.group(1)
            if tok in allow or tok.lower() in _CONNECTORS or not tok[0].isupper():
                standalone = True
    return saw and not standalone


def signal_score(text: str, company: Company) -> int:
    score = 0
    if _VALUATION_RE.search(text):
        score += 3
    if _MONEY_RE.search(text):
        score += 2
    if _REVENUE_RE.search(text):
        score += 2
    if _FUNDING_RE.search(text):
        score += 1
    if entity_mismatch(text, company.name, company.aliases):
        score -= 5
    return score


def rank_items(items: list[RawItem], company: Company) -> list[RawItem]:
    return sorted(items, key=lambda it: -signal_score(f"{it.title or ''} {it.text}", company))


def fetch(company: Company, *, client=None, limit: int = 15) -> list[RawItem]:
    import feedparser
    import httpx

    owns_client = client is None
    client = client or httpx.Client(timeout=8.0, follow_redirects=True)
    items: list[RawItem] = []
    seen: set[str] = set()
    try:
        # Broad funding query first, then the metric-specific angle for extra outlets.
        for terms in (QUERY_TERMS, METRIC_TERMS):
            try:
                resp = client.get(build_query_url(company.name, terms))
                resp.raise_for_status()
            except Exception:  # noqa: BLE001 — one query failing must not abort the company
                continue
            for it in parse_feed(feedparser.parse(resp.content), company.id):
                key = it.url or it.title or ""
                if key and key not in seen:
                    seen.add(key)
                    items.append(it)
        # Rank by metric signal so valuation/ARR-bearing headlines always survive the
        # cap — recency order alone let redundant raise-echoes crowd them out.
        return rank_items(items, company)[:limit]
    finally:
        if owns_client:
            client.close()
