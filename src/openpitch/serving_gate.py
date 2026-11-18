"""Serving-time data-quality gate.

Decides, per company, which published figures are too implausible to show and which
to show with a caution. `assess` is pure: it takes a Company and its claims and does
no I/O. The gate runs only where data is served (MCP tools, dashboard, quality report);
data/ is never edited, so a withheld figure is hidden from citation, not deleted.

A withheld figure never appears in a served value, and every served `reason` is
written without it. The numeric `detail` is emitted only on the audit path
(get_provenance), which also keeps the raw claims.

Thresholds and the reasoning behind them live in config/serving_gate.yaml.
Kill switch: OPENPITCH_GATE=off serves every figure ungated.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

GATE_VERSION = "1"
WITHHOLD, CAUTION = "withhold", "caution"

# Mirrors config/serving_gate.yaml (tests/test_serving_gate.py keeps them equal). Used
# for any key the YAML lacks or gets wrong, e.g. a no-clone install on an older remote.
DEFAULTS: dict = {
    "enabled": True,
    "min_confidence": 0.0,
    "shape_rule": True,
    "usd_floors": {"valuation": 100000, "total_funding": 100000, "round_amount": 100000,
                   "arr": 10000, "mrr": 1000},
    "bounds": {"revenue_multiple": [0.5, 500], "revenue_growth": [-100, 5000],
               "headcount_growth": [-100, 1000], "nrr": [0, 1000], "equity_sold_pct": [0, 100],
               "headcount": [1, 250000], "subscribers": [1, 5000000000], "open_roles": [0, 50000]},
    "usd_units": ["", "usd", "us$", "$", "dollars", "us dollars"],
    "fx_usd_per_unit": {"eur": 1.08, "gbp": 1.27, "chf": 1.12, "cad": 0.73, "aud": 0.65,
                        "sgd": 0.74, "nzd": 0.6, "cny": 0.14, "rmb": 0.14, "yuan": 0.14,
                        "hkd": 0.128, "krw": 0.00072, "won": 0.00072, "jpy": 0.0067,
                        "yen": 0.0067, "inr": 0.012, "aed": 0.27, "sar": 0.27, "ils": 0.27,
                        "idr": 0.000063, "brl": 0.18, "sek": 0.095, "nok": 0.093, "try": 0.03},
    "parity_band": [0.5, 2.0],
    "face_tolerance": 0.05,
    "pair_tolerance": 0.10,
    "arr_valuation_max_ratio": 2.0,
    "high_confidence_guard": 0.75,
    "soft_qualifiers": ["forward_looking", "unconfirmed"],
    "stale_derivation_ratio": 3.0,
}

_SCALE = {"trillion": 1e12, "tn": 1e12, "t": 1e12, "billion": 1e9, "bn": 1e9, "b": 1e9,
          "million": 1e6, "mn": 1e6, "mm": 1e6, "m": 1e6, "thousand": 1e3, "k": 1e3}
_SC = r"(trillion|billion|million|thousand|tn|bn|mn|mm|t|b|m|k)?(?![a-z])"
_NUM = r"(\d+(?:[.,]\d+)*)"
_AMOUNT = re.compile(_NUM + r"\s*" + _SC, re.I)
# A USD-marked amount: "$900M", "US$900 million", "USD 900m", "900 million US dollars".
# "(?<![a-z])\$" keeps HK$, S$, A$, R$ and similar out.
_USD_AMOUNT = re.compile(
    r"(?:(?<![a-z])\$|us\$|usd\s?)\s*" + _NUM + r"\s*" + _SC
    + r"|" + _NUM + r"\s*" + r"(trillion|billion|million|thousand|tn|bn|mn|mm|t|b|m|k)?"
    + r"\s*(?:usd|us dollars|dollars)(?![a-z])", re.I)


@dataclass(frozen=True)
class Verdict:
    action: str                      # WITHHOLD or CAUTION
    rule: str
    reason: str                      # served text: never contains a withheld figure
    evidence: tuple[str, ...] = ()   # claim ids that tripped the rule, where known
    detail: str = ""                 # audit text with the numbers (get_provenance only)

    def as_dict(self, detail: bool = False) -> dict:
        d = {"action": self.action, "rule": self.rule, "reason": self.reason,
             "evidence_claim_ids": list(self.evidence), "gate_version": GATE_VERSION}
        if detail and self.detail:
            d["detail"] = self.detail
        return d


def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _valid(value, default):
    """`value` if it has the shape of `default`, else `default` (one bad YAML key never
    disables the gate or crashes a tool)."""
    if isinstance(default, bool):
        if isinstance(value, str):
            return value.strip().lower() not in ("off", "false", "0", "no")
        return value if isinstance(value, bool) else default
    if isinstance(default, (int, float)):
        return value if _num(value) else default
    if isinstance(default, list):
        if not isinstance(value, list):
            return default
        if default and _num(default[0]):        # a numeric pair such as parity_band
            return value if len(value) == len(default) and all(map(_num, value)) else default
        return [str(x) for x in value]
    if isinstance(default, dict):
        out = dict(default)
        for k, v in (value.items() if isinstance(value, dict) else ()):
            out[k] = _valid(v, default[k]) if k in default else v
        return out
    return value


def _cfg() -> dict:
    from .config import load_serving_gate
    raw = load_serving_gate()
    raw = raw if isinstance(raw, dict) else {}
    return {k: _valid(raw.get(k, d), d) for k, d in DEFAULTS.items()}


def enabled() -> bool:
    if os.environ.get("OPENPITCH_GATE", "").strip().lower() in ("off", "0", "false", "no"):
        return False
    return bool(_cfg()["enabled"])


def _close(a: float, b: float, tol: float) -> bool:
    return bool(a) and abs(a - b) / abs(a) <= tol


def _quotes(text: str | None) -> tuple[list[float], list[float], list[float]]:
    """From a claim's raw text: (bare numbers, scaled amounts, USD-marked scaled amounts)."""
    bare, scaled, usd = [], [], []
    for n, sc in _AMOUNT.findall(text or ""):
        try:
            x = float(n.replace(",", ""))
        except ValueError:
            continue
        bare.append(x)
        scaled.append(x * _SCALE.get((sc or "").lower(), 1))
    for n1, s1, n2, s2 in _USD_AMOUNT.findall(text or ""):
        n, sc = (n1, s1) if n1 else (n2, s2)
        try:
            usd.append(float(n.replace(",", "")) * _SCALE.get((sc or "").lower(), 1))
        except ValueError:
            continue
    return bare, scaled, usd


