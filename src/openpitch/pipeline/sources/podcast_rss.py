"""Podcast adapter — the freshness edge (FRD §7).

Founders/operators leak metrics on VC/startup podcasts before any database.
We scan a configured set of show RSS feeds for recent episodes that mention a
company; matching episodes become RawItems flagged for transcription (the
transcribe stage handles audio → text; published transcripts are preferred).

`episodes_mentioning` is pure; `fetch` does network. Feeds: config/podcasts.yaml
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from .base import RawItem, mentions, parse_date
from ...models import Company, SourceType

CONFIG = Path(__file__).resolve().parents[4] / "config" / "podcasts.yaml"


def load_feeds(path: Path = CONFIG) -> list[dict]:
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text()) or {}
    return [f for f in data.get("feeds", []) if f.get("feed_url")]


def _audio_url(entry) -> str | None:
    for enc in entry.get("enclosures", []) or []:
        href = enc.get("href") or enc.get("url")
        if href:
            return href
    links = entry.get("links", []) or []
    for ln in links:
        if (ln.get("type") or "").startswith("audio"):
            return ln.get("href")
    return None


def episodes_mentioning(parsed, company: Company, show_name: str) -> list[RawItem]:
    """Pure: episodes from one show that mention the company."""
    items: list[RawItem] = []
    for entry in getattr(parsed, "entries", []):
        title = entry.get("title")
        summary = entry.get("summary", "")
        if not mentions(company, title, summary):
            continue
        items.append(
            RawItem(
                company_id=company.id,
                source_type=SourceType.PODCAST,
                source_name=show_name,
                title=title,
                text=summary,                       # replaced by transcript downstream
                url=entry.get("link"),
                published_at=parse_date(entry.get("published")),
                needs_transcription=True,
                audio_url=_audio_url(entry),
            ).finalize()
        )
    return items


def fetch(company: Company, *, feeds: list[dict] | None = None, client=None, limit: int = 6) -> list[RawItem]:
    """Fetch the `limit` most-recent episodes (across feeds) that mention the company.

    The cap keeps a live run inside free-tier LLM quota — these shows mention the
    big labs constantly, so we take only the freshest mentions.
    """
    import feedparser
    import httpx

    feeds = feeds if feeds is not None else load_feeds()
    owns_client = client is None
    client = client or httpx.Client(timeout=8.0, follow_redirects=True)
    items: list[RawItem] = []
    try:
        for feed in feeds:
            try:
                resp = client.get(feed["feed_url"])
                resp.raise_for_status()
            except Exception:  # noqa: BLE001 — one feed failing must not abort the company
                continue
            parsed = feedparser.parse(resp.content)
            items.extend(episodes_mentioning(parsed, company, feed.get("name", "Podcast")))
        items.sort(key=lambda it: it.published_at or date(1970, 1, 1), reverse=True)
        return items[:limit]
    finally:
        if owns_client:
            client.close()
