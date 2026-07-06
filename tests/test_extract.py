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


def test_extract_drops_gmv_mislabeled_as_arr():
    # The Foodics trap: a GMV figure tagged arr, in a phrase that also says "revenue growth".
    llm = MockLLM({"claims": [
        {"metric": "arr", "value": 6_000_000_000, "raw_text": "reports $6 billion GMV and 29% revenue growth"},
        {"metric": "arr", "value": 20_800_000, "raw_text": "Foodics 2024: $20.8M ARR"},
    ]})
    claims = extract_claims(raw(SourceType.NEWS, "MENAbytes"), ACME, llm=llm, metric_keys=METRICS, now=NOW)
    vals = sorted(c.value for c in claims)
    assert vals == [20_800_000]  # GMV claim dropped, genuine ARR kept


def test_volume_mislabel_guard_unit():
    from openpitch.pipeline.extract.extract import is_volume_mislabel
    assert is_volume_mislabel("arr", "$6 billion GMV and 29% revenue growth")
    assert is_volume_mislabel("mrr", "processed $2B in total payment volume")
    assert not is_volume_mislabel("arr", "hit $200M ARR run rate")      # recurring rescues
    assert not is_volume_mislabel("arr", "$50M revenue of recurring SaaS")
    assert not is_volume_mislabel("valuation", "$6 billion GMV")        # non-revenue metric untouched


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


# ── batch prompt: company context + per-item budget (gap-fill support) ───────


def test_batch_prompt_includes_company_context():
    from openpitch.pipeline.extract import build_batch_prompt
    sierra = Company(id="sierra", name="Sierra", website="sierra.ai",
                     category="ai-agents", summary="AI agents for customer service.",
                     last_updated="2026-07-03")
    prompt = build_batch_prompt([raw(SourceType.NEWS, "TechCrunch")], sierra, METRICS)
    assert "website sierra.ai" in prompt and "ai-agents" in prompt
    assert "share the name" in prompt
    # no context fields -> no context block
    bare = build_batch_prompt([raw(SourceType.NEWS, "TechCrunch")], ACME, METRICS)
    assert "share the name" not in bare


def test_batch_per_item_chars_passthrough():
    from openpitch.pipeline.extract import extract_claims_batch
    long_item = raw(SourceType.NEWS, "TechCrunch")
    long_item.text = ("filler " * 400) + "valued at $15.8 billion"  # ~2800 chars, tail matters
    seen = {}

    def capture(user):
        seen["prompt"] = user
        return {"claims": []}

    extract_claims_batch([long_item], ACME, llm=MockLLM(capture), metric_keys=METRICS,
                         now=NOW, per_item_chars=6000)
    assert "valued at $15.8 billion" in seen["prompt"]
    extract_claims_batch([long_item], ACME, llm=MockLLM(capture), metric_keys=METRICS, now=NOW)
    assert "valued at $15.8 billion" not in seen["prompt"]  # default 1500 truncates
