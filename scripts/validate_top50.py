#!/usr/bin/env python3
"""Validate the dashboard top-50 against a deep-researched reference list.

Reads data/validation/reference_top50.json (a dated, sourced ground-truth ranking
of the top AI startups by valuation under OpenPitch's own criteria) and diffs it
against the live universe. Prints a report and writes docs/VALIDATION-TOP50.md.

Re-runnable: rerun after any ingestion to re-grade. Read-only on data/.

    PYTHONPATH=src .venv/bin/python scripts/validate_top50.py
    PYTHONPATH=src .venv/bin/python scripts/validate_top50.py --selftest
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from statistics import median

from openpitch import store
from openpitch.paths import REPO_ROOT

REFERENCE = REPO_ROOT / "data" / "validation" / "reference_top50.json"
REPORT = REPO_ROOT / "docs" / "VALIDATION-TOP50.md"
TOP_N = 50
VAL_DISCREPANCY = 0.25  # flag resolved-vs-reference valuation gaps beyond this fraction

# Last-resort name→id aliases for cases normalization can't bridge (live aliases are
# sparse). Keep tiny; prefer filling `openpitch_id` in the fixture.
ALIAS_MAP = {
    "cursor": "anysphere",
    "devin": "cognition",
    "codeium": "windsurf",
    "windsurf (codeium)": "windsurf",
    "x.ai": "xai",
    "grok": "xai",
}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def _name_keys(name: str):
    """Yield match keys for a name, including parenthetical parts.

    'Anysphere (Cursor)' -> {'anysphere cursor', 'anysphere', 'cursor'}.
    """
    keys = {_norm(name)}
    outer = re.sub(r"\(.*?\)", "", name)
    keys.add(_norm(outer))
    for part in re.findall(r"\((.*?)\)", name):
        keys.add(_norm(part))
    return {k for k in keys if k}


def build_index(companies):
    """Map every normalized name/alias/id key -> company."""
    idx = {}
    for c in companies:
        keys = {_norm(c.id)}
        keys |= _name_keys(c.name)
        for a in c.aliases or []:
            keys |= _name_keys(a)
        for k in keys:
            idx.setdefault(k, c)
    return idx


def match(ref_entry, companies, idx):
    """Resolve a reference entry to a live company, or None. Order: id → name/alias → ALIAS_MAP."""
    oid = (ref_entry.get("openpitch_id") or "").strip()
    if oid:
        for c in companies:
            if c.id == oid:
                return c
    key = _norm(ref_entry.get("name", ""))
    if key in idx:
        return idx[key]
    mapped = ALIAS_MAP.get(key)
    if mapped and mapped in idx:
        return idx[mapped]
    return None


def _valuation(c):
    rv = c.metrics.get("valuation") if c else None
    return float(rv.value) if rv and isinstance(rv.value, (int, float)) else None


def _money(v):
    return f"${v/1e9:.1f}B" if v else "—"


def evaluate():
    ref = json.loads(REFERENCE.read_text())
    ref_companies = ref.get("companies", [])[:TOP_N]
    companies = store.read_all_companies()
    idx = build_index(companies)
    op_top = {c.id for c in companies if c.in_universe and (c.universe_rank or 9999) <= TOP_N}

    rows, rank_deltas, val_errors = [], [], []
    missing_absent, missing_below, val_flags = [], [], []
    matched_ids = set()

    for e in ref_companies:
        c = match(e, companies, idx)
        ref_rank = e.get("rank")
        ref_val = e.get("valuation_usd")
        if c is None:
            missing_absent.append(e)
            rows.append((ref_rank, e["name"], "ABSENT", None, ref_val, None))
            continue
        matched_ids.add(c.id)
        op_rank = c.universe_rank
        in_top = c.id in op_top
        if not in_top:
            missing_below.append((e, c))
        if ref_rank and op_rank:
            rank_deltas.append(abs(ref_rank - op_rank))
        op_val = _valuation(c)
        if ref_val and op_val:
            err = abs(op_val - ref_val) / ref_val
            val_errors.append(err)
            if err > VAL_DISCREPANCY:
                val_flags.append((e["name"], ref_val, op_val, err))
        rows.append((ref_rank, e["name"], c.id, op_rank if in_top else f">{TOP_N}", ref_val, op_val))

    # Dashboard-only: in OP top-50 but not matched by any reference entry.
    dashboard_only = [c for c in companies if c.id in op_top and c.id not in matched_ids]
    dashboard_only.sort(key=lambda c: c.universe_rank or 9999)

    overlap = sum(1 for e in ref_companies if (m := match(e, companies, idx)) and m.id in op_top)
    return {
        "ref": ref, "n_ref": len(ref_companies), "rows": rows,
        "overlap": overlap, "missing_absent": missing_absent, "missing_below": missing_below,
        "dashboard_only": dashboard_only, "val_flags": val_flags,
        "rank_deltas": rank_deltas, "val_errors": val_errors,
    }


def render(r) -> str:
    n = r["n_ref"]
    L = []
    L.append("# OpenPitch — Top-50 Validation Report\n")
    L.append(f"Reference: deep-researched top AI startups by valuation, as of "
             f"**{r['ref'].get('as_of','?')}** ({n} entries).")
    L.append(f"Criteria: {r['ref'].get('criteria','')}\n")
    L.append("## Summary\n")
    pct = round(r["overlap"] / n * 100) if n else 0
    L.append(f"- **Overlap:** {r['overlap']} / {n} reference companies are in the dashboard top-{TOP_N} ({pct}%).")
    L.append(f"- **Missing — absent entirely:** {len(r['missing_absent'])} (not in OpenPitch's universe at all).")
    L.append(f"- **Missing — profiled but ranked >{TOP_N}:** {len(r['missing_below'])}.")
    L.append(f"- **Dashboard-only (possible false positives):** {len(r['dashboard_only'])}.")
    md = median(r["rank_deltas"]) if r["rank_deltas"] else 0
    me = median(r["val_errors"]) if r["val_errors"] else 0
    L.append(f"- **Median |rank delta|:** {md:.0f} positions · **Median valuation error:** {me*100:.0f}%.")
    L.append(f"- **Valuation discrepancies >{int(VAL_DISCREPANCY*100)}%:** {len(r['val_flags'])}.\n")

    L.append(f"## Missing from dashboard — ABSENT entirely (coverage gaps → add to watchlist)\n")
    if r["missing_absent"]:
        for e in sorted(r["missing_absent"], key=lambda e: e.get("rank") or 999):
            src = e.get("source", {})
            L.append(f"- **{e['name']}** — ref rank {e.get('rank','?')}, {_money(e.get('valuation_usd'))} "
                     f"({e.get('segment','?')}, {e.get('ai_type','?')}). Source: {src.get('outlet','?')} {src.get('date','')}")
    else:
        L.append("_None._")
    L.append("")

    L.append(f"## Missing from dashboard — profiled but ranked >{TOP_N}\n")
    if r["missing_below"]:
        for e, c in sorted(r["missing_below"], key=lambda x: x[1].universe_rank or 9999):
            L.append(f"- **{e['name']}** (`{c.id}`) — ref rank {e.get('rank','?')}, OP rank {c.universe_rank}. "
                     f"ref {_money(e.get('valuation_usd'))} vs OP {_money(_valuation(c))}")
    else:
        L.append("_None._")
    L.append("")

    L.append(f"## Dashboard-only — in OP top-{TOP_N}, not in reference top-{n} (review)\n")
    if r["dashboard_only"]:
        for c in r["dashboard_only"]:
            L.append(f"- **{c.name}** (`{c.id}`) — OP rank {c.universe_rank}, {_money(_valuation(c))} ({c.segment})")
    else:
        L.append("_None._")
    L.append("")

    L.append(f"## Valuation discrepancies > {int(VAL_DISCREPANCY*100)}%\n")
    if r["val_flags"]:
        for name, rv, ov, err in sorted(r["val_flags"], key=lambda x: -x[3]):
            L.append(f"- **{name}** — reference {_money(rv)} vs OpenPitch {_money(ov)} ({err*100:.0f}% off)")
    else:
        L.append("_None._")
    L.append("")

    L.append("## Full reference ranking vs OpenPitch\n")
    L.append("| Ref rank | Company | OP id | OP rank | Ref val | OP val |")
    L.append("|---:|---|---|---|---:|---:|")
    for ref_rank, name, oid, op_rank, rv, ov in r["rows"]:
        L.append(f"| {ref_rank or ''} | {name} | {oid} | {op_rank or ''} | {_money(rv)} | {_money(ov)} |")
    L.append("")
    return "\n".join(L)


def selftest():
    companies = store.read_all_companies()
    idx = build_index(companies)
    ids = {c.id for c in companies}

    def resolve(name, oid=""):
        return match({"name": name, "openpitch_id": oid}, companies, idx)

    if "anysphere" in ids:
        assert resolve("Cursor") and resolve("Cursor").id == "anysphere", "Cursor→anysphere failed"
        assert resolve("Anysphere").id == "anysphere", "Anysphere→anysphere failed"
    if "openai" in ids:
        assert resolve("OpenAI").id == "openai", "OpenAI→openai failed"
    if "mistral" in ids:
        assert resolve("Mistral AI").id == "mistral", "Mistral AI→mistral failed"
    # openpitch_id wins even with a mismatched display name
    if "openai" in ids:
        assert resolve("Totally Different Name", "openai").id == "openai", "id-priority failed"
    # an unknown name resolves to nothing
    assert resolve("Zzz Nonexistent Co 999") is None, "unknown should be None"
    print("selftest ok")


def main():
    if "--selftest" in sys.argv:
        selftest()
        return
    if not REFERENCE.exists():
        print(f"No reference fixture at {REFERENCE}", file=sys.stderr)
        sys.exit(1)
    r = evaluate()
    report = render(r)
    REPORT.write_text(report)
    print(report)
    print(f"\n[written] {REPORT}")


if __name__ == "__main__":
    main()
