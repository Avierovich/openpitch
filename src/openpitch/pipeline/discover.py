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

FEED = "https://news.google.com/rss/search?" + urllib.parse.urlencode({
    "q": '("AI startup" OR "AI company") (raises OR funding OR Series OR valuation)',
    "hl": "en-US", "gl": "US", "ceid": "US:en",
})

_SYS = (
    "Extract AI startups that recently raised funding from these news headlines. "
    "Return ONLY real, private AI companies — skip public companies, investors/VC firms, "
    "and generic mentions. For each give name, a short category, and domain if obvious."
)
_SCHEMA = {
    "type": "object",
    "properties": {"companies": {"type": "array", "items": {
        "type": "object", "required": ["name"], "properties": {
            "name": {"type": "string"}, "category": {"type": "string"}, "domain": {"type": "string"},
        }}}},
    "required": ["companies"],
}


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def discover(*, llm: LLMProvider, limit: int = 40) -> list[dict]:
    """One LLM call over recent AI-funding headlines → candidate companies."""
    import feedparser

    entries = feedparser.parse(FEED).entries[:limit]
    text = "\n".join(f"{e.get('title', '')}. {e.get('summary', '')}" for e in entries)
    if not text.strip():
        return []
    data = llm.complete_json(_SYS, text, _SCHEMA) or {}
    out = []
    for c in data.get("companies", []):
        name = (c.get("name") or "").strip()
        if name:
            out.append({"id": _slug(name), "name": name, "category": c.get("category") or "ai",
                        "domain": c.get("domain") or None, "segment": "global"})
    return out


def merge_discovered(found: list[dict]) -> int:
    """Append new candidates to config/discovered.yaml (dedup by id). Returns count added."""
    path = config_dir() / "discovered.yaml"
    data = (yaml.safe_load(path.read_text()) if path.exists() else None) or {"companies": []}
    have = {c["id"] for c in data["companies"]}
    new = [c for c in found if c["id"] not in have]
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
