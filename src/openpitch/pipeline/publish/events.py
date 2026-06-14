"""Event detection (FRD §8.5, EVENTS-SPEC) — what materially moved.

Emits typed events by diffing new resolved values against the previously
published ones. Materiality thresholds + band-crossings come from EVENTS-SPEC.
Because "previous" is the last published value, repeats are inherently deduped.
"""

from __future__ import annotations

from datetime import datetime

from ...models import Event, EventPayload, EventType, EstimateType, ResolvedValue, Source

# Materiality: (min pct change, [absolute bands that, if crossed, also fire]).
_THRESHOLDS: dict[str, tuple[float, list[float]]] = {
    "arr": (15.0, [10e6, 50e6, 100e6, 250e6]),
    "revenue_growth": (25.0, []),
    "valuation": (20.0, []),
    "total_funding": (15.0, []),
    "headcount": (10.0, [100, 500, 1000]),
    "subscribers": (25.0, []),
}


def _is_num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _crosses(prev: float, cur: float, bands: list[float]) -> bool:
    lo, hi = min(prev, cur), max(prev, cur)
    return any(lo < b <= hi for b in bands)


def _material(metric: str, prev: float, cur: float) -> bool:
    pct_floor, bands = _THRESHOLDS.get(metric, (20.0, []))
    if prev == 0:
        return cur != 0
    pct = abs(cur - prev) / abs(prev) * 100
    return pct >= pct_floor or _crosses(prev, cur, bands)


def _event_type(metric: str) -> EventType:
    if metric == "valuation":
        return EventType.VALUATION_UPDATE
    return EventType.METRIC_UPDATE


def detect_events(
    company_id: str,
    company_name: str,
    prev_metrics: dict[str, ResolvedValue],
    new_metrics: dict[str, ResolvedValue],
    *,
    sources_by_metric: dict[str, list[Source]] | None = None,
    now: datetime,
) -> list[Event]:
    sources_by_metric = sources_by_metric or {}
    day = now.date().isoformat()
    events: list[Event] = []

    for metric, rv in new_metrics.items():
        prev = prev_metrics.get(metric)

        # Contradiction newly raised.
        if rv.contradiction and not (prev and prev.contradiction):
            events.append(Event(
                id=f"evt_{day}_{company_id}_{metric}_contradiction",
                type=EventType.CONTRADICTION_FLAGGED,
                company_id=company_id, company_name=company_name,
                summary=f"{company_name}: public-source discrepancy on {metric}",
                payload=EventPayload(metric=metric, current=rv.value),
                confidence=rv.confidence, estimate_type=rv.estimate_type,
                sources=sources_by_metric.get(metric, []), detected_at=now,
            ))

        # Material value change vs last published.
        if prev and _is_num(prev.value) and _is_num(rv.value) and _material(metric, float(prev.value), float(rv.value)):
            change = round((float(rv.value) - float(prev.value)) / abs(float(prev.value)) * 100, 1) if prev.value else None
            events.append(Event(
                id=f"evt_{day}_{company_id}_{metric}",
                type=_event_type(metric),
                company_id=company_id, company_name=company_name,
                summary=f"{company_name} {metric} changed {prev.value} → {rv.value}",
                payload=EventPayload(metric=metric, previous=prev.value, current=rv.value, change_pct=change),
                confidence=rv.confidence, estimate_type=rv.estimate_type,
                sources=sources_by_metric.get(metric, []), detected_at=now,
            ))

    return events
