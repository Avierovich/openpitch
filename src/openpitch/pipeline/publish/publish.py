"""Persist a company's resolved data + emit events + build the digest (FRD §7)."""

from __future__ import annotations

from datetime import datetime

from ... import store
from ...models import Claim, Company, Event, Source
from .events import detect_events


def _sources_by_metric(claims: list[Claim]) -> dict[str, list[Source]]:
    out: dict[str, list[Source]] = {}
    for c in claims:
        out.setdefault(c.metric, [])
        if c.source.type.value != "derived" and c.source not in out[c.metric]:
            out[c.metric].append(c.source)
    return out


def publish_company(
    company: Company, claims: list[Claim], *, now: datetime
) -> list[Event]:
    """Persist a company profile + claims + history, and return emitted events."""
    prev = store.read_company(company.id)
    prev_metrics = prev.metrics if prev else {}

    events = detect_events(
        company.id, company.name, prev_metrics, company.metrics,
        sources_by_metric=_sources_by_metric(claims), now=now,
    )

    store.write_claims(company.id, claims)
    store.write_company(company)

    # Append history only when a metric's value changed since the last snapshot.
    for metric, rv in company.metrics.items():
        last = store.last_history(company.id, metric)
        if last is None or last.value != rv.value or last.confidence != rv.confidence:
            store.append_history(company.id, metric, rv)

    store.append_events(events)
    return events


def write_digest_for(day: str, events: list[Event]) -> str:
    """Render + persist the 'what moved today' digest; returns the markdown."""
    lines = [f"# What moved — {day}", ""]
    if not events:
        lines.append("_No material changes today._")
    else:
        by_company: dict[str, list[Event]] = {}
        for e in events:
            by_company.setdefault(e.company_name or e.company_id, []).append(e)
        for company, evs in sorted(by_company.items()):
            lines.append(f"## {company}")
            for e in evs:
                band = "high" if e.confidence >= 0.75 else "medium" if e.confidence >= 0.5 else "low"
                lines.append(f"- **{e.type.value}** — {e.summary} _(confidence: {band})_")
            lines.append("")
    md = "\n".join(lines)
    store.write_digest(day, md)
    return md
