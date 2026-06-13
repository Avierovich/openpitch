"""Source adapters (FRD §7, stage 2).

Each adapter exposes a pure parser (unit-tested without network) and a thin
`fetch(company) -> list[RawItem]`. Adapters MUST respect robots.txt / ToS and
prefer official APIs and already-published transcripts (BRD NFR-02).

v1 adapters: edgar · news · podcast_rss · company_site.
"""

from __future__ import annotations

from . import company_site, edgar, news, podcast_rss
from .base import RawItem, SourceAdapter, mentions, parse_date

# Adapter modules in default run order (cheap/high-trust first).
ADAPTERS = [edgar, news, podcast_rss, company_site]

__all__ = [
    "RawItem",
    "SourceAdapter",
    "mentions",
    "parse_date",
    "ADAPTERS",
    "edgar",
    "news",
    "podcast_rss",
    "company_site",
]
