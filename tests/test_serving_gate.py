"""Serving-time data-quality gate: rules, robustness, kill switch, and the contract
that a withheld figure never reaches a served value or served text."""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path

import pytest
import yaml

from openpitch import config as cfgmod
from openpitch import serving_gate as g
from openpitch import store
from openpitch.mcp_server import tools
from openpitch.models import (
    Claim, Company, Derivation, EstimateType, ResolvedValue, Source, SourceType,
)
from openpitch.pipeline import dashboard, quality

AS_OF = date(2026, 11, 18)
NOW = datetime(2026, 11, 18, 5, 0, 0)


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENPITCH_DATA_DIR", str(tmp_path))
    return tmp_path


def _cl(cid, metric, value, unit=None, raw="", quals=(), inputs=None, company="acme"):
    return Claim(
        id=cid, company_id=company, metric=metric, value=value, unit=unit,
        raw_text=raw or f"{metric} is {value}", qualifiers=list(quals),
        source=Source(type=SourceType.NEWS if not inputs else SourceType.DERIVED, name="TC"),
        extracted_at=NOW, extractor_model="t", base_confidence=0.5,
        derivation=Derivation(kind="identity", formula="v/arr", inputs=list(inputs)) if inputs else None,
    )


def _rv(metric, value, conf=0.5, claims=(), **kw):
    return ResolvedValue(metric=metric, value=value, as_of=AS_OF, estimate_type=EstimateType.REPORTED,
                         confidence=conf, supporting_claims=[c.id for c in claims], **kw)


def _co(cid="acme", **metrics):
    return Company(id=cid, name=cid.title(), last_updated=AS_OF, metrics=metrics)


def _rule(verdicts, metric):
    v = verdicts.get(metric)
    return (v.action, v.rule) if v else None


def _forms(x: float) -> list[str]:
    """Ways a figure could be spelled in text: 500.0, 500, $500, 4e+09, 4,000,000,000."""
    return {str(x), g._fmt(x), g._money(x), f"{x:g}", f"{x:,.0f}", dashboard._money(x)} - {""}


def _mentions(text: str, x: float) -> bool:
    return any(re.search(rf"(?<![\d.,]){re.escape(f)}(?![\d])", text) for f in _forms(x))


# ── rules ────────────────────────────────────────────────────────────────────

def test_scale_word_never_applied_is_withheld_but_applied_scale_passes():
    bad = _cl("c1", "valuation", 500, unit="million USD")
    assert _rule(g.assess(_co(valuation=_rv("valuation", 500, claims=[bad])), [bad]), "valuation") \
        == (g.WITHHOLD, "unit_not_normalized")
    ok = _cl("c2", "valuation", 500e6, unit="million USD")
    assert g.assess(_co(valuation=_rv("valuation", 500e6, claims=[ok])), [ok]) == {}


def test_fractional_scale_that_was_applied_passes():
    # "$0.5 billion" stored as 5e8 is correct even though 5e8 < 1e9.
    c = _cl("c1", "valuation", 5e8, unit="billion USD", raw="valued at $0.5 billion")
    assert g.assess(_co(valuation=_rv("valuation", 5e8, claims=[c])), [c]) == {}


def test_ratio_unit_written_into_money_metric_is_withheld():
    c = _cl("c1", "arr", 80e6, unit="x")
    assert _rule(g.assess(_co(arr=_rv("arr", 80e6, claims=[c])), [c]), "arr") == (g.WITHHOLD, "unit_not_normalized")


def test_unconverted_far_currency_at_face_value_is_withheld():
    c = _cl("c1", "round_amount", 7e9, unit="HKD", raw="raised HK$7 billion")
    v = g.assess(_co(round_amount=_rv("round_amount", 7e9, claims=[c])), [c])
    assert _rule(v, "round_amount") == (g.WITHHOLD, "unit_not_normalized")
    assert v["round_amount"].evidence == ("c1",)


