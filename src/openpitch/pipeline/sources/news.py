"""News adapter via Google News RSS (FRD §7).

Free, no API key. We bias the query toward money/growth language so the feed
surfaces funding- and metric-relevant coverage rather than generic mentions.

`parse_feed` is pure (takes a parsed feedparser object); `fetch` does network.
"""

from __future__ import annotations

import urllib.parse

from .base import RawItem, parse_date
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
        summary = entry.get("summary", "")
        source_name = (entry.get("source", {}) or {}).get("title") or "Google News"
        items.append(
            RawItem(
                company_id=company_id,
                source_type=SourceType.NEWS,
                source_name=source_name,
                title=title,
                text=f"{title}. {summary}",
                url=entry.get("link"),
                published_at=parse_date(entry.get("published")),
            ).finalize()
        )
    return items


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
        return items[:limit]  # Google News RSS is recency-ordered; dedup keeps both angles
    finally:
        if owns_client:
            client.close()
