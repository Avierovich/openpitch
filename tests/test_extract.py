"""Tests for the extraction stage (FRD §7 stage 4) — using a MockLLM, no network."""

from __future__ import annotations

from datetime import date, datetime

from openpitch.models import Company
from openpitch.pipeline.extract import build_user_prompt, extract_claims
from openpitch.pipeline.llm import MockLLM
from openpitch.pipeline.sources.base import RawItem
from openpitch.models import SourceType
from openpitch.reconcile.engine import reconcile

METRICS = ["arr", "valuation", "headcount"]
ACME = Company(id="acme", name="Acme AI", last_updated="2026-06-13")
NOW = datetime(2026, 6, 13, 4, 0, 0)


def raw(stype: SourceType, name: str, published: date = date(2026, 6, 9)) -> RawItem:
    return RawItem(
        company_id="acme",
        source_type=stype,
        source_name=name,
        title="Interview",
        text="Founder talks growth.",
        url="https://x/y",
        published_at=published,
    ).finalize()


def mock(metric="arr", value=100_000_000, role="founder", qualifiers=None, extra=None):
    claims = [{
        "metric": metric, "value": value, "unit": "USD",
        "qualifiers": qualifiers or [], "speaker_role": role,
        "raw_text": "we crossed $100M ARR",
    }]
    if extra:
        claims.extend(extra)
    return MockLLM({"claims": claims})


# ── prompt ───────────────────────────────────────────────────────────────────


def test_prompt_includes_company_and_metrics():
    p = build_user_prompt(raw(SourceType.PODCAST, "20VC"), "Acme AI", METRICS)
    assert "Acme AI" in p
    assert "arr" in p and "headcount" in p


# ── extraction ───────────────────────────────────────────────────────────────


def test_extract_basic_claim_carries_provenance():
    claims = extract_claims(
        raw(SourceType.PODCAST, "20VC"), ACME, llm=mock(), metric_keys=METRICS, now=NOW
    )
    assert len(claims) == 1
    c = claims[0]
    assert c.metric == "arr"
    assert c.value == 100_000_000
    assert c.source.type is SourceType.PODCAST
    assert c.source.name == "20VC"
    assert c.speaker.role.value == "founder"
    assert c.extractor_model == "mock"
    assert c.base_confidence > 0
    assert c.id.startswith("clm_")


def test_extract_drops_unknown_metric():
    llm = mock(extra=[{"metric": "vibes", "value": 9, "raw_text": "great vibes"}])
    claims = extract_claims(raw(SourceType.NEWS, "TC"), ACME, llm=llm, metric_keys=METRICS, now=NOW)
    assert [c.metric for c in claims] == ["arr"]  # 'vibes' filtered out


def test_extract_confidence_reflects_source_quality():
    # Same value, but a founder-on-podcast claim should outrank an anonymous social post.
    pod = extract_claims(
        raw(SourceType.PODCAST, "20VC"), ACME,
        llm=mock(role="founder"), metric_keys=METRICS, now=NOW,
    )[0]
    soc = extract_claims(
        raw(SourceType.SOCIAL, "x"), ACME,
        llm=mock(role="unknown"), metric_keys=METRICS, now=NOW,
    )[0]
    assert pod.base_confidence > soc.base_confidence


def test_extract_handles_empty():
    claims = extract_claims(
        raw(SourceType.WEB, "site"), ACME, llm=MockLLM({"claims": []}),
        metric_keys=METRICS, now=NOW,
    )
    assert claims == []


# ── end-to-end: extract → reconcile ──────────────────────────────────────────


def test_extract_batch_tags_items_to_sources():
    from openpitch.pipeline.extract import extract_claims_batch
    items = [raw(SourceType.NEWS, "TC"), raw(SourceType.PODCAST, "20VC")]
    llm = MockLLM({"claims": [
        {"item_index": 0, "metric": "arr", "value": 50_000_000, "unit": "USD",
         "speaker_role": "journalist", "raw_text": "hit $50M ARR"},
        {"item_index": 1, "metric": "valuation", "value": 900_000_000, "unit": "USD",
         "speaker_role": "founder", "raw_text": "valued near $900M"},
        {"item_index": 9, "metric": "arr", "value": 1, "raw_text": "bad index"},  # dropped
    ]})
    claims = extract_claims_batch(items, ACME, llm=llm, metric_keys=METRICS, now=NOW)
    assert len(claims) == 2
    by_metric = {c.metric: c for c in claims}
    assert by_metric["arr"].source.name == "TC"          # item 0 -> news
    assert by_metric["valuation"].source.name == "20VC"  # item 1 -> podcast


def test_gemini_rotates_models_on_daily_quota():
    from openpitch.pipeline.llm import GeminiLLM

    class _Models:
        def generate_content(self, model, contents, config):
            if model == "gemini-2.5-flash":
                raise RuntimeError("429 RESOURCE_EXHAUSTED ... GenerateRequestsPerDayPerProjectPerModel-FreeTier")
            class R:
                text = '{"claims": []}'
            return R()

    class _Client:
        models = _Models()

    g = GeminiLLM.__new__(GeminiLLM)
    g.client = _Client()
    g.models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.5-flash-lite"]
    g._exhausted = set()
    assert g.complete_json("s", "u", {}) == {"claims": []}
    assert "gemini-2.5-flash" in g._exhausted   # exhausted model rotated out
    assert g.model == "gemini-2.0-flash"


def test_extract_then_reconcile_consensus():
    c1 = extract_claims(
        raw(SourceType.PODCAST, "20VC"), ACME,
        llm=mock(value=100_000_000), metric_keys=METRICS, now=NOW,
    )
    c2 = extract_claims(
        raw(SourceType.NEWS, "TheInformation"), ACME,
        llm=mock(value=105_000_000, role="journalist"), metric_keys=METRICS, now=NOW,
    )
    rv = reconcile(
        "arr", c1 + c2, as_of=date(2026, 6, 13), tau=120, tolerance=0.15, unit="USD"
    )
    assert rv is not None
    assert rv.estimate_type.value == "consensus"
    assert 100_000_000 <= rv.value <= 105_000_000
    assert rv.range is not None
