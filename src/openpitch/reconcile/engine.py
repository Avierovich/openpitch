"""Reconciliation engine (FRD §5) — the hard, valuable core.

Takes all current claims for one (company, metric) and produces a single
ResolvedValue: a confidence-weighted estimate, a credible range, an
estimate_type, a contradiction flag, and a delta vs the previous value.

Never overwrites — the caller (publish stage) appends history. This module is
pure logic with no I/O, so it is fully unit-testable.
"""

from __future__ import annotations

from datetime import date

from ..models import Claim, Delta, EstimateType, Range, ResolvedValue
from .confidence import current_confidence, corroborate

CREDIBLE_FLOOR = 0.30        # claims below this don't widen the range (§5.1 step 5)
# A contradiction = a rival cluster that is BOTH meaningful in absolute terms AND a
# serious fraction of the dominant cluster. Relative (not a fixed floor) so it still
# fires on real, time-decayed data where single-source clusters sit well below 0.5.
CONTRADICTION_ABS = 0.15
CONTRADICTION_RATIO = 0.33
# A contradiction is a SAME-PERIOD disagreement, not a stale figure vs a newer one.
# Metrics like valuation/ARR grow via rounds, so two far-apart-in-time clusters are a
# trajectory, not a conflict. Only flag rivals whose freshest claim is within this
# window of the dominant cluster's freshest claim.
CONTRADICTION_WINDOW_DAYS = 120
# Metrics whose multiple values are sequential events (successive rounds, accumulating
# totals), not competing claims — never a "discrepancy".
SEQUENTIAL_METRICS = {"round_amount", "total_funding"}


def _numeric(claims: list[Claim]) -> list[Claim]:
    return [c for c in claims if isinstance(c.value, (int, float)) and not isinstance(c.value, bool)]


def _cluster(
    scored: list[tuple[Claim, float]], tolerance: float
) -> list[list[tuple[Claim, float]]]:
    """1-D greedy clustering by relative value proximity (§5.2).

    Claims are grouped when consecutive sorted values are within `tolerance`
    (relative). `scored` is a list of (claim, confidence) pairs.
    """
    if not scored:
        return []
    ordered = sorted(scored, key=lambda sc: float(sc[0].value))
    clusters: list[list[tuple[Claim, float]]] = [[ordered[0]]]
    for claim, conf in ordered[1:]:
        prev_val = float(clusters[-1][-1][0].value)
        cur_val = float(claim.value)
        denom = max(abs(prev_val), abs(cur_val), 1e-9)
        if abs(cur_val - prev_val) / denom <= tolerance:
            clusters[-1].append((claim, conf))
        else:
            clusters.append([(claim, conf)])
    return clusters


def _cluster_weight(cluster: list[tuple[Claim, float]]) -> float:
    return sum(conf for _, conf in cluster)


def _cluster_date(cluster: list[tuple[Claim, float]]) -> date | None:
    dates = [c.source.published_at for c, _ in cluster if c.source.published_at]
    return max(dates) if dates else None


def _public_source_names(cluster: list[tuple[Claim, float]]) -> set[str]:
    """Distinct PUBLIC (non-derived) source names backing a cluster."""
    return {c.source.name for c, _ in cluster if c.source.type.value != "derived"}


def reconcile(
    metric: str,
    claims: list[Claim],
    *,
    as_of: date,
    tau: float,
    tolerance: float,
    unit: str | None = None,
    previous: ResolvedValue | None = None,
    reliabilities: dict[str, float] | None = None,
    history_ref: str | None = None,
) -> ResolvedValue | None:
    """Reconcile claims for one metric into a single ResolvedValue.

    `reliabilities` maps source name -> learned reliability (optional).
    Returns None if there are no usable numeric claims.
    """
    reliabilities = reliabilities or {}
    numeric = _numeric(claims)
    if not numeric:
        return None

    scored = [
        (
            c,
            current_confidence(
                c, as_of=as_of, tau=tau, reliability=reliabilities.get(c.source.name)
            ),
        )
        for c in numeric
    ]

    clusters = _cluster(scored, tolerance)
    clusters.sort(key=_cluster_weight, reverse=True)
    dominant = clusters[0]

    # Confidence-weighted central estimate of the dominant cluster.
    total_w = _cluster_weight(dominant) or 1e-9
    value = sum(float(c.value) * w for c, w in dominant) / total_w

    # Range spans all *credible* claims, not just the dominant cluster.
    credible_vals = [float(c.value) for c, w in scored if w >= CREDIBLE_FLOOR]
    rng = (
        Range(low=min(credible_vals), high=max(credible_vals))
        if len(credible_vals) >= 2
        else None
    )

    # estimate_type: multiple independent sources agreeing => consensus.
    distinct_sources = {c.source.name for c, _ in dominant}
    estimate_type = (
        EstimateType.CONSENSUS if len(distinct_sources) > 1 else EstimateType.REPORTED
    )

    confidence = corroborate([w for _, w in dominant])

    # Contradiction: a rival cluster carries serious weight (absolute + relative to
    # dominant) AND is contemporaneous with it — not just an older/newer data point (§5.3).
    floor = max(CONTRADICTION_ABS, CONTRADICTION_RATIO * total_w)
    dom_date = _cluster_date(dominant)

    def _same_period(c) -> bool:
        cd = _cluster_date(c)
        if dom_date is None or cd is None:
            return True  # undated → can't rule out a real conflict
        return abs((cd - dom_date).days) <= CONTRADICTION_WINDOW_DAYS

    # A "public-source discrepancy" means independent PUBLIC sources disagree. A
    # rival cluster only counts if it carries a public source the dominant cluster
    # lacks — so a derived value vs a reported one, or one outlet disagreeing with
    # itself, is NOT a contradiction.
    dom_sources = _public_source_names(dominant)

    def _independent(c) -> bool:
        return bool(_public_source_names(c) - dom_sources)

    contradiction = metric not in SEQUENTIAL_METRICS and any(
        _cluster_weight(c) >= floor and _same_period(c) and _independent(c)
        for c in clusters[1:]
    )

    # Freshest supporting date drives as_of.
    pub_dates = [c.source.published_at for c, _ in dominant if c.source.published_at]
    resolved_as_of = max(pub_dates) if pub_dates else as_of

    delta = None
    if previous is not None and isinstance(previous.value, (int, float)):
        prev_val = float(previous.value)
        if prev_val != 0:
            delta = Delta(
                previous=prev_val,
                change_pct=round((value - prev_val) / abs(prev_val) * 100, 1),
                since=previous.as_of,
            )

    return ResolvedValue(
        metric=metric,
        value=round(value, 2),
        unit=unit,
        range=rng,
        as_of=resolved_as_of,
        estimate_type=estimate_type,
        confidence=round(confidence, 3),
        supporting_claims=[c.id for c, _ in dominant],
        contradiction=contradiction,
        delta=delta,
        history_ref=history_ref,
    )
