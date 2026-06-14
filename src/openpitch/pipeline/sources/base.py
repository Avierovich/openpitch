"""Source-adapter contract (FRD §7, stage 2).

Every adapter turns a Company into a list of RawItems (text or audio) for the
extraction stage. I/O (fetch) is kept separate from parsing so parsers are pure
and unit-testable without network access.

RawItems are content-hashed for caching/incrementality — an unchanged item
skips re-extraction, keeping us inside free-tier limits (BRD §9.1).
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime
from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from ...models import Company, SourceType


class RawItem(BaseModel):
    company_id: str
    source_type: SourceType
    source_name: str
    title: str | None = None
    text: str = ""                       # content fed to extraction (or transcript)
    url: str | None = None
    locator: str | None = None           # timestamp / accession / anchor
    published_at: date | None = None
    needs_transcription: bool = False     # podcast audio without a transcript
    audio_url: str | None = None
    content_hash: str = ""

    def finalize(self) -> "RawItem":
        """Compute the content hash if not already set."""
        if not self.content_hash:
            basis = f"{self.url}|{self.title}|{self.text}|{self.audio_url}".encode()
            self.content_hash = hashlib.sha256(basis).hexdigest()[:16]
        return self


@runtime_checkable
class SourceAdapter(Protocol):
    name: str

    def fetch(self, company: Company) -> list[RawItem]: ...


# ── shared helpers ───────────────────────────────────────────────────────────


def mentions(company: Company, *texts: str | None) -> bool:
    """True if any of the company's names/aliases appears in the given text."""
    haystack = " ".join(t for t in texts if t).lower()
    names = [company.name, *company.aliases]
    return any(n.lower() in haystack for n in names if n)


def parse_date(value: str | None) -> date | None:
    """Best-effort date parse across the formats sources hand us."""
    if not value:
        return None
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    # ISO-ish fallback (e.g. 2026-06-13T05:00:00Z)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None
