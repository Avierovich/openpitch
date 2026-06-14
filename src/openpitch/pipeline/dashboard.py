"""Static dashboard generator (FRD §9) — pre-rendered company cards, no backend.

Reads the committed data and writes self-contained HTML into dashboard/dist/ that
opens with zero setup (LAUNCH-GATES demo readiness). Also writes the A2A Agent
Card to dist/.well-known/agent.json (FRD §8.7).
"""

from __future__ import annotations

import json
from datetime import date

from .. import store
from ..paths import REPO_ROOT

DIST = REPO_ROOT / "dashboard" / "dist"

_CSS = """
:root{--bg:#0f1320;--card:#171c2e;--fg:#e8ecf5;--mut:#9aa3b8;--acc:#2e7d6f;--warn:#e3b341}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 -apple-system,Segoe UI,Roboto,sans-serif}
a{color:#7fd1c1;text-decoration:none}.wrap{max-width:1000px;margin:0 auto;padding:32px 20px}
h1{font-size:26px;margin:0 0 4px}.sub{color:var(--mut);margin:0 0 24px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px}
.card{background:var(--card);border:1px solid #232a40;border-radius:12px;padding:16px}
.card h3{margin:0 0 2px;font-size:17px}.cat{color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.04em}
.m{display:flex;justify-content:space-between;border-top:1px solid #232a40;padding:7px 0;font-size:14px}
.m .k{color:var(--mut)}.v{font-variant-numeric:tabular-nums}
.tag{display:inline-block;background:#202840;color:var(--mut);border-radius:6px;padding:1px 7px;font-size:11px;margin-left:6px}
.warn{color:var(--warn)}.conf{font-size:11px;color:var(--mut)}
.src{font-size:12px;color:var(--mut)}.disc{background:#1c1530;border:1px solid #3a2a52;border-radius:10px;padding:12px;color:#cbb8e6;font-size:13px;margin:18px 0}
"""


def _money(v) -> str:
    try:
        v = float(v)
    except (TypeError, ValueError):
        return str(v)
    for unit, d in (("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if abs(v) >= d:
            return f"${v / d:.1f}{unit}"
    return f"{v:,.0f}"


def _band(c: float) -> str:
    return "high" if c >= 0.75 else "medium" if c >= 0.5 else "low"


def _company_card(c) -> str:
    rows = ""
    for m, rv in c.metrics.items():
        warn = ' <span class="warn" title="public-source discrepancy">⚑</span>' if rv.contradiction else ""
        val = _money(rv.value) if rv.unit == "USD" else f"{rv.value:,.0f}" if isinstance(rv.value, (int, float)) else rv.value
        rows += (f'<div class="m"><span class="k">{m}{warn}</span>'
                 f'<span class="v">{val} <span class="conf">[{rv.estimate_type.value} · {_band(rv.confidence)}]</span></span></div>')
    return (f'<a class="card" href="company/{c.id}.html"><div class="cat">{c.category or ""} · #{c.universe_rank}</div>'
            f'<h3>{c.name}</h3>{rows}</a>')


def _company_page(c) -> str:
    blocks = ""
    for m, rv in c.metrics.items():
        srcs = ""
        for cl in store.read_claims(c.id):
            if cl.metric == m and cl.source.type.value != "derived":
                link = f'<a href="{cl.source.url}">{cl.source.name}</a>' if cl.source.url else cl.source.name
                srcs += f'<div class="src">↳ {link} · {cl.source.type.value} · {cl.source.published_at or "n.d."} — "{cl.raw_text}"</div>'
        warn = ' <span class="warn">⚑ public-source discrepancy</span>' if rv.contradiction else ""
        val = _money(rv.value) if rv.unit == "USD" else (f"{rv.value:,.0f}" if isinstance(rv.value, (int, float)) else rv.value)
        blocks += (f'<div class="card"><div class="m"><span class="k">{m}{warn}</span>'
                   f'<span class="v">{val} <span class="conf">[{rv.estimate_type.value} · conf {rv.confidence}]</span></span></div>{srcs}</div>')
    return _html(f"{c.name} — OpenPitch", f'<a href="../index.html">← all companies</a><h1>{c.name}</h1>'
                 f'<p class="sub">{c.category or ""} · rank #{c.universe_rank} · VC-attention {c.vc_attention_score}</p>'
                 f'<div class="grid">{blocks}</div>{_DISCLAIMER}')


_DISCLAIMER = ('<div class="disc">OpenPitch is public-source, probabilistic intelligence — '
               'every figure carries its source and confidence. Not audited data, not investment advice. '
               'Seed figures are illustrative pending verification. See methodology &amp; corrections.</div>')


def _html(title: str, body: str) -> str:
    return f"<!doctype html><html><head><meta charset=utf-8><title>{title}</title><style>{_CSS}</style></head><body><div class=wrap>{body}</div></body></html>"


def _agent_card() -> dict:
    return {
        "name": "OpenPitch",
        "description": "Free, open, sourced & confidence-scored intelligence on AI startups.",
        "version": "0.1",
        "skills": [
            {"id": "research_company", "description": "Return a company's sourced metrics with confidence."},
            {"id": "compare_companies", "description": "Compare metrics across companies."},
            {"id": "whats_moved", "description": "Report material changes and contradictions."},
            {"id": "find_contradictions", "description": "Surface public-source discrepancies."},
        ],
        "capabilities": {"streaming": False},
        "provenance": "Every numeric answer includes sources and confidence.",
    }


def build() -> str:
    companies = sorted(store.read_all_companies(), key=lambda c: c.universe_rank or 1e9)
    (DIST / "company").mkdir(parents=True, exist_ok=True)
    (DIST / ".well-known").mkdir(parents=True, exist_ok=True)

    cards = "".join(_company_card(c) for c in companies)
    index = _html(
        "OpenPitch — AI-startup intelligence",
        f'<h1>OpenPitch</h1><p class="sub">Free, open, sourced AI-startup intelligence · '
        f'{len(companies)} companies · updated {date.today()}</p>{_DISCLAIMER}<div class="grid">{cards}</div>',
    )
    (DIST / "index.html").write_text(index)
    for c in companies:
        (DIST / "company" / f"{c.id}.html").write_text(_company_page(c))
    (DIST / ".well-known" / "agent.json").write_text(json.dumps(_agent_card(), indent=2))
    return str(DIST)
