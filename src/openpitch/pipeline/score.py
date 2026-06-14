"""VC-attention scoring & universe selection (FRD §6).

Ranks candidates by a composite of observable signals (valuation primary,
funding next) — deliberately NOT ARR. With no data yet, falls back to watchlist
order so the pipeline is always runnable. Tracks entries/exits vs the prior universe.
"""

from __future__ import annotations

import math

from ..config import load_scoring
from ..models import Company


def _signal(company: Company) -> float:
    """Observable VC-attention proxy from whatever resolved data exists."""
    m = company.metrics
    for key in ("valuation", "total_funding", "round_amount"):
        rv = m.get(key)
        if rv and isinstance(rv.value, (int, float)) and rv.value > 0:
            return math.log10(float(rv.value))
    return 0.0


def select_universe(
    companies: list[Company], *, size: int | None = None, prev_ids: list[str] | None = None
) -> dict:
    """Score, rank, and tag companies; return a universe summary with churn."""
    cfg = load_scoring()
    size = size or int(cfg.get("universe_size", 50))

    scored = sorted(companies, key=_signal, reverse=True)
    raw = [_signal(c) for c in scored]
    hi = max(raw) if raw else 0.0
    for rank, c in enumerate(scored, start=1):
        c.vc_attention_score = round((_signal(c) / hi * 100) if hi else 0.0, 1)
        c.universe_rank = rank
        c.in_universe = rank <= size

    selected = [c.id for c in scored if c.in_universe]
    prev = set(prev_ids or [])
    return {
        "size": size,
        "ranked": [{"id": c.id, "rank": c.universe_rank, "score": c.vc_attention_score} for c in scored],
        "selected": selected,
        "entries": [cid for cid in selected if cid not in prev] if prev else [],
        "exits": [cid for cid in prev if cid not in selected] if prev else [],
    }