def _split_unit(unit: str | None) -> tuple[str, float]:
    """'million USD' -> ('usd', 1e6); 'x' -> ('x', 1.0); None -> ('', 1.0)."""
    scale, rest = 1.0, []
    for w in re.findall(r"[a-z$]+", (unit or "").lower()):
        if w in _SCALE and scale == 1.0:
            scale = _SCALE[w]
        else:
            rest.append(w)
    return " ".join(rest), scale


def _fmt(v) -> str:
    return f"{v:,.4g}" if _num(v) else repr(v)


def _money(v: float) -> str:
    for div, suf in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(v) >= div:
            return f"${v / div:g}{suf}"
    return f"${v:g}"


def assess(company, claims=None) -> dict[str, Verdict]:
    """Verdict per metric that fails a rule; metrics absent from the result pass.

    `claims` is the company's claim list. Without it the unit, currency and derivation
    rules cannot run and only the value-only rules apply.
    """
    if not enabled():
        return {}
    cfg = _cfg()
    from .config import load_metrics
    reg = {k: d.unit for k, d in load_metrics().items()}
    by_id = {c.id: c for c in (claims or [])}
    M = company.metrics
    out: dict[str, Verdict] = {}
    flagged: set[str] = set()      # claims that tripped a unit rule

    def hold(m, rule, reason, detail="", ev=()):
        if m not in out or out[m].action != WITHHOLD:    # first withhold reason wins
            out[m] = Verdict(WITHHOLD, rule, reason, tuple(ev), detail)

    def caution(m, rule, reason, detail="", ev=()):
        if m not in out:
            out[m] = Verdict(CAUTION, rule, reason, tuple(ev), detail)

    def held(m) -> bool:
        return m in out and out[m].action == WITHHOLD

    # Confidence floor (off by default; see the config for why).
    floor = float(cfg["min_confidence"])
    if floor > 0:
        for m, rv in M.items():
            if rv.confidence < floor:
                hold(m, "below_min_confidence", f"confidence is below the {floor} floor",
                     f"confidence {rv.confidence} < {floor}")

    # Shape: a value whose type cannot be the registry type.
    if cfg["shape_rule"]:
        for m, rv in M.items():
            u, v = reg.get(m), rv.value
            if v is None:
                continue
            if u == "object" and not isinstance(v, (dict, str)):
                hold(m, "shape", f"{m} should describe a round but holds a bare number",
                     f"value {_fmt(v)}")
            elif u == "list" and not isinstance(v, list):
                hold(m, "shape", f"{m} should be a list of names but holds a single value",
                     f"value {_fmt(v)}")
            elif u in ("USD", "x", "count", "pct") and not _num(v):
                hold(m, "shape", f"{m} should be a number", f"value {_fmt(v)}")

    # Unit trail (USD): the served value equals a supporting claim's number that was
    # stated in another unit, a ratio, or with an unapplied scale word.
    usd_units = set(cfg["usd_units"])
    fx = cfg["fx_usd_per_unit"]
    lo_par, hi_par = cfg["parity_band"]
    tol = float(cfg["face_tolerance"])
    for m, rv in M.items():
        if reg.get(m) != "USD" or not _num(rv.value) or held(m):
            continue
        for cid in rv.supporting_claims:
            c = by_id.get(cid)
            if not c or c.derivation or not _num(c.value):
                continue
            cv = float(c.value)
            if not cv or abs(rv.value - cv) / abs(cv) > tol:
                continue
            cur, scale = _split_unit(c.unit)
            bare, scaled, usd_quoted = _quotes(c.raw_text)
            if cur in usd_units:
                if scale > 1 and cv < scale:
                    # "$0.5 billion" stored as 5e8 was scaled correctly; "$500 million"
                    # stored as 500 was not. Without a parsable quote, assume not.
                    applied = any(_close(n * scale, cv, tol) for n in bare)
                    if not (applied and not any(_close(n, cv, tol) for n in bare)):
                        flagged.add(cid)
                        hold(m, "unit_not_normalized",
                             f'the source states it in "{c.unit}" but the scale was never applied',
                             f"value {_fmt(rv.value)} vs unit {c.unit}", [cid])
                        break
                continue
            rate = fx.get(cur)
            if rate is not None:
                converted = (any(_close(a, cv, tol) for a in usd_quoted)
                             or (scaled and not any(_close(a, cv, tol) for a in scaled)))
                if converted:
                    caution(m, "currency_label_mismatch",
                            f"labelled {c.unit} but the value appears already converted to USD",
                            f"value {_fmt(cv)}; quoted {[_fmt(a) for a in scaled]}", [cid])
                    continue
                if lo_par <= rate <= hi_par:
                    caution(m, "currency_unverified",
                            f"stated in {c.unit} and shown unconverted; the error is bounded "
                            f"near {abs(1 - rate):.0%}", f"value {_fmt(cv)} {c.unit}", [cid])
                    continue
            flagged.add(cid)
            hold(m, "unit_not_normalized",
                 f'it equals a source figure stated in "{c.unit}" that was never converted to USD',
                 f"value {_fmt(rv.value)} equals claim {cid} in {c.unit}", [cid])
            break

    # Magnitude floors (USD) and believable windows (everything else).
    for m, fl in cfg["usd_floors"].items():
        rv = M.get(m)
        if rv and _num(rv.value) and _num(fl) and rv.value < fl:
            hold(m, "below_floor", f"below the {_money(fl)} floor for {m}; the magnitude was "
                                   "probably lost", f"value {_fmt(rv.value)} < {_fmt(fl)}")
    for m, bound in cfg["bounds"].items():
        rv = M.get(m)
        if not (rv and _num(rv.value) and isinstance(bound, (list, tuple)) and len(bound) == 2):
            continue
        lo, hi = bound
        if not lo <= rv.value <= hi:
            hold(m, "out_of_bounds", f"outside the believable range {_fmt(lo)} to {_fmt(hi)}",
                 f"value {_fmt(rv.value)}")

    # Cross-metric identities, only between figures that survived the rules above.
    soft = set(cfg["soft_qualifiers"])
    guard = float(cfg["high_confidence_guard"])
    ptol = float(cfg["pair_tolerance"])

    def served(m) -> bool:
        return m in M and _num(M[m].value) and not held(m)

    def is_soft(m) -> bool:
        rv = M[m]
        if getattr(rv, "unconfirmed", False):
            return True
        sup = [by_id[x] for x in rv.supporting_claims if x in by_id and not by_id[x].derivation]
        return bool(sup) and all(set(c.qualifiers) & soft for c in sup)

    def resolve(a, b, relation, structural=None):
        """Blame the forward-looking/unconfirmed side, else the structural loser, else
        the less confident side. Withhold it only if it is not itself high confidence."""
        sa, sb = is_soft(a), is_soft(b)
        loser = (a if sa else b) if sa != sb else structural or (
            a if M[a].confidence <= M[b].confidence else b)
        other = b if loser == a else a
        detail = f"{a} {_fmt(val(a))}, {b} {_fmt(val(b))}"
        if M[loser].confidence < guard:
            hold(loser, "cross_metric", f"{relation}; {loser} is the less reliable side", detail)
        else:
            caution(loser, "cross_metric", relation, detail)
            caution(other, "cross_metric", relation, detail)

    def val(m) -> float:
        return float(M[m].value)

    r = float(cfg["arr_valuation_max_ratio"])
    if served("arr") and served("valuation") and val("arr") > r * val("valuation"):
        resolve("arr", "valuation", f"revenue exceeds {r:g}x the valuation")
    if served("total_funding") and served("valuation") and val("total_funding") > val("valuation") * (1 + ptol):
        resolve("valuation", "total_funding", "total raised exceeds the valuation")
    if served("round_amount") and served("valuation") and val("round_amount") > val("valuation") * (1 + ptol):
        resolve("round_amount", "valuation", "a single round exceeds the valuation")
    if served("round_amount") and served("total_funding") and val("round_amount") > val("total_funding") * (1 + ptol):
        resolve("total_funding", "round_amount", "total raised is below a single round",
                structural="total_funding")

    def derived_inputs(rv) -> list[str] | None:
        sup = [by_id[x] for x in rv.supporting_claims if x in by_id]
        if not sup or not all(s.derivation for s in sup):
            return None
        return [i for s in sup for i in s.derivation.inputs]

    # Derived figures: withhold when built from a withheld or unit-flagged input, unless
    # it is a ratio of inputs sharing one scaled unit (the scale cancels: 500M/79.5M).
    bad_inputs = flagged | {cid for m, v in out.items() if v.action == WITHHOLD
                            for cid in M[m].supporting_claims}
    for m, rv in M.items():
        inputs = None if held(m) else derived_inputs(rv)
        tainted = [i for i in inputs or () if i in bad_inputs]
        if not tainted:
            continue
        units = {(by_id[i].unit or "").strip().lower() for i in inputs if i in by_id}
        if reg.get(m) == "x" and len(units) == 1 and _split_unit(next(iter(units)))[1] > 1:
            continue
        hold(m, "depends_on_withheld", f"{m} is computed from a withheld input",
             f"tainted inputs {tainted}", tainted)

    # Stale derivations, once every withhold is final: caution only (the input may be the
    # accurate one), and never against a withheld metric, whose figure must not be quoted.
    stale = float(cfg["stale_derivation_ratio"])
    for m, rv in M.items():
        if held(m):
            continue
        for i in derived_inputs(rv) or ():
            c = by_id.get(i)
            pub = M.get(c.metric) if c else None
            if not (c and pub) or held(c.metric):
                continue
            if _num(c.value) and _num(pub.value) and c.value and pub.value:
                ratio = max(c.value, pub.value) / min(c.value, pub.value)
                if ratio > stale:
                    caution(m, "stale_derivation",
                            f"computed from a {c.metric} input {ratio:.1f}x away from the "
                            f"published {c.metric}",
                            f"input {_fmt(c.value)} vs published {_fmt(pub.value)}", [i])
                    break
    return out