def test_far_currency_value_matching_a_quoted_usd_amount_is_converted():
    c = _cl("c1", "round_amount", 9e8, unit="HKD", raw="raised HK$7 billion (about US$900 million)")
    assert _rule(g.assess(_co(round_amount=_rv("round_amount", 9e8, claims=[c])), [c]), "round_amount") \
        == (g.CAUTION, "currency_label_mismatch")


def test_converted_value_with_stale_currency_label_is_only_cautioned():
    c = _cl("c1", "valuation", 755_588_000, unit="KRW", raw="valued at 1 trillion won")
    assert _rule(g.assess(_co(valuation=_rv("valuation", 755_588_000, claims=[c])), [c]), "valuation") \
        == (g.CAUTION, "currency_label_mismatch")


def test_near_parity_currency_unconverted_vs_already_converted():
    raw = _cl("c1", "total_funding", 13e6, unit="EUR", raw="raised €13 million")
    assert _rule(g.assess(_co(total_funding=_rv("total_funding", 13e6, claims=[raw])), [raw]), "total_funding") \
        == (g.CAUTION, "currency_unverified")
    conv = _cl("c2", "total_funding", 14.04e6, unit="EUR", raw="raised €13 million")
    assert _rule(g.assess(_co(total_funding=_rv("total_funding", 14.04e6, claims=[conv])), [conv]), "total_funding") \
        == (g.CAUTION, "currency_label_mismatch")


def test_money_floor_and_non_money_bounds():
    v = g.assess(_co(arr=_rv("arr", 20.8), revenue_multiple=_rv("revenue_multiple", 742.9),
                     headcount=_rv("headcount", 689_000)))
    assert _rule(v, "arr") == (g.WITHHOLD, "below_floor")
    assert _rule(v, "revenue_multiple") == (g.WITHHOLD, "out_of_bounds")
    assert _rule(v, "headcount") == (g.WITHHOLD, "out_of_bounds")


def test_shape_rule_rejects_bare_number_in_object_slot_only():
    assert _rule(g.assess(_co(latest_round=_rv("latest_round", 7.0))), "latest_round") == (g.WITHHOLD, "shape")
    assert g.assess(_co(latest_round=_rv("latest_round", "Series B"))) == {}


def test_cross_metric_withholds_the_less_reliable_side():
    v = g.assess(_co(arr=_rv("arr", 103e9, conf=0.37), valuation=_rv("valuation", 14.6e9, conf=0.97)))
    assert _rule(v, "arr") == (g.WITHHOLD, "cross_metric")
    assert "valuation" not in v


def test_cross_metric_never_withholds_a_high_confidence_figure():
    # A round above total raised: total_funding is the structural loser, but at 0.97 it
    # may be debt-inclusive, so both sides are only cautioned.
    v = g.assess(_co(total_funding=_rv("total_funding", 3e9, conf=0.97),
                     round_amount=_rv("round_amount", 3.9e9, conf=0.9)))
    assert _rule(v, "total_funding") == (g.CAUTION, "cross_metric")
    assert _rule(v, "round_amount") == (g.CAUTION, "cross_metric")


def test_forward_looking_side_loses_a_cross_metric_conflict():
    fl = _cl("r1", "round_amount", 2.5e9, quals=["unconfirmed"])
    v = g.assess(_co(total_funding=_rv("total_funding", 2e9, conf=0.4),
                     round_amount=_rv("round_amount", 2.5e9, conf=0.66, claims=[fl])), [fl])
    assert _rule(v, "round_amount") == (g.WITHHOLD, "cross_metric")
    assert "total_funding" not in v


def test_derived_figure_inherits_a_withheld_input():
    a = _cl("a1", "arr", 80e6, unit="x")
    vv = _cl("v1", "valuation", 12e9)
    d = _cl("d1", "revenue_multiple", 150, inputs=["v1", "a1"])
    v = g.assess(_co(arr=_rv("arr", 80e6, claims=[a]), valuation=_rv("valuation", 12e9, claims=[vv]),
                     revenue_multiple=_rv("revenue_multiple", 150, claims=[d])), [a, vv, d])
    assert _rule(v, "revenue_multiple") == (g.WITHHOLD, "depends_on_withheld")


