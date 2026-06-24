"""Static dashboard generator (FRD §9) — pre-rendered company cards, no backend.

Reads the committed data and writes self-contained HTML into dashboard/dist/ that
opens with zero setup (LAUNCH-GATES demo readiness). Also writes the A2A Agent
Card to dist/.well-known/agent.json (FRD §8.7).
"""

from __future__ import annotations

from html import escape
import json
from datetime import date

from .. import store
from ..config import load_metrics, load_scoring, load_watchlist
from ..paths import REPO_ROOT
from .quality import render_html, write_report

DIST = REPO_ROOT / "dashboard" / "dist"

_CSS = """
:root{--bg:#0f1320;--card:#171c2e;--fg:#e8ecf5;--mut:#9aa3b8;--acc:#2e7d6f;--warn:#e3b341}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 -apple-system,Segoe UI,Roboto,sans-serif}
a{color:#7fd1c1;text-decoration:none}.wrap{max-width:1000px;margin:0 auto;padding:32px 20px}
h1{font-size:26px;margin:0 0 4px}.sub{color:var(--mut);margin:0 0 24px}
.toolbar{display:flex;gap:10px;align-items:center;justify-content:space-between;margin:0 0 14px;flex-wrap:wrap}
.toolbar label{color:var(--mut);font-size:13px}.toolbar select{background:#171c2e;color:var(--fg);border:1px solid #303852;border-radius:6px;padding:7px 10px}
.quality{display:flex;gap:10px;align-items:center;justify-content:space-between;background:#141929;border:1px solid #303852;border-radius:8px;padding:10px 12px;margin:0 0 14px;color:var(--mut);font-size:13px}
.quality strong{color:var(--fg)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px}
.card{display:block;background:var(--card);border:1px solid #232a40;border-radius:12px;padding:16px}
.pending{border-style:dashed;background:#141929}
.card h3{margin:0 0 2px;font-size:17px}.cat{color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.04em}
.card h3 .name{color:var(--fg)}.card h3 .name:hover{color:#7fd1c1;text-decoration:underline}
.more{display:inline-block;margin-top:10px;font-size:12px;color:var(--mut)}.more:hover{color:#7fd1c1}
.m{display:flex;justify-content:space-between;border-top:1px solid #232a40;padding:7px 0;font-size:14px}
.m .k{color:var(--mut)}.v{font-variant-numeric:tabular-nums}
.tag{display:inline-block;background:#202840;color:var(--mut);border-radius:6px;padding:1px 7px;font-size:11px;margin-left:6px}
.warn{color:var(--warn)}.conf{font-size:11px;color:var(--mut)}
.rumor{font-size:10px;color:#e3b341;border:1px solid #5c4a1a;border-radius:4px;padding:0 4px;vertical-align:middle}
.confirmed{font-size:11px;color:#7fd1c1}
.yr{font-size:11px;color:var(--mut);margin-left:5px;font-variant-numeric:tabular-nums}
.yr.old{color:#1a1205;background:var(--warn);font-weight:700;border-radius:4px;padding:0 5px}
.src{font-size:12px;color:var(--mut)}.disc{background:#1c1530;border:1px solid #3a2a52;border-radius:10px;padding:12px;color:#cbb8e6;font-size:13px;margin:18px 0}
"""

