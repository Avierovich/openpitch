"""Tests for the derivation & validation engine (FRD §5.6)."""

from __future__ import annotations

from datetime import date, datetime

from openpitch.models import Claim, Source, SourceType, Speaker, SpeakerRole
from openpitch.reconcile.derive import (
    concordance,
    derive_claims,
    detect_surge,
    growth_direction,
    headcount_implied_arr,
)
from openpitch.reconcile.engine import reconcile

RUN = date(2026, 6, 13)
NOW = datetime(2026, 6, 13, 4, 0, 0)


def claim(cid, metric, value, *, stype=SourceType.PODCAST, sname="20VC",
          role=SpeakerRole.FOUNDER, base=0.6, published=RUN, qualifiers=()) -> Claim:
    return Claim(
        id=cid, company_id="acme", metric=metric, value=value, raw_text="…",
        qualifiers=list(qualifiers), speaker=Speaker(role=role),
        source=Source(type=stype, name=sname, published_at=published),
        extracted_at=NOW, extractor_model="test", base_confidence=base,
    )


# ── hard identities ──────────────────────────────────────────────────────────


def test_no_derivation_from_forward_looking_inputs():
    # "targeting $10M MRR by 2027" must not become an untagged current-ARR claim.
    derived = derive_claims([claim("m", "mrr", 10_000_000, qualifiers=["forward_looking"])],
                            now=NOW, as_of=RUN)
    assert derived == []


def test_derivation_propagates_unconfirmed():
    # revenue_multiple derived from a rumored valuation must stay tagged unconfirmed.
    derived = derive_claims([
        claim("v", "valuation", 1_000_000_000, qualifiers=["unconfirmed"]),
        claim("a", "arr", 50_000_000),
    ], now=NOW, as_of=RUN)
    mult = [c for c in derived if c.metric == "revenue_multiple"]
    assert len(mult) == 1 and "unconfirmed" in mult[0].qualifiers


def test_arr_from_mrr():
    derived = derive_claims([claim("m", "mrr", 10_000_000, base=0.6)], now=NOW, as_of=RUN)
    arr = [c for c in derived if c.metric == "arr"]
    assert len(arr) == 1
    assert arr[0].value == 120_000_000
    assert arr[0].source.type is SourceType.DERIVED
    assert arr[0].derivation.formula == "ARR = MRR × 12"
    assert arr[0].derivation.inputs == ["m"]
    # confidence propagated from input × identity reliability
    assert 0.5 < arr[0].base_confidence < 0.6


def test_revenue_multiple_from_valuation_and_arr():
    claims = [claim("v", "valuation", 1_000_000_000), claim("a", "arr", 50_000_000)]
    derived = derive_claims(claims, now=NOW, as_of=RUN)
    mult = [c for c in derived if c.metric == "revenue_multiple"]
    assert mult and mult[0].value == 20.0


def test_arr_from_subscribers_acv():
    claims = [claim("s", "subscribers", 1000), claim("c", "acv", 50_000)]
    derived = derive_claims(claims, now=NOW, as_of=RUN)
    arr = [c for c in derived if c.metric == "arr"]
    assert arr and arr[0].value == 50_000_000


def test_valuation_from_round_and_equity():
    claims = [claim("r", "round_amount", 50_000_000), claim("e", "equity_sold_pct", 10)]
    derived = derive_claims(claims, now=NOW, as_of=RUN)
    val = [c for c in derived if c.metric == "valuation"]
    assert val and val[0].value == 500_000_000  # $50M for 10% -> $500M post


def test_no_inputs_no_derivation():
    assert derive_claims([claim("a", "arr", 100)], now=NOW, as_of=RUN) == []


# ── the headline: derived value triangulates a reported one ──────────────────


def test_derived_value_is_not_a_public_source_contradiction():
    # Reported ARR ~$60M (two news sources) vs MRR $10M -> derived ARR $120M.
    # A derived value disagreeing with reported sources is NOT a public-source
    # discrepancy — only one set of public sources is involved, so it must not flag.
    reported = [
        claim("n1", "arr", 60_000_000, stype=SourceType.NEWS, sname="TC", role=SpeakerRole.JOURNALIST),
        claim("n2", "arr", 61_000_000, stype=SourceType.NEWS, sname="Bloomberg", role=SpeakerRole.JOURNALIST),
    ]
    derived = derive_claims([claim("m", "mrr", 10_000_000, base=0.6)], now=NOW, as_of=RUN)
    rv = reconcile("arr", reported + derived, as_of=RUN, tau=120, tolerance=0.15, unit="USD")
    assert rv is not None
    assert rv.contradiction is False         # derived-vs-reported is not a public-source discrepancy
    assert rv.value < 80_000_000             # reported cluster (stronger) wins


# ── validation: surge + concordance ──────────────────────────────────────────


def test_detect_surge():
    s = detect_surge([(date(2026, 4, 1), 100), (date(2026, 6, 1), 160)], threshold_pct=25)
    assert s is not None and s.pct_change == 60.0


def test_no_surge_below_threshold():
    assert detect_surge([(date(2026, 4, 1), 100), (date(2026, 6, 1), 108)], threshold_pct=25) is None


def test_concordance():
    assert concordance(60, 50) == "corroborates"
    assert concordance(60, 2) == "contradicts"      # revenue up, hiring flat -> suspicious
    assert concordance(5, 50) == "neutral"


def test_growth_direction():
    assert growth_direction(50) == "strong growth"
    assert growth_direction(20) == "growing"
    assert growth_direction(-20) == "contracting"
    assert growth_direction(0) == "flat"


# ── soft benchmark is segment-aware (the foundation-model caveat) ────────────


def test_headcount_implied_arr_segment_aware():
    _, fm_high, fm_rel = headcount_implied_arr(100, "foundation-model")
    _, app_high, app_rel = headcount_implied_arr(100, "vertical-app")
    assert fm_rel < app_rel               # labs: weaker ARR proxy
    assert fm_high < headcount_implied_arr(100, "ai-infra")[1]