def test_ratio_of_inputs_sharing_one_scale_error_is_still_served():
    # 500 / 79.5 = 6.29x is correct even though both inputs lost "million".
    a = _cl("a1", "arr", 79.5, unit="million USD")
    vv = _cl("v1", "valuation", 500, unit="million USD")
    d = _cl("d1", "revenue_multiple", 6.29, inputs=["v1", "a1"])
    v = g.assess(_co(arr=_rv("arr", 79.5, claims=[a]), valuation=_rv("valuation", 500, claims=[vv]),
                     revenue_multiple=_rv("revenue_multiple", 6.29, claims=[d])), [a, vv, d])
    assert _rule(v, "arr")[0] == _rule(v, "valuation")[0] == g.WITHHOLD
    assert "revenue_multiple" not in v


def test_stale_derivation_never_quotes_a_withheld_metric():
    # valuation 4e9 is withheld (cross_metric); a multiple derived from an older 2e10
    # valuation must not carry a caution that names the withheld 4e9.
    old = _cl("v_old", "valuation", 2e10)
    cur = _cl("v_cur", "valuation", 4e9)
    tf = _cl("tf", "total_funding", 1.2e10)
    ar = _cl("ar", "arr", 1e9)
    d = _cl("d1", "revenue_multiple", 20, inputs=["v_old", "ar"])
    v = g.assess(_co(valuation=_rv("valuation", 4e9, conf=0.3, claims=[cur]),
                     total_funding=_rv("total_funding", 1.2e10, conf=0.6, claims=[tf]),
                     arr=_rv("arr", 1e9, conf=0.6, claims=[ar]),
                     revenue_multiple=_rv("revenue_multiple", 20, claims=[d])), [old, cur, tf, ar, d])
    assert _rule(v, "valuation") == (g.WITHHOLD, "cross_metric")
    assert not any(_mentions(x.reason + x.detail, 4e9) for m, x in v.items() if m != "valuation")


def test_served_reasons_never_contain_the_withheld_figure():
    cases = [
        (_co(arr=_rv("arr", 20.8)), "arr", 20.8, []),
        (_co(headcount=_rv("headcount", 689_000)), "headcount", 689_000, []),
        (_co(valuation=_rv("valuation", 4e9, conf=0.3), total_funding=_rv("total_funding", 1.2e10, conf=0.6)),
         "valuation", 4e9, []),
    ]
    c = _cl("c1", "valuation", 500, unit="million USD", raw="valued at $500 million")
    cases.append((_co(valuation=_rv("valuation", 500, claims=[c])), "valuation", 500, [c]))
    for company, metric, figure, claims in cases:
        v = g.assess(company, claims)[metric]
        assert v.action == g.WITHHOLD
        assert not _mentions(v.reason, figure), (metric, v.reason)
        assert _mentions(v.detail, figure), (metric, v.detail)       # the audit text keeps it


def test_clean_company_passes_untouched():
    c = _cl("c1", "valuation", 1e9)
    assert g.assess(_co(valuation=_rv("valuation", 1e9, conf=0.9, claims=[c]),
                        arr=_rv("arr", 60e6)), [c]) == {}


def test_confidence_floor_is_off_by_default_and_works_when_set(monkeypatch):
    low = _co(arr=_rv("arr", 60e6, conf=0.05))
    assert g.assess(low) == {}
    monkeypatch.setattr(g, "_cfg", lambda: {**g.DEFAULTS, "min_confidence": 0.2})
    assert _rule(g.assess(low), "arr") == (g.WITHHOLD, "below_min_confidence")


# ── robustness ───────────────────────────────────────────────────────────────

def test_kill_switch_disables_every_rule(monkeypatch):
    monkeypatch.setenv("OPENPITCH_GATE", "off")
    assert not g.enabled()
    assert g.assess(_co(arr=_rv("arr", 20.8), latest_round=_rv("latest_round", 7.0))) == {}


@pytest.mark.parametrize("raw", [[], "nonsense", None, 42,
                                 {"enabled": "off"},
                                 {"parity_band": "x", "bounds": {"headcount": "bad"}, "usd_floors": None},
                                 {"enabled": None, "min_confidence": "high"}])
