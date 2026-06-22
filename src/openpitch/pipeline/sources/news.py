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


def build_query_url(name: str) -> str:
    q = f'"{name}" ({QUERY_TERMS})'
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


def fetch(company: Company, *, client=None, limit: int = 10) -> list[RawItem]:
    import feedparser
    import httpx

    owns_client = client is None
    client = client or httpx.Client(timeout=8.0, follow_redirects=True)
    try:
        resp = client.get(build_query_url(company.name))
        resp.raise_for_status()
        parsed = feedparser.parse(resp.content)
        return parse_feed(parsed, company.id)[:limit]  # Google News RSS is recency-ordered
    finally:
        if owns_client:
            client.close()
