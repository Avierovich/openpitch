"""Company-site adapter — hiring/growth signals (FRD §7, leading indicators).

Best-effort: pulls the homepage and a careers page if present. The extractor
later mines these for headcount, customer logos, and (via the careers page)
hiring velocity — used for self-anchored implied-growth signals (FRD §5.5).

`careers_candidates` and `extract_text` are pure; `fetch` does network.
"""

from __future__ import annotations

import re

from .base import RawItem
from ...models import Company, SourceType

CAREERS_PATHS = ("/careers", "/jobs", "/about", "/company")
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def careers_candidates(domain: str) -> list[str]:
    base = f"https://{domain.rstrip('/')}"
    return [base, *[f"{base}{p}" for p in CAREERS_PATHS]]


def extract_text(html: str, *, limit: int = 4000) -> str:
    """Pure: strip tags/whitespace to plain text, truncated for the extractor."""
    text = _TAG_RE.sub(" ", html)
    text = _WS_RE.sub(" ", text).strip()
    return text[:limit]


def fetch(company: Company, *, client=None) -> list[RawItem]:
    import httpx

    if not company.website:
        return []
    domain = company.website.replace("https://", "").replace("http://", "").strip("/")
    owns_client = client is None
    client = client or httpx.Client(timeout=15.0, follow_redirects=True)
    items: list[RawItem] = []
    try:
        for url in careers_candidates(domain):
            try:
                resp = client.get(url, headers={"User-Agent": "OpenPitch/0.1"})
                if resp.status_code != 200 or not resp.text:
                    continue
                items.append(
                    RawItem(
                        company_id=company.id,
                        source_type=SourceType.WEB,
                        source_name=domain,
                        title=url,
                        text=extract_text(resp.text),
                        url=url,
                    ).finalize()
                )
            except Exception:  # noqa: BLE001 — one URL failing must not abort the company
                continue
    finally:
        if owns_client:
            client.close()
    return items