def test_malformed_config_never_crashes(monkeypatch, raw):
    monkeypatch.setattr(cfgmod, "load_serving_gate", lambda: raw)
    v = g.assess(_co(arr=_rv("arr", 20.8), headcount=_rv("headcount", 689_000)))
    if raw == {"enabled": "off"}:
        assert v == {} and not g.enabled()
    else:
        assert _rule(v, "arr") == (g.WITHHOLD, "below_floor")       # defaults still apply


@pytest.mark.parametrize("text", ["enabled: [unclosed", "- a\n- b\n", "", "\xff\xfe"])
def test_unparsable_config_file_loads_as_empty(tmp_path, monkeypatch, text):
    (tmp_path / "serving_gate.yaml").write_bytes(text.encode("latin-1"))
    monkeypatch.setenv("OPENPITCH_CONFIG_DIR", str(tmp_path))
    cfgmod.load_serving_gate.cache_clear()
    try:
        assert cfgmod.load_serving_gate() == {}
    finally:
        cfgmod.load_serving_gate.cache_clear()


def test_yaml_and_code_defaults_stay_identical():
    cfg = yaml.safe_load((Path(__file__).parents[1] / "config" / "serving_gate.yaml").read_text())
    assert cfg == g.DEFAULTS


# ── MCP + dashboard contract ─────────────────────────────────────────────────

BAD = 500.0                               # a $500M valuation that lost "million"
_FIGURE_KEYS = {"value", "current", "previous", "range", "delta", "confirmed_value"}


def _seed_bad_company():
    bad = _cl("c1", "valuation", BAD, unit="million USD", raw="valued at $500 million")
    ok = _cl("c2", "arr", 60e6)
    c = _co(valuation=_rv("valuation", BAD, claims=[bad]), arr=_rv("arr", 60e6, conf=0.8, claims=[ok]))
    store.write_company(c)
    store.write_claims("acme", [bad, ok])
    store.append_history("acme", "valuation", c.metrics["valuation"])
    ev = {"id": "e1", "schema_version": "1.0", "type": "valuation_update", "company_id": "acme",
          "company_name": "Acme", "summary": f"Acme valuation changed None -> {BAD}",
          "payload": {"metric": "valuation", "previous": None, "current": BAD, "change_pct": None},
          "confidence": 0.5, "estimate_type": "reported", "sources": [], "detected_at": "2026-11-18T05:00:00"}
    feed = Path(store.data_dir()) / "events" / "feed.jsonl"
    feed.parent.mkdir(parents=True, exist_ok=True)
    feed.write_text(json.dumps(ev) + "\n")


