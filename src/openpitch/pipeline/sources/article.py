"""Targeted article source — full-body news fetch for gap-fill (NOT in ADAPTERS).

Google News RSS links are JS-redirect stubs whose bodies can't be fetched, so the
regular news adapter is headline-only. When a company's headline metrics have a gap
(funding known, valuation missing), this module runs a targeted Bing News RSS query —
Bing's `apiclick` links carry the REAL publisher URL in the `url=` param — fetches a
few article bodies, and hands them to extraction. Bounded and polite per DATA-POLICY:
one RSS GET + ≤3 article GETs per gap company per run.

`build_query_url`, `publisher_url`, and `parse_feed` are pure; fetchers do network.
"""

from __future__ import annotations

import hashlib
import urllib.parse

from .base import RawItem, parse_date
from .company_site import extract_text
from .news import entity_mismatch, rank_items
from ...models import Company, SourceType

BING_NEWS_RSS = "https://www.bing.com/news/search"
VALUATION_TERMS = 'valuation OR "valued at" OR "post-money"'
# Descriptive bot-compat UA (DATA-POLICY): names the bot; bare library UAs get blocked.
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; OpenPitch/0.1)"}
BODY_CAP = 6000


def build_query_url(name: str, terms: str = VALUATION_TERMS) -> str:
    q = f'"{name}" ({terms})'
    return f"{BING_NEWS_RSS}?" + urllib.parse.urlencode({"q": q, "format": "rss"})


def publisher_url(link: str | None) -> str | None:
    """Unwrap Bing's apiclick redirect to the real publisher URL; passthrough otherwise."""
    if not link:
        return None
    parts = urllib.parse.urlparse(link)
    if parts.netloc.endswith("bing.com"):
        target = urllib.parse.parse_qs(parts.query).get("url", [None])[0]
        return target or None
    return link


def parse_feed(parsed, company: Company) -> list[RawItem]:
    """Pure: Bing RSS -> RawItems with real publisher URLs.

    Entity mismatches are HARD-filtered here (unlike the ranking-only demotion in
    news.py) because every surviving candidate costs a real article fetch.
    """
    items: list[RawItem] = []
    seen: set[str] = set()
    for entry in getattr(parsed, "entries", []):
        url = publisher_url(entry.get("link"))
        title = entry.get("title") or ""
        if not url or url in seen or entity_mismatch(title, company.name, company.aliases):
            continue
        seen.add(url)
        source_name = ((entry.get("source", {}) or {}).get("title")
                       or urllib.parse.urlparse(url).netloc.removeprefix("www."))
        snippet = extract_text(entry.get("summary", ""), limit=300)
        items.append(RawItem(
            company_id=company.id,
            source_type=SourceType.NEWS,
            source_name=source_name,
            title=title,
            text=f"{title}. {snippet}" if snippet else title,
            url=url,
            published_at=parse_date(entry.get("published")),
            # Hash on url|title, NOT text: article bodies churn (ads/js remnants) and
            # would defeat the extraction cache. Immutable-article assumption;
            # --no-cache is the escape hatch.
            content_hash=hashlib.sha256(f"{url}|{title}".encode()).hexdigest()[:16],
        ))
    return items


def fetch_candidates(company: Company, *, client=None, limit: int = 6,
                     terms: str = VALUATION_TERMS) -> list[RawItem]:
    """One Bing RSS GET -> ranked candidate articles (no bodies yet)."""
    import feedparser
    import httpx

    owns = client is None
    client = client or httpx.Client(timeout=6.0, follow_redirects=True)
    try:
        resp = client.get(build_query_url(company.name, terms), headers=HEADERS)
        resp.raise_for_status()
        cands = parse_feed(feedparser.parse(resp.content), company)
        return rank_items(cands, company)[:limit]
    finally:
        if owns:
            client.close()


def fetch_bodies(items: list[RawItem], *, client=None, limit: int = 3,
                 cap: int = BODY_CAP) -> list[RawItem]:
    """Fetch article bodies for the first `limit` items; failures are dropped
    (and deliberately NOT cached) so they retry on the next run."""
    import httpx

    owns = client is None
    client = client or httpx.Client(timeout=6.0, follow_redirects=True)
    out: list[RawItem] = []
    try:
        for it in items[:limit]:
            try:
                resp = client.get(it.url, headers=HEADERS)
                if resp.status_code != 200 or not resp.text:
                    continue
                it.text = f"{it.title}. {extract_text(resp.text, limit=cap)}"
                out.append(it)
            except Exception:  # noqa: BLE001 — one article failing must not abort gap-fill
                continue
    finally:
        if owns:
            client.close()
    return out