_JS = """
<script>
const grid = document.querySelector('[data-grid]');
const sort = document.querySelector('[data-sort]');
const number = (card, key) => Number(card.dataset[key] || 0);
const text = (card, key) => (card.dataset[key] || '').toLowerCase();
function compareCards(mode, a, b) {
  if (mode === 'name') return text(a, 'name').localeCompare(text(b, 'name'));
  if (mode === 'category') return text(a, 'category').localeCompare(text(b, 'category')) || number(a, 'rank') - number(b, 'rank');
  if (mode === 'funding') return number(b, 'funding') - number(a, 'funding') || number(a, 'rank') - number(b, 'rank');
  if (mode === 'revenue') return number(b, 'revenue') - number(a, 'revenue') || number(a, 'rank') - number(b, 'rank');
  if (mode === 'coverage') return number(b, 'coverage') - number(a, 'coverage') || number(a, 'rank') - number(b, 'rank');
  return number(b, 'valuation') - number(a, 'valuation') || number(a, 'rank') - number(b, 'rank');
}
function applySort() {
  [...grid.children].sort((a, b) => compareCards(sort.value, a, b)).forEach(card => grid.appendChild(card));
}
if (grid && sort) {
  sort.addEventListener('change', applySort);
  applySort();
}
</script>
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
    # "stale" (<0.05) distinguishes a figure decayed to near-zero trust from a
    # merely-uncertain "low" one, so an old single-source number can't read as current.
    if c < 0.05:
        return "stale"
    return "high" if c >= 0.75 else "medium" if c >= 0.5 else "low"


CURRENT_YEAR = date.today().year


def _status_html(rv) -> str:
    """Differentiate a fresh 'in talks' mark from the last confirmed figure, so
    recency (the headline) and credibility (the confirmed anchor) both show."""
    out = ""
    if getattr(rv, "unconfirmed", False):
        out += ' <span class="rumor" title="reported in talks / not yet closed">in talks</span>'
    cv = getattr(rv, "confirmed_value", None)
    if cv:
        cy = f" '{str(rv.confirmed_as_of)[2:4]}" if getattr(rv, "confirmed_as_of", None) else ""
        out += f' <span class="confirmed">· {_money(cv)} confirmed{cy}</span>'
    return out


def _site_url(website: str | None) -> str:
    """Normalize a stored domain (e.g. 'openai.com') to a full URL, or '' if none."""
    w = (website or "").strip()
    if not w:
        return ""
    return w if w.startswith(("http://", "https://")) else f"https://{w}"


def _year_badge(as_of) -> str:
    """Show the data point's year; highlight it (amber) when older than the current
    year — in startup valuations a figure from a prior year is materially stale."""
    yr = str(as_of)[:4] if as_of else ""
    if not (yr.isdigit()):
        return ""
    cls = "yr old" if int(yr) < CURRENT_YEAR else "yr"
    title = f"as of {as_of} — older than {CURRENT_YEAR}" if int(yr) < CURRENT_YEAR else f"as of {as_of}"
    return f'<span class="{cls}" title="{title}">{yr}</span>'


def _metric_label(key: str) -> str:
    defs = load_metrics()
    return defs[key].label if key in defs else key.replace("_", " ").title()


def _tier(rank: int | None) -> str:
    if not rank:
        return "Watchlist"
    if rank <= 10:
        return "Tier 1"
    if rank <= 25:
        return "Tier 2"
    if rank <= 50:
        return "Tier 3"
    return "Watchlist"


def _display_rank(rank: int) -> str:
    return f"#{rank}" if rank <= 50 else "watchlist"


def _metric_number(c, metric: str) -> float:
    rv = c.metrics.get(metric)
    return float(rv.value) if rv and isinstance(rv.value, (int, float)) else 0.0


def _coverage(c) -> int:
    return len(c.metrics)


def _card_attrs(*, rank: int, name: str, category: str | None, valuation=0.0, funding=0.0, revenue=0.0, coverage=0) -> str:
    return (
        f'data-rank="{rank}" data-name="{escape(name, quote=True)}" '
        f'data-category="{escape(category or "", quote=True)}" '
        f'data-valuation="{valuation}" data-funding="{funding}" data-revenue="{revenue}" data-coverage="{coverage}"'
    )


def _company_card(c, display_rank: int | None = None) -> str:
    rank = display_rank or c.universe_rank
    rows = ""
    for m, rv in c.metrics.items():
        warn = ' <span class="warn" title="public-source discrepancy">⚑</span>' if rv.contradiction else ""
        val = _money(rv.value) if rv.unit == "USD" else f"{rv.value:,.0f}" if isinstance(rv.value, (int, float)) else rv.value
        rows += (f'<div class="m"><span class="k">{_metric_label(m)}{warn}</span>'
                 f'<span class="v">{val}{_status_html(rv)} <span class="conf">[{rv.estimate_type.value} · {_band(rv.confidence)}]</span>'
                 f'{_year_badge(rv.as_of)}</span></div>')
    if not rows:
        rows = '<div class="m"><span class="k">Coverage status</span><span class="v">source checked; no metric claims yet</span></div>'
    attrs = _card_attrs(
        rank=rank or 9999, name=c.name, category=c.category,
        valuation=_metric_number(c, "valuation"), funding=_metric_number(c, "total_funding"),
        revenue=_metric_number(c, "arr"), coverage=_coverage(c),
    )
    name = escape(c.name)
    site = _site_url(c.website)
    name_html = (
        f'<a class="name" href="{escape(site, quote=True)}" target="_blank" rel="noopener noreferrer">{name}</a>'
        if site else name
    )
    return (f'<div class="card" {attrs}>'
            f'<div class="cat">{_tier(rank)} · {escape(c.category or "")} · {_display_rank(rank or 0)}</div>'
            f'<h3>{name_html}</h3>{rows}'
            f'<a class="more" href="company/{escape(c.id, quote=True)}.html">sources &amp; history →</a></div>')


def _pending_card(meta: dict, display_rank: int) -> str:
    domain = meta.get("domain")
    url = _site_url(domain)
    site = f'<a href="{escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">{escape(domain)}</a>' if url else "domain pending"
    name = escape(meta["name"])
    name_html = (
        f'<a class="name" href="{escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">{name}</a>'
        if url else name
    )
    attrs = _card_attrs(rank=display_rank, name=meta["name"], category=meta.get("category"))
    return (
        f'<article class="card pending" {attrs}><div class="cat">{_tier(display_rank)} · {escape(meta.get("category") or "")} · #{display_rank}</div>'
        f'<h3>{name_html}</h3>'
        f'<div class="m"><span class="k">Coverage status</span><span class="v">pending sourced metrics</span></div>'
        f'<div class="src">{site}</div></article>'
    )


def _company_page(c, display_rank: int | None = None) -> str:
    rank = display_rank or c.universe_rank
    blocks = ""
    for m, rv in c.metrics.items():
        srcs = ""
        for cl in store.read_claims(c.id):
            if cl.metric == m and cl.source.type.value != "derived":
                link = f'<a href="{cl.source.url}">{cl.source.name}</a>' if cl.source.url else cl.source.name
                srcs += f'<div class="src">↳ {link} · {cl.source.type.value} · {cl.source.published_at or "n.d."} — "{cl.raw_text}"</div>'
        warn = ' <span class="warn">⚑ public-source discrepancy</span>' if rv.contradiction else ""
        val = _money(rv.value) if rv.unit == "USD" else (f"{rv.value:,.0f}" if isinstance(rv.value, (int, float)) else rv.value)
        blocks += (f'<div class="card"><div class="m"><span class="k">{_metric_label(m)}{warn}</span>'
                   f'<span class="v">{val}{_status_html(rv)} <span class="conf">[{rv.estimate_type.value} · conf {rv.confidence}]</span>'
                   f'{_year_badge(rv.as_of)}</span></div>{srcs}</div>')
    return _html(f"{c.name} — OpenPitch", f'<a href="../index.html">← all companies</a><h1>{c.name}</h1>'
                 f'<p class="sub">{_tier(rank)} · {c.category or ""} · rank {_display_rank(rank or 0)} · VC-attention {c.vc_attention_score}</p>'
                 f'<div class="grid">{blocks}</div>{_DISCLAIMER}')


_DISCLAIMER = ('<div class="disc">OpenPitch is public-source, probabilistic intelligence — '
               'every figure carries its source and confidence. Not audited data, not investment advice. '
               'Seed figures are illustrative pending verification. See methodology &amp; corrections.</div>')


def _html(title: str, body: str) -> str:
    return f"<!doctype html><html><head><meta charset=utf-8><title>{title}</title><style>{_CSS}</style></head><body><div class=wrap>{body}</div>{_JS}</body></html>"


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
    quality = write_report()
    # Fail loud rather than silently shipping an empty-looking dashboard. If a read
    # comes up short (e.g. racing a concurrent `run` that's rewriting data/, or a
    # corrupt file), abort instead of overwriting a good dashboard with a near-empty
    # "all pending" one. Atomic writes (store.atomic_write_text) make this rare, but
    # this is the last-resort guard the symptom demands.
    company_ids = store.list_company_ids()
    companies_raw = store.read_all_companies()
    if len(companies_raw) < len(company_ids):
        raise RuntimeError(
            f"Aborting dashboard build: read {len(companies_raw)} of {len(company_ids)} "
            "company files — data/ looks mid-write or corrupt. Re-run after writes settle."
        )
    prev_selected = (store.read_universe() or {}).get("selected", [])
    loaded_in_universe = sum(1 for c in companies_raw if c.in_universe)
    if prev_selected and loaded_in_universe < len(prev_selected) // 2:
        raise RuntimeError(
            f"Aborting dashboard build: only {loaded_in_universe} in-universe companies "
            f"loaded but universe.json selects {len(prev_selected)} — likely a transient "
            "partial read. Re-run."
        )
    companies = sorted(
        companies_raw,
        key=lambda c: (-_metric_number(c, "valuation"), c.universe_rank or 1e9, c.name),
    )
    universe_size = int(load_scoring().get("universe_size", 50))
    sourced_ids = {c.id for c in companies}
    display_companies = [(rank, c) for rank, c in enumerate(companies[:universe_size], start=1)]
    next_rank = len(display_companies) + 1
    pending = []
    for meta in load_watchlist():
        if next_rank > universe_size:
            break
        if meta["id"] in sourced_ids:
            continue
        pending.append((next_rank, meta))
        next_rank += 1

    (DIST / "company").mkdir(parents=True, exist_ok=True)
    (DIST / ".well-known").mkdir(parents=True, exist_ok=True)

    cards = "".join(_company_card(c, rank) for rank, c in display_companies)
    cards += "".join(_pending_card(meta, rank) for rank, meta in pending)
    index = _html(
        "OpenPitch — AI-startup intelligence",
        f'<h1>OpenPitch</h1><p class="sub">Free, open, sourced AI-startup intelligence · '
        f'{len(display_companies)} sourced profiles · {len(display_companies) + len(pending)} top-50 slots · updated {date.today()}</p>'
        f'{_DISCLAIMER}<div class="quality"><span><strong>{quality.critical_count}</strong> critical quality issues · '
        f'<strong>{quality.warning_count}</strong> warnings</span><a href="quality.html">View data quality</a></div>'
        f'<div class="toolbar"><label for="sort">Sort</label><select id="sort" data-sort>'
        f'<option value="valuation" selected>Valuation</option><option value="revenue">Revenue (ARR)</option><option value="funding">Total funding</option>'
        f'<option value="coverage">Source coverage</option><option value="category">Category</option><option value="name">Name</option>'
        f'</select></div><div class="grid" data-grid>{cards}</div>',
    )
    store.atomic_write_text(DIST / "index.html", index)
    for rank, c in display_companies:
        store.atomic_write_text(DIST / "company" / f"{c.id}.html", _company_page(c, rank))
    store.atomic_write_text(DIST / ".well-known" / "agent.json", json.dumps(_agent_card(), indent=2))
    store.atomic_write_text(DIST / "quality.html", render_html(quality))
    return str(DIST)
