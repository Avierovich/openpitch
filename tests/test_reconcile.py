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