def _leaks(obj, path="") -> list[str]:
    """Every place the withheld figure surfaces: a value-bearing key, or any text."""
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in _FIGURE_KEYS and v == BAD:
                out.append(f"{path}.{k}")
            out += _leaks(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out += _leaks(v, f"{path}[{i}]")
    elif isinstance(obj, str) and _mentions(obj, BAD):
        out.append(f"{path} (text)")
    return out


def test_no_tool_leaks_a_withheld_figure(data_dir):
    _seed_bad_company()
    responses = {
        "list_companies": tools.list_companies(),
        "get_company": tools.get_company("acme"),
        "get_metric": tools.get_metric("acme", "valuation", with_history=True),
        "compare_companies": tools.compare_companies(["acme"], ["valuation", "arr"]),
        "get_events": tools.get_events(),
        "what_moved": tools.what_moved(since="2026-01-01"),
    }
    for name, resp in responses.items():
        assert _leaks(resp) == [], f"{name} leaks the withheld figure: {_leaks(resp)}"
    # The healthy metric on the same company is untouched.
    assert responses["compare_companies"]["comparison"][0]["metrics"]["arr"]["value"] == 60e6


def test_get_metric_reports_withheld_and_points_to_provenance(data_dir):
    _seed_bad_company()
    r = tools.get_metric("acme", "valuation")
    assert r["status"] == "withheld"
    assert "value" in r["metric"] and r["metric"]["value"] is None      # schema key kept, nulled
    assert r["metric"]["gate"]["rule"] == "unit_not_normalized"
    assert r["next"] == "get_provenance('acme', 'valuation')"
    # Withheld is distinct from no data.
    cells = tools.compare_companies(["acme"], ["valuation", "headcount"])["comparison"][0]["metrics"]
    assert cells["valuation"]["status"] == "withheld" and cells["headcount"] is None


def test_provenance_stays_a_complete_audit_trail(data_dir):
    _seed_bad_company()
    p = tools.get_provenance("acme", "valuation")
    assert p["status"] == "ok" and p["gate"]["action"] == "withhold"
    assert _mentions(p["gate"]["detail"], BAD)                           # numbers live here only
    raw = {c["id"]: c for c in p["claims"]}
    assert raw["c1"]["value"] == BAD and raw["c1"]["gate_flag"] == "unit_not_normalized"


def test_provenance_flags_supporting_claims_when_the_rule_names_none(data_dir):
    low = _cl("f1", "arr", 20.8)
    store.write_company(_co(arr=_rv("arr", 20.8, claims=[low])))
    store.write_claims("acme", [low])
    p = tools.get_provenance("acme", "arr")
    assert p["gate"]["rule"] == "below_floor" and p["gate"]["evidence_claim_ids"] == []
    assert p["claims"][0]["gate_flag"] == "below_floor"


def test_one_unreadable_claims_file_degrades_instead_of_failing(data_dir):
    store.write_company(_co(valuation=_rv("valuation", 50)))     # below the floor
    store.write_company(_co("beta", valuation=_rv("valuation", 2e9, conf=0.9)))
    (Path(data_dir) / "claims").mkdir(exist_ok=True)
    (Path(data_dir) / "claims" / "acme.json").write_text("{not json")
    heads = {c["id"]: c["headline_metrics"] for c in tools.list_companies()["companies"]}
    assert heads["acme"]["valuation"]["status"] == "withheld"     # value-only rules still ran
    assert heads["beta"]["valuation"]["value"] == 2e9


def test_kill_switch_restores_ungated_output(data_dir, monkeypatch):
    _seed_bad_company()
    monkeypatch.setenv("OPENPITCH_GATE", "off")
    assert tools.get_metric("acme", "valuation")["metric"]["value"] == BAD
    assert "gate" not in tools.get_provenance("acme", "valuation")


def test_quality_report_gate_section_only_when_the_gate_ran(data_dir, monkeypatch):
    store.write_company(_co(arr=_rv("arr", 20.8), latest_round=_rv("latest_round", 7.0)))
    on = quality.build_snapshot()
    md = quality.render_markdown(on)
    assert "Implausible Figures Withheld" in md and "latest_round: 1" in md
    assert any("arr (below_floor)" in x for x in on.gate_withheld)
    monkeypatch.setenv("OPENPITCH_GATE", "off")
    off = quality.build_snapshot()
    assert not off.gate_ran and off.gate_withheld == []
    assert "Implausible" not in quality.render_markdown(off) and "Implausible" not in quality.render_html(off)


def test_dashboard_never_renders_or_sorts_by_a_withheld_figure(data_dir):
    _seed_bad_company()
    c = store.read_company("acme")
    v = g.assess(c, store.read_claims("acme"))
    card = dashboard._company_card(c, 1, v)
    assert "withheld" in card and 'data-valuation="0.0"' in card
    assert dashboard._metric_number(c, "valuation", v) == 0.0
    assert dashboard._metric_number(c, "valuation") == BAD      # ungated call unchanged
    # The page keeps the source quote ("valued at $500 million", which is accurate) as the
    # audit trail; OpenPitch's own wrong figure must never render as the value.
    page = dashboard._company_page(c, 1, v)
    assert '<span class="v"><span class="wh"' in page
    assert f'<span class="v">{dashboard._money(BAD)}' not in page
    assert not _mentions(card, BAD)
    assert "No resolved valuations yet" in dashboard._market_map([c], {"acme": v})
