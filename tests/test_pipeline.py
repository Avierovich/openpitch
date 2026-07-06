"""End-to-end tests for storage, publish, scoring, and MCP tools (tmp data dir)."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from openpitch import store
from openpitch.mcp_server import tools
from openpitch.models import (
    Claim, Company, EstimateType, ResolvedValue, Source, SourceType, Speaker, SpeakerRole,
)
from openpitch.pipeline.publish import publish_company
from openpitch.pipeline.run import _reconcile_company
from openpitch.reconcile.confidence import base_confidence

NOW = datetime(2026, 6, 14, 5, 0, 0)
AS_OF = date(2026, 6, 14)


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENPITCH_DATA_DIR", str(tmp_path))
    return tmp_path


def _claim(metric, value, *, stype, sname, role=SpeakerRole.JOURNALIST, published=AS_OF):
    c = Claim(
        id=f"{metric}-{sname}-{int(value)}", company_id="acme", metric=metric, value=value,
        raw_text=f"{metric} is {value}", speaker=Speaker(role=role),
        source=Source(type=stype, name=sname, published_at=published),
        extracted_at=NOW, extractor_model="t", base_confidence=0.0,
    )
    c.base_confidence = round(base_confidence(c), 4)
    return c


def test_store_roundtrip(data_dir):
    c = Company(id="acme", name="Acme", last_updated=AS_OF, metrics={
        "arr": ResolvedValue(metric="arr", value=100, as_of=AS_OF,
                             estimate_type=EstimateType.REPORTED, confidence=0.5)})
    store.write_company(c)
    got = store.read_company("acme")
    assert got and got.metrics["arr"].value == 100
    assert store.list_company_ids() == ["acme"]


def test_pipeline_contradiction_and_mcp(data_dir):
    meta = {"id": "acme", "name": "Acme", "category": "foundation-model", "segment": "global"}
    claims = [
        _claim("arr", 60_000_000, stype=SourceType.NEWS, sname="TC"),
        _claim("arr", 61_000_000, stype=SourceType.NEWS, sname="BB"),
        _claim("arr", 120_000_000, stype=SourceType.NEWS, sname="Reuters"),
        _claim("mrr", 10_000_000, stype=SourceType.PODCAST, sname="20VC", role=SpeakerRole.FOUNDER),
        _claim("valuation", 1_000_000_000, stype=SourceType.NEWS, sname="TC"),
    ]
    company, all_claims = _reconcile_company(meta, claims, now=NOW, as_of=AS_OF)
    events = publish_company(company, all_claims, now=NOW)

    # Independent Reuters $120M (+ MRR-derived $120M) contradicts the dominant ~60M
    # cluster (TC/BB) -> flagged. A cross-source disagreement, not derived-only.
    assert company.metrics["arr"].contradiction is True
    assert any(e.type.value == "contradiction_flagged" for e in events)
    # Identity-derived revenue_multiple present.
    assert "revenue_multiple" in company.metrics

    # MCP tools over the committed data.
    gm = tools.get_metric("acme", "arr")
    assert gm["status"] == "ok" and gm["metric"]["contradiction"] is True and gm["sources"]
    prov = tools.get_provenance("acme", "arr")
    assert prov["claims"] and all("current_confidence" in c for c in prov["claims"])
    assert tools.get_metric("acme", "vibes")["status"] == "invalid_metric"
    assert tools.get_metric("zzz", "arr")["status"] == "not_found"
    assert tools.list_companies()["companies"][0]["id"] == "acme"
    assert tools.get_events()["events"]


def test_no_data_responses(data_dir):
    assert tools.get_company("ghost")["status"] == "not_found"
    assert tools.search("nothing")["results"] == []


def test_list_companies_falls_back_to_index(data_dir):
    # Remote-style consumer: only the manifest exists, no companies/ dir to glob.
    store.write_index(["alpha", "beta"])
    assert store.list_company_ids() == ["alpha", "beta"]


def test_finalize_ranks_globally_across_incremental_runs(data_dir):
    from openpitch.pipeline.run import _finalize, _reconcile_company

    def claim_for(cid, val):
        c = Claim(id=f"{cid}-val", company_id=cid, metric="valuation", value=val, raw_text="x",
                  speaker=Speaker(role=SpeakerRole.JOURNALIST),
                  source=Source(type=SourceType.NEWS, name="N", published_at=AS_OF),
                  extracted_at=NOW, extractor_model="t", base_confidence=0.0)
        c.base_confidence = round(base_confidence(c), 4)
        return c

    def mk(cid, val):
        return _reconcile_company({"id": cid, "name": cid, "category": "x", "segment": "global"},
                                  [claim_for(cid, val)], now=NOW, as_of=AS_OF)

    _finalize([mk("alpha", 100_000_000_000)], now=NOW, as_of=AS_OF)
    _finalize([mk("beta", 200_000_000_000)], now=NOW, as_of=AS_OF)  # separate, incremental run

    ranks = sorted(c.universe_rank for c in store.read_all_companies())
    assert ranks == [1, 2]                          # global + unique despite two runs
    assert store.read_company("beta").universe_rank == 1  # higher valuation ranks first


def test_dashboard_renders_top_50_watchlist_slots(data_dir, monkeypatch):
    c = Company(
        id="openai", name="OpenAI", category="foundation-model", universe_rank=1,
        last_updated=AS_OF, metrics={
            "arr": ResolvedValue(
                metric="arr", value=100, as_of=AS_OF,
                estimate_type=EstimateType.REPORTED, confidence=0.5,
            )
        },
    )
    store.write_company(c)

    from openpitch.pipeline import dashboard

    # Redirect output to a tmp dir — must NOT clobber the real dashboard/dist with
    # this test's single-company data (that was the "1 sourced profile" bug).
    dist = data_dir / "dist"
    monkeypatch.setattr(dashboard, "DIST", dist)
    dashboard.build()
    index = (dist / "index.html").read_text()
    assert "1 companies profiled · top 50 ranked below" in index
    assert index.count('class="card') == 50
    assert "ARR / revenue" in index
    assert "pending sourced metrics" in index
    assert '<option value="valuation" selected>Valuation</option>' in index
    assert 'data-sort' in index
    assert 'data-valuation="0.0"' in index
    assert "View data quality" in index
    assert (dist / "quality.html").exists()
    assert (data_dir / "quality" / "report.md").exists()


def test_quality_report_flags_top50_gaps(data_dir):
    c = Company(id="acme", name="Acme", category="foundation-model", last_updated=AS_OF)
    store.write_company(c)

    from openpitch.pipeline.quality import build_snapshot, render_markdown, write_report

    snapshot = build_snapshot()
    assert "Acme" in snapshot.top50_no_metrics
    assert snapshot.critical_count >= 1

    write_report()
    report = (data_dir / "quality" / "report.md").read_text()
    assert "# OpenPitch Data Quality Report" in report
    assert "Acme" in report
    assert "Top-50 Missing Valuation" in render_markdown(snapshot)


def test_quality_warnings_are_honest(data_dir):
    from openpitch.pipeline.quality import build_snapshot, _under_corroborated

    def val(v):
        return ResolvedValue(metric="valuation", value=v, as_of=AS_OF,
                             estimate_type=EstimateType.REPORTED, confidence=0.5)

    lab = Company(id="lab", name="Lab", category="foundation-model", universe_rank=1,
                  in_universe=True, last_updated=AS_OF, metrics={"valuation": val(9e9)})
    app = Company(id="app", name="App", category="vertical-app", universe_rank=2,
                  in_universe=True, last_updated=AS_OF, metrics={"valuation": val(8e9)})
    store.write_company(lab)
    store.write_company(app)

    s = build_snapshot()
    assert "Lab" not in s.top50_missing_arr   # frontier lab: missing ARR is reality, not a gap
    assert "App" in s.top50_missing_arr       # app layer: ARR expected -> a real warning

    # a single FILING is authoritative; a single low-trust news source is not
    store.write_claims("lab", [_claim("valuation", 9e9, stype=SourceType.FILING, sname="EDGAR")])
    store.write_claims("app", [_claim("valuation", 8e9, stype=SourceType.NEWS, sname="SiliconANGLE")])
    assert _under_corroborated("lab", "valuation") is False
    assert _under_corroborated("app", "valuation") is True

    # a single TIER-1 outlet (Bloomberg) is credible on its own -> not a warning
    store.write_claims("app", [_claim("valuation", 8e9, stype=SourceType.NEWS, sname="Bloomberg")])
    assert _under_corroborated("app", "valuation") is False


def test_apply_taxonomy_overlays_by_id(tmp_path, monkeypatch):
    import yaml
    from openpitch import config
    monkeypatch.setenv("OPENPITCH_CONFIG_DIR", str(tmp_path))
    (tmp_path / "taxonomy.yaml").write_text(yaml.safe_dump({
        "vocab": {"generative-media": ["voice", "video"]},
        "companies": {"acme": {"category": "generative-media", "subcategory": "voice",
                               "specialty": "voice cloning"}},
    }))
    config.load_taxonomy.cache_clear()
    out = config.apply_taxonomy({"id": "acme", "name": "Acme", "category": "ai", "domain": "acme.ai"})
    assert out["category"] == "generative-media"      # classified main wins
    assert out["subcategory"] == "voice" and out["specialty"] == "voice cloning"
    # unknown id -> unchanged
    assert config.apply_taxonomy({"id": "ghost", "category": "x"}) == {"id": "ghost", "category": "x"}
    config.load_taxonomy.cache_clear()


# ── gap-fill: targeted valuation hunt (the Sierra fix) ───────────────────────


def _gap_fill_setup(monkeypatch, bodies_return):
    """Monkeypatch the article source; return (meta, stub, funding_claims)."""
    from openpitch.pipeline.sources import article, base
    from openpitch.models import SourceType as ST

    cand = base.RawItem(
        company_id="sierra", source_type=ST.NEWS, source_name="TechCrunch",
        title="Sierra hits $15.8B valuation", url="https://tc.com/a",
        content_hash="cafe0123deadbeef",
    )
    monkeypatch.setattr(article, "fetch_candidates", lambda company, **kw: [cand])
    monkeypatch.setattr(article, "fetch_bodies",
                        lambda items, **kw: bodies_return(items))
    meta = {"id": "sierra", "name": "Sierra", "domain": "sierra.ai"}
    stub = Company(id="sierra", name="Sierra", website="sierra.ai", last_updated=AS_OF)
    funding = [_claim("total_funding", 950e6, stype=SourceType.NEWS, sname="CNBC")]
    return meta, stub, funding, cand


def test_gap_fill_adds_valuation_and_records_cache(data_dir, monkeypatch):
    from openpitch.pipeline.llm import MockLLM
    from openpitch.pipeline.run import _gap_fill

    def bodies(items):
        for it in items:
            it.text = f"{it.title}. The round values Sierra at $15.8 billion post-money."
        return items

    meta, stub, funding, cand = _gap_fill_setup(monkeypatch, bodies)
    llm = MockLLM({"claims": [{"item_index": 0, "metric": "valuation", "value": 15.8e9,
                               "raw_text": "values Sierra at $15.8 billion"}]})
    cache = {}
    extra = _gap_fill(meta, stub, funding, metric="valuation", llm=llm,
                      keys=["valuation", "total_funding"], cache=cache, now=NOW)
    assert len(extra) == 1 and extra[0].metric == "valuation" and extra[0].value == 15.8e9
    assert f"sierra:{cand.content_hash}" in cache  # recorded for future runs


def test_gap_fill_reuses_cache_without_fetch(data_dir, monkeypatch):
    from openpitch.pipeline.llm import MockLLM
    from openpitch.pipeline.run import _gap_fill

    fetched = []

    def bodies(items):
        fetched.extend(items)
        return []

    meta, stub, funding, cand = _gap_fill_setup(monkeypatch, bodies)
    cached_claim = _claim("valuation", 15.8e9, stype=SourceType.NEWS, sname="TechCrunch")
    cached_claim.source.url = "https://tc.com/a"
    cache = {f"sierra:{cand.content_hash}": [cached_claim.model_dump(mode="json")]}
    extra = _gap_fill(meta, stub, funding, metric="valuation",
                      llm=MockLLM({"claims": []}),
                      keys=["valuation"], cache=cache, now=NOW)
    assert fetched == []                      # cache hit -> no article fetch
    assert len(extra) == 1 and extra[0].value == 15.8e9


def test_quality_flags_funded_but_no_valuation(data_dir):
    from openpitch.pipeline import quality

    def co(cid, **metrics):
        rvs = {m: ResolvedValue(metric=m, value=v, as_of=AS_OF,
                                estimate_type=EstimateType.REPORTED, confidence=0.5)
               for m, v in metrics.items()}
        store.write_company(Company(id=cid, name=cid.title(), last_updated=AS_OF, metrics=rvs))

    co("sierra", total_funding=950e6)                       # must flag (the failure)
    co("tiny", total_funding=50e6)                          # below floor -> silent
    co("healthy", total_funding=950e6, valuation=15.8e9)    # has valuation -> silent
    snap = quality.build_snapshot()
    assert "Sierra" in snap.funded_no_valuation
    assert "Tiny" not in snap.funded_no_valuation
    assert "Healthy" not in snap.funded_no_valuation
    assert snap.critical_count >= 1


def test_valuation_below_round_amount_is_dropped(data_dir):
    # Post-money >= round by definition: a lone junk "$5.6M valuation" claim must not
    # survive next to a $250M round (the GetLatka/Augment case).
    claims = [
        _claim("round_amount", 250e6, stype=SourceType.NEWS, sname="TechCrunch"),
        _claim("valuation", 5.6e6, stype=SourceType.WEB, sname="GetLatka"),
    ]
    company, _ = _reconcile_company({"id": "acme", "name": "Acme"}, claims, now=NOW, as_of=AS_OF)
    assert "valuation" not in company.metrics
    # a plausible valuation alongside the junk one survives (junk dropped, real kept)
    claims.append(_claim("valuation", 1e9, stype=SourceType.NEWS, sname="Reuters"))
    company, _ = _reconcile_company({"id": "acme", "name": "Acme"}, claims, now=NOW, as_of=AS_OF)
    assert company.metrics["valuation"].value == 1e9


def test_valuation_junk_dropped_against_total_funding_floor(data_dir):
    # No round_amount claim, but $252M total raised: a "$5.6M valuation" scrape is
    # junk (2% of capital raised); a genuine down-round at 60% of raised survives.
    claims = [
        _claim("total_funding", 252e6, stype=SourceType.WEB, sname="GetLatka"),
        _claim("valuation", 5.6e6, stype=SourceType.WEB, sname="GetLatka"),
    ]
    company, _ = _reconcile_company({"id": "acme", "name": "Acme"}, claims, now=NOW, as_of=AS_OF)
    assert "valuation" not in company.metrics
    claims[1] = _claim("valuation", 150e6, stype=SourceType.NEWS, sname="Reuters")
    company, _ = _reconcile_company({"id": "acme", "name": "Acme"}, claims, now=NOW, as_of=AS_OF)
    assert company.metrics["valuation"].value == 150e6


def test_quality_discovery_backlog_is_not_critical(data_dir, monkeypatch):
    # An auto-discovered candidate awaiting its first run is funnel state, not a
    # defect; only unprofiled CURATED high-priority companies are critical.
    from openpitch.pipeline import quality
    watchlist = [
        {"id": "curated-gap", "name": "Curated Gap", "category": "ai-infra"},
        {"id": "fresh-find", "name": "Fresh Find", "category": "ai-infra", "discovered": True},
    ]
    monkeypatch.setattr(quality, "load_watchlist", lambda: watchlist)
    snap = quality.build_snapshot()
    assert snap.unprofiled_high_priority == ["Curated Gap"]
    assert snap.discovery_backlog == 1
