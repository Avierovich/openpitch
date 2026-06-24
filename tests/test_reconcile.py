"""Tests for the confidence model + reconciliation engine (FRD §4–5)."""

from __future__ import annotations

from datetime import date, datetime

from openpitch.models import Claim, Source, SourceType, Speaker, SpeakerRole
from openpitch.reconcile.confidence import (
    base_confidence,
    corroborate,
    current_confidence,
)
from openpitch.reconcile.engine import reconcile
from openpitch.reconcile.reliability import update_reliability

RUN = date(2026, 6, 13)
ARR_TAU = 120
ARR_TOL = 0.15


def claim(
    cid: str,
    value: float,
    *,
    stype: SourceType,
    sname: str,
    role: SpeakerRole = SpeakerRole.UNKNOWN,
    published: date = RUN,
    qualifiers: list[str] | None = None,
) -> Claim:
    return Claim(
        id=cid,
        company_id="acme",
        metric="arr",
        value=value,
        raw_text="…",
        qualifiers=qualifiers or [],
        speaker=Speaker(role=role),
        source=Source(type=stype, name=sname, published_at=published),
        extracted_at=datetime(2026, 6, 13, 4, 0, 0),
        extractor_model="test",
        base_confidence=0.5,
    )


# ── confidence model ─────────────────────────────────────────────────────────


def test_filing_beats_social_prior():
    f = claim("f", 100, stype=SourceType.FILING, sname="EDGAR")
    s = claim("s", 100, stype=SourceType.SOCIAL, sname="x")
    assert base_confidence(f) > base_confidence(s)


def test_qualifiers_lower_confidence():
    plain = claim("a", 100, stype=SourceType.PODCAST, sname="20VC", role=SpeakerRole.FOUNDER)
    soft = claim(
        "b", 100, stype=SourceType.PODCAST, sname="20VC", role=SpeakerRole.FOUNDER,
        qualifiers=["run_rate", "rounded"],
    )
    assert base_confidence(soft) < base_confidence(plain)


def test_decay_reduces_confidence_with_age():
    fresh = claim("fr", 100, stype=SourceType.NEWS, sname="TC", published=RUN)
    old = claim("ol", 100, stype=SourceType.NEWS, sname="TC", published=date(2025, 6, 13))
    assert current_confidence(old, as_of=RUN, tau=ARR_TAU) < current_confidence(
        fresh, as_of=RUN, tau=ARR_TAU
    )


def test_corroboration_compounds():
    # Two independent 0.6 claims should exceed either alone.
    assert corroborate([0.6, 0.6]) > 0.6
    assert corroborate([0.6, 0.6]) <= 0.97


# ── reconciliation engine ────────────────────────────────────────────────────


def test_single_reported():
    rv = reconcile(
        "arr",
        [claim("a", 100, stype=SourceType.NEWS, sname="TC")],
        as_of=RUN, tau=ARR_TAU, tolerance=ARR_TOL, unit="USD",
    )
    assert rv is not None
    assert rv.estimate_type.value == "reported"
    assert abs(rv.value - 100) < 1e-6


def test_agreeing_sources_form_consensus():
    claims = [
        claim("a", 100, stype=SourceType.PODCAST, sname="20VC", role=SpeakerRole.FOUNDER),
        claim("b", 105, stype=SourceType.NEWS, sname="TheInformation"),
    ]
    rv = reconcile("arr", claims, as_of=RUN, tau=ARR_TAU, tolerance=ARR_TOL)
    assert rv.estimate_type.value == "consensus"
    assert 100 <= rv.value <= 105
    assert rv.range is not None


def test_contradiction_flagged():
    # Two podcast founders at ~100 (dominant) vs a filing+news cluster at ~60.
    claims = [
        claim("p1", 100, stype=SourceType.PODCAST, sname="20VC", role=SpeakerRole.FOUNDER),
        claim("p2", 102, stype=SourceType.PODCAST, sname="Lenny", role=SpeakerRole.FOUNDER),
        claim("f1", 60, stype=SourceType.FILING, sname="EDGAR"),
        claim("n1", 62, stype=SourceType.NEWS, sname="Bloomberg"),
    ]
    rv = reconcile("arr", claims, as_of=RUN, tau=ARR_TAU, tolerance=ARR_TOL)
    assert rv.contradiction is True
    assert rv.value > 95          # dominant (podcast) cluster wins on summed weight