def guarded(company, load_claims=None) -> dict[str, Verdict]:
    """assess() for serving call sites: never raises. An unreadable claims file degrades
    to the value-only rules; any other failure serves the company ungated, as before the
    gate existed, rather than failing the tool or the build."""
    if company is None or not enabled():
        return {}
    claims = None
    if load_claims is not None:
        try:
            claims = load_claims(company.id)
        except Exception:  # noqa: BLE001 — one bad file must not fail the whole response
            claims = None
    try:
        return assess(company, claims)
    except Exception:  # noqa: BLE001
        return {}


# ── Serving helpers: one definition of "withheld", shared by MCP and dashboard ──

_FIGURE_KEYS = ("value", "range", "delta", "confirmed_value", "confirmed_as_of")


def withheld(verdicts: dict, metric: str) -> Verdict | None:
    v = verdicts.get(metric)
    return v if v and v.action == WITHHOLD else None


def apply(metric_dict: dict, v: Verdict) -> dict:
    """A serialized ResolvedValue, gated. Withheld nulls every figure key (keeping the
    schema's keys present); caution annotates and keeps the figure."""
    if v.action == WITHHOLD:
        nulled = {k: None for k in _FIGURE_KEYS if k in metric_dict}
        return {**metric_dict, **nulled, "value": None, "status": "withheld", "gate": v.as_dict()}
    return {**metric_dict, "gate": v.as_dict()}


def cell(v: Verdict, rv) -> dict:
    """Compact withheld marker for summary views. Distinct from None, which means no data."""
    return {"value": None, "status": "withheld", "rule": v.rule, "reason": v.reason,
            "confidence": rv.confidence, "as_of": str(rv.as_of)}


def mask_history(rows: list[dict]) -> list[dict]:
    return [{**r, "value": None} for r in rows]


def mask_event(ev: dict, v: Verdict) -> dict:
    """An event about a withheld figure: drop the numbers, including from the summary."""
    p = dict(ev.get("payload") or {})
    for k in ("previous", "current", "change_pct"):
        if k in p:
            p[k] = None
    p["status"] = "withheld"
    name = ev.get("company_name") or ev.get("company_id")
    return {**ev, "payload": p, "gate": v.as_dict(),
            "summary": f"{name}: {p.get('metric')} figure withheld by the data-quality gate ({v.rule})"}
