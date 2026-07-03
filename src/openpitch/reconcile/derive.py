"""Derivation & validation engine (FRD §5.6) — reason about the numbers.

Two jobs:
  1. DERIVE — compute metrics from others via hard financial identities
     (MRR→ARR, round÷equity→valuation, subscribers×ACV→ARR, valuation÷ARR→multiple).
     Each output is a DERIVED Claim with a full derivation trail and a confidence
     PROPAGATED from its inputs — it then flows into the reconciliation engine
     alongside reported claims, so reported-vs-derived disagreements get flagged
     as contradictions automatically.
  2. VALIDATE — hiring/headcount surge detection and revenue↔hiring concordance,
     used to corroborate or question reported growth.

Pure logic: deterministic, no LLM, no network. The soft benchmark estimates
(headcount × revenue-per-employee) are segment-aware and clearly low-confidence;
they are NOT wired into v1 derive_claims (Decision 3, FRD §13) — available but gated.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime

from ..models import Claim, Derivation, Source, SourceType, Speaker, SpeakerRole

IDENTITY_RELIABILITY = 0.92   # exact math, but allow slack for timing/rounding of inputs
MAX_BASE = 0.97


def _is_num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _best_by_metric(claims: list[Claim]) -> dict[str, Claim]:
    best: dict[str, Claim] = {}
    for c in claims:
        cur = best.get(c.metric)
        if cur is None or c.base_confidence > cur.base_confidence:
            best[c.metric] = c
    return best


def _derived(
    metric: str, value: float, unit: str, formula: str, inputs: list[Claim],
    confidence: float, *, now: datetime, as_of: date | None,
) -> Claim:
    pubs = [c.source.published_at for c in inputs if c.source.published_at]
    pub = max(pubs) if pubs else as_of
    ids = [c.id for c in inputs]
    cid = "drv_" + hashlib.sha256(f"{metric}|{formula}|{ids}".encode()).hexdigest()[:10]
    # Propagate not-yet-closed qualifiers: a value derived from a rumored/in-talks
    # input is itself unconfirmed — the derivation must not launder that away.
    quals = sorted({q for c in inputs for q in (c.qualifiers or [])}
                   & {"unconfirmed", "rumored", "in_talks"})
    return Claim(
        id=cid,
        company_id=inputs[0].company_id,
        metric=metric,
        value=round(value, 2),
        unit=unit,
        raw_text=formula,
        qualifiers=quals,
        speaker=Speaker(role=SpeakerRole.UNKNOWN),
        source=Source(type=SourceType.DERIVED, name=f"derived:{metric}", published_at=pub),
        extracted_at=now,
        extractor_model="derive-engine",
        base_confidence=round(min(confidence, MAX_BASE), 4),
        derivation=Derivation(kind="identity", formula=formula, inputs=ids),
    )


def derive_claims(
    claims: list[Claim], *, now: datetime | None = None, as_of: date | None = None
) -> list[Claim]:
    """Apply hard financial identities to produce derived claims (v1-safe)."""
    now = now or datetime.now()
    # Never derive from projections: "targeting $10M MRR by 2027" must not become an
    # untagged current-ARR claim (the Replit trap via the derivation side door).
    claims = [c for c in claims if "forward_looking" not in (c.qualifiers or [])]
    b = _best_by_metric(claims)
    out: list[Claim] = []

    # ARR = MRR × 12
    if "mrr" in b and _is_num(b["mrr"].value):
        m = b["mrr"]
        out.append(_derived(
            "arr", float(m.value) * 12, "USD", "ARR = MRR × 12", [m],
            m.base_confidence * IDENTITY_RELIABILITY, now=now, as_of=as_of))

    # revenue_multiple = valuation ÷ ARR
    if "valuation" in b and "arr" in b and _is_num(b["valuation"].value) and _is_num(b["arr"].value):
        v, a = b["valuation"], b["arr"]
        if float(a.value) != 0:
            out.append(_derived(
                "revenue_multiple", float(v.value) / float(a.value), "x",
                "revenue_multiple = valuation ÷ ARR", [v, a],
                v.base_confidence * a.base_confidence * IDENTITY_RELIABILITY, now=now, as_of=as_of))

    # ARR = subscribers × ACV
    if "subscribers" in b and "acv" in b and _is_num(b["subscribers"].value) and _is_num(b["acv"].value):
        s, c = b["subscribers"], b["acv"]
        out.append(_derived(
            "arr", float(s.value) * float(c.value), "USD", "ARR = subscribers × ACV", [s, c],
            s.base_confidence * c.base_confidence * IDENTITY_RELIABILITY, now=now, as_of=as_of))

    # post-money valuation = round_amount ÷ (equity_sold_pct / 100)
    if "round_amount" in b and "equity_sold_pct" in b and _is_num(b["round_amount"].value) and _is_num(b["equity_sold_pct"].value):
        r, e = b["round_amount"], b["equity_sold_pct"]
        if float(e.value) > 0:
            out.append(_derived(
                "valuation", float(r.value) / (float(e.value) / 100.0), "USD",
                "post-money = round ÷ equity%", [r, e],
                r.base_confidence * e.base_confidence * IDENTITY_RELIABILITY, now=now, as_of=as_of))

    return out


# ── validation: hiring surge + revenue↔hiring concordance ────────────────────


@dataclass
class Surge:
    pct_change: float
    from_value: float
    to_value: float
    window_days: int


def detect_surge(
    series: list[tuple[date, float]], *, window_days: int = 90, threshold_pct: float = 25.0
) -> Surge | None:
    """Detect a headcount/open-roles surge from a tracked time series (FRD §5.6).

    Compares the latest value to the earliest point within `window_days`.
    """
    pts = [p for p in series if _is_num(p[1])]
    if len(pts) < 2:
        return None
    pts.sort(key=lambda p: p[0])
    latest_date, latest = pts[-1]
    ref = next(((d, v) for d, v in pts if (latest_date - d).days <= window_days), pts[0])
    rd, rv = ref
    if rv <= 0:
        return None
    pct = (latest - rv) / rv * 100
    if pct >= threshold_pct:
        return Surge(round(pct, 1), rv, latest, (latest_date - rd).days)
    return None


def concordance(
    revenue_growth_pct: float | None, headcount_growth_pct: float | None, *, tolerance: float = 15.0
) -> str:
    """Do a revenue-growth claim and observed hiring agree? (FRD §5.6)

    Returns 'corroborates' | 'contradicts' | 'neutral'.
    """
    if revenue_growth_pct is None or headcount_growth_pct is None:
        return "neutral"
    if revenue_growth_pct >= tolerance and headcount_growth_pct >= tolerance:
        return "corroborates"
    if revenue_growth_pct >= tolerance and headcount_growth_pct < tolerance / 3:
        return "contradicts"
    return "neutral"


def growth_direction(headcount_growth_pct: float | None) -> str:
    """Safe v1 qualitative implied-growth signal (no fabricated dollar figure)."""
    if headcount_growth_pct is None:
        return "unknown"
    if headcount_growth_pct >= 40:
        return "strong growth"
    if headcount_growth_pct >= 10:
        return "growing"
    if headcount_growth_pct <= -10:
        return "contracting"
    return "flat"


# ── soft benchmark (v2, gated, segment-aware) ────────────────────────────────

# Revenue-per-employee bands (USD) by category — WIDE and illustrative.
# Foundation-model labs are research-heavy/pre-revenue, so headcount is a WEAK
# ARR proxy there (low band + low reliability). See STRATEGY-DEEP-DIVE / the
# headcount caveat. Not wired into v1 derive_claims.
SEGMENT_RPE: dict[str, tuple[int, int]] = {
    "foundation-model": (50_000, 250_000),
    "ai-infra": (200_000, 600_000),
    "coding-agent": (150_000, 450_000),
    "vertical-app": (150_000, 400_000),
    "enterprise-ai": (150_000, 400_000),
    "ai-agents": (120_000, 350_000),
    "generative-media": (120_000, 350_000),
    "data-eval": (120_000, 300_000),
}
_HEADCOUNT_ARR_RELIABILITY = {"foundation-model": 0.20}


def headcount_implied_arr(headcount: float, category: str | None) -> tuple[float, float, float]:
    """SOFT (v2): returns (low, high, reliability) implied-ARR band. Segment-aware."""
    lo, hi = SEGMENT_RPE.get(category or "", (100_000, 400_000))
    reliability = _HEADCOUNT_ARR_RELIABILITY.get(category or "", 0.40)
    return (headcount * lo, headcount * hi, reliability)