def test_same_source_disagreement_is_not_a_contradiction():
    # One outlet reporting two values ($3B and $9B) is not a public-source discrepancy.
    claims = [
        claim("a", 9_000_000_000, stype=SourceType.NEWS, sname="TechCrunch"),
        claim("b", 9_000_000_000, stype=SourceType.NEWS, sname="Tech Funding News"),
        claim("c", 3_000_000_000, stype=SourceType.NEWS, sname="TechCrunch"),
    ]
    rv = reconcile("valuation", claims, as_of=RUN, tau=365, tolerance=0.15)
    assert rv.contradiction is False  # rival $3B is TechCrunch, already in the dominant cluster


def test_cross_source_disagreement_is_a_contradiction():
    claims = [
        claim("a", 9_000_000_000, stype=SourceType.NEWS, sname="TechCrunch"),
        claim("b", 9_000_000_000, stype=SourceType.NEWS, sname="Reuters"),
        claim("c", 3_000_000_000, stype=SourceType.NEWS, sname="Bloomberg"),
        claim("d", 3_000_000_000, stype=SourceType.NEWS, sname="WSJ"),
    ]
    rv = reconcile("valuation", claims, as_of=RUN, tau=365, tolerance=0.15)
    assert rv.contradiction is True  # Bloomberg/WSJ are independent of the dominant cluster


def test_temporal_gap_is_not_a_contradiction():
    # Far apart in value AND ~9 months apart -> trajectory (a raise), not a discrepancy.
    old = claim("o", 13_000_000_000, stype=SourceType.NEWS, sname="Tracxn", published=date(2025, 9, 9))
    new = claim("n", 23_000_000_000, stype=SourceType.NEWS, sname="TC", published=date(2026, 6, 12))
    rv = reconcile("valuation", [old, new], as_of=date(2026, 6, 14), tau=365, tolerance=0.20)
    assert rv.contradiction is False


def test_forward_looking_revenue_target_is_dropped():
    # "$1B ARR by the end of 2026" is a projection, not current revenue (the Replit trap).
    target = claim("t", 1_000_000_000, stype=SourceType.PODCAST, sname="20VC",
                   role=SpeakerRole.FOUNDER, qualifiers=["forward_looking"])
    assert reconcile("arr", [target], as_of=RUN, tau=ARR_TAU, tolerance=ARR_TOL) is None


def test_forward_looking_valuation_is_kept():
    # For valuation, forward_looking == "in talks" — recency is the edge, keep it.
    rumored = claim("r", 30_000_000_000, stype=SourceType.NEWS, sname="Bloomberg",
                    qualifiers=["forward_looking"])
    rv = reconcile("valuation", [rumored], as_of=RUN, tau=365, tolerance=0.15)
    assert rv is not None and abs(rv.value - 30_000_000_000) < 1


def test_unconfirmed_headline_surfaces_confirmed_anchor():
    # Real Fireworks shape: several fresh "in talks" reports dominate an older confirmed
    # round -> headline stays the fresh figure, confirmed surfaced as the anchor.
    rumored = [
        claim(f"u{i}", 15_000_000_000, stype=SourceType.NEWS, sname=f"Outlet{i}",
              qualifiers=["unconfirmed"], published=date(2026, 5, 26))
        for i in range(3)
    ]
    confirmed = claim("c", 4_000_000_000, stype=SourceType.NEWS, sname="WSJ",
                      published=date(2026, 1, 8))
    rv = reconcile("valuation", rumored + [confirmed], as_of=date(2026, 6, 1), tau=365, tolerance=0.15)
    assert rv.unconfirmed is True
    assert abs(rv.value - 15_000_000_000) < 1            # headline stays the fresh figure
    assert rv.confirmed_value == 4_000_000_000           # confirmed anchor surfaced
    assert rv.confirmed_as_of == date(2026, 1, 8)


def test_confidence_never_certain():
    claims = [claim(f"c{i}", 100, stype=SourceType.FILING, sname=f"src{i}") for i in range(10)]
    rv = reconcile("arr", claims, as_of=RUN, tau=ARR_TAU, tolerance=ARR_TOL)
    assert rv.confidence <= 0.97


def test_no_numeric_claims_returns_none():
    c = claim("a", 100, stype=SourceType.NEWS, sname="TC")
    c.value = "a lot"
    assert reconcile("arr", [c], as_of=RUN, tau=ARR_TAU, tolerance=ARR_TOL) is None


# ── reliability ──────────────────────────────────────────────────────────────


def test_reliability_moves_with_evidence():
    assert update_reliability(0, 0) == 0.5
    assert update_reliability(9, 0) > 0.7
    assert update_reliability(0, 9) < 0.3
