"""Extraction cache — skip re-running the LLM on unchanged source items.

A source item's `content_hash` (url|title|text|audio) identifies it; once extracted,
its claims are cached under "<company_id>:<hash>" in data/cache/seen.json. The next
run reuses them instead of paying the LLM again, while still carrying the claims
forward (so coverage doesn't regress). Items that yielded NO claims are cached as []
so they aren't re-sent either. Keyed by company so a shared article can't leak claims
between companies. `split`/`record` are pure for testability.
"""

from __future__ import annotations

import json

from ..models import Claim
from ..paths import data_dir


def _path():
    return data_dir() / "cache" / "seen.json"


def load() -> dict:
    p = _path()
    return json.loads(p.read_text()) if p.exists() else {}


def save(cache: dict) -> None:
    from .. import store
    store._write_json(_path(), cache)  # atomic write


def _key(company_id: str, content_hash: str) -> str:
    return f"{company_id}:{content_hash}"


def split(text_items, company_id: str, cache: dict):
    """Partition items into (reused_claims, items_to_extract) using the cache."""
    reused: list[Claim] = []
    to_extract = []
    for it in text_items:
        hit = cache.get(_key(company_id, it.content_hash))
        if hit is not None:                       # seen before (possibly empty)
            reused.extend(Claim.model_validate(c) for c in hit)
        else:
            to_extract.append(it)
    return reused, to_extract


def record(cache: dict, company_id: str, to_extract, new_claims) -> dict:
    """Cache the freshly-extracted claims per source item (matched by url→hash), and
    mark every just-extracted item as seen — including the dry ones (empty list)."""
    url_to_hash = {it.url: it.content_hash for it in to_extract if it.url}
    by_hash: dict[str, list] = {}
    for cl in new_claims:
        h = url_to_hash.get(cl.source.url)
        if h:
            by_hash.setdefault(h, []).append(cl.model_dump(mode="json"))
    for it in to_extract:
        cache[_key(company_id, it.content_hash)] = by_hash.get(it.content_hash, [])
    return cache
