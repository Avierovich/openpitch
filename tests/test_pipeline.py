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
        _claim("mrr", 10_000_000, stype=SourceType.PODCAST, sname="20VC", role=SpeakerRole.FOUNDER),
        _claim("valuation", 1_000_000_000, stype=SourceType.NEWS, sname="TC"),
    ]
    company, all_claims = _reconcile_company(meta, claims, now=NOW, as_of=AS_OF)
    events = publish_company(company, all_claims, now=NOW)

    # Derived ARR (MRR×12 = 120M) contradicts reported ~60M -> flagged + event emitted.
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


def test_dashboard_renders_top_50_watchlist_slots(data_dir):
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

    from openpitch.pipeline.dashboard import DIST, build

    build()
    index = (DIST / "index.html").read_text()
    assert "1 sourced profiles · 50 top-50 slots" in index
    assert index.count('class="card') == 50
    assert "ARR / revenue" in index
    assert "pending sourced metrics" in index
    assert '<option value="valuation" selected>Valuation</option>' in index
    assert 'data-sort' in index
    assert 'data-valuation="0.0"' in index
    assert "View data quality" in index
    assert (DIST / "quality.html").exists()
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
