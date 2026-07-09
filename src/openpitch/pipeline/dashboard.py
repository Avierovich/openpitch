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
.cat .sub{color:#7fd1c1}
.desc{margin:2px 0 10px;color:var(--mut);font-size:13px;line-height:1.45}
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
.rangebar,.spark{vertical-align:middle;margin-left:6px}
.maplink{margin-left:auto;font-size:13px}
.map{display:flex;flex-direction:column;gap:8px;margin:18px 0}
.maprow{display:grid;grid-template-columns:minmax(160px,240px) 1fr;gap:12px;align-items:center}
.maplabel{color:var(--mut);font-size:13px}
.maptrack{background:#141929;border:1px solid #232a40;border-radius:6px;height:20px;overflow:hidden}
.mapbar{background:var(--acc);height:100%;min-width:2px}
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
const filter = document.querySelector('[data-filter]');
function applyFilter() {
  const v = filter ? filter.value : '';
  [...grid.children].forEach(card => {
    const cat = text(card, 'category'), sub = text(card, 'subcategory');
    card.style.display = (!v || v === cat || v === cat + '/' + sub) ? '' : 'none';
  });
}
function applySort() {
  [...grid.children].sort((a, b) => compareCards(sort.value, a, b)).forEach(card => grid.appendChild(card));
  applyFilter();
}
if (grid && sort) {
  sort.addEventListener('change', applySort);
  if (filter) filter.addEventListener('change', applyFilter);
  applySort();
}
</script>
"""


def _money(v) -> str:
    try:
        v = float(v)
    except (TypeError, ValueError):
        return str(v)
    for unit, d in (("T", 1e12), ("B", 1e9), ("M", 1e6), ("K", 1e3)):
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


_BAND_FILL = {"high": "#2e7d6f", "medium": "#5a6b8c", "low": "#6b5a3a", "stale": "#3a3a44"}


def _range_bar(rv) -> str:
    """Tiny low—consensus—high SVG bar: makes the probabilistic RANGE visible (the
    differentiator), not just the point estimate. Empty unless a real spread exists."""
    r = getattr(rv, "range", None)
    if not r or not isinstance(getattr(r, "low", None), (int, float)) \
            or not isinstance(getattr(r, "high", None), (int, float)):
        return ""
    lo, hi = float(r.low), float(r.high)
    val = float(rv.value) if isinstance(rv.value, (int, float)) else None
    if hi <= lo or val is None:
        return ""
    w = 120
    x = round(max(0.0, min(1.0, (val - lo) / (hi - lo))) * w, 1)
    fill = _BAND_FILL.get(_band(rv.confidence), "#5a6b8c")
    tip = f"range {_money(lo)}–{_money(hi)} · consensus {_money(val)} · as of {rv.as_of}"
    return (f'<svg class="rangebar" width="{w}" height="8" viewBox="0 0 {w} 8" role="img" '
            f'aria-label="{escape(tip, quote=True)}"><title>{escape(tip)}</title>'
            f'<rect x="0" y="3" width="{w}" height="2" rx="1" fill="{fill}" opacity="0.5"/>'
            f'<rect x="{x - 1}" y="0" width="2" height="8" rx="1" fill="{fill}"/></svg>')


def _sparkline(company_id: str, metric: str) -> str:
    """Value-over-time polyline from committed history — makes freshness / the
    git-as-audit-log claim visible. Empty unless ≥2 tracked points."""
    # One point per distinct date (history can repeat a value); newest wins per day.
    by_day = {str(r.get("as_of", "")): r.get("value")
              for r in store.read_history(company_id, metric)
              if isinstance(r.get("value"), (int, float)) and r.get("as_of")}
    pts = sorted(by_day.items())
    vals = [v for _, v in pts]
    # Skip a flat/degenerate series — a single tracked value on one date is not a
    # trajectory, and a flat line reads as "broken" rather than "stable".
    if len(pts) < 2 or max(vals) == min(vals):
        return ""
    lo, span = min(vals), (max(vals) - min(vals)) or 1
    w, h, n = 120, 24, len(pts)
    coords = " ".join(f"{round(i / (n - 1) * w, 1)},{round(h - 2 - (v - lo) / span * (h - 4), 1)}"
                      for i, (_, v) in enumerate(pts))
    trend = "#7fd1c1" if vals[-1] >= vals[0] else "#e3b341"
    tip = f"{metric}: {_money(vals[0])} ({pts[0][0]}) → {_money(vals[-1])} ({pts[-1][0]})"
    return (f'<svg class="spark" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" '
            f'aria-label="{escape(tip, quote=True)}"><title>{escape(tip)}</title>'
            f'<polyline fill="none" stroke="{trend}" stroke-width="1.5" points="{coords}"/></svg>')


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


def _card_attrs(*, rank: int, name: str, category: str | None, subcategory: str | None = None,
                valuation=0.0, funding=0.0, revenue=0.0, coverage=0) -> str:
    return (
        f'data-rank="{rank}" data-name="{escape(name, quote=True)}" '
        f'data-category="{escape(category or "", quote=True)}" '
        f'data-subcategory="{escape(subcategory or "", quote=True)}" '
        f'data-valuation="{valuation}" data-funding="{funding}" data-revenue="{revenue}" data-coverage="{coverage}"'
    )


def _taxon_label(category: str | None, subcategory: str | None) -> str:
    """'generative-media · video' — the differentiating two-level label."""
    main = escape(category or "")
    return f'{main} · <span class="sub">{escape(subcategory)}</span>' if subcategory else main


def _company_card(c, display_rank: int | None = None) -> str:
    rank = display_rank or c.universe_rank
    rows = ""
    for m, rv in c.metrics.items():
        warn = ' <span class="warn" title="public-source discrepancy">⚑</span>' if rv.contradiction else ""
        val = _money(rv.value) if rv.unit == "USD" else f"{rv.value:,.0f}" if isinstance(rv.value, (int, float)) else rv.value
        rows += (f'<div class="m"><span class="k">{_metric_label(m)}{warn}</span>'
                 f'<span class="v">{val}{_status_html(rv)} <span class="conf">[{rv.estimate_type.value} · {_band(rv.confidence)}]</span>'
                 f'{_year_badge(rv.as_of)}{_range_bar(rv)}</span></div>')
    if not rows:
        rows = '<div class="m"><span class="k">Coverage status</span><span class="v">source checked; no metric claims yet</span></div>'
    attrs = _card_attrs(
        rank=rank or 9999, name=c.name, category=c.category, subcategory=c.subcategory,
        valuation=_metric_number(c, "valuation"), funding=_metric_number(c, "total_funding"),
        revenue=_metric_number(c, "arr"), coverage=_coverage(c),
    )
    name = escape(c.name)
    site = _site_url(c.website)
    title = f' title="{escape(c.specialty, quote=True)}"' if c.specialty else ""
    name_html = (
        f'<a class="name" href="{escape(site, quote=True)}" target="_blank" rel="noopener noreferrer">{name}</a>'
        if site else name
    )
    desc = f'<p class="desc">{escape(c.summary)}</p>' if c.summary else ""
    return (f'<div class="card" {attrs}{title}>'
            f'<div class="cat">{_tier(rank)} · {_taxon_label(c.category, c.subcategory)} · {_display_rank(rank or 0)}</div>'
            f'<h3>{name_html}</h3>{desc}{rows}'
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
    attrs = _card_attrs(rank=display_rank, name=meta["name"], category=meta.get("category"),
                        subcategory=meta.get("subcategory"))
    return (
        f'<article class="card pending" {attrs}><div class="cat">{_tier(display_rank)} · {_taxon_label(meta.get("category"), meta.get("subcategory"))} · #{display_rank}</div>'
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
                # Escape everything crawled/LLM-produced (name, url, raw_text) — this page
                # ships to public Pages, and a crafted article must not inject markup.
                sname = escape(cl.source.name)
                url = cl.source.url or ""
                link = (f'<a href="{escape(url, quote=True)}">{sname}</a>'
                        if url.startswith(("http://", "https://")) else sname)
                srcs += f'<div class="src">↳ {link} · {cl.source.type.value} · {cl.source.published_at or "n.d."} — "{escape(cl.raw_text)}"</div>'
        warn = ' <span class="warn">⚑ public-source discrepancy</span>' if rv.contradiction else ""
        val = _money(rv.value) if rv.unit == "USD" else (f"{rv.value:,.0f}" if isinstance(rv.value, (int, float)) else rv.value)
        blocks += (f'<div class="card"><div class="m"><span class="k">{_metric_label(m)}{warn}</span>'
                   f'<span class="v">{val}{_status_html(rv)} <span class="conf">[{rv.estimate_type.value} · conf {rv.confidence}]</span>'
                   f'{_year_badge(rv.as_of)}{_range_bar(rv)}{_sparkline(c.id, m)}</span></div>{srcs}</div>')
    return _html(f"{escape(c.name)} — OpenPitch", f'<a href="../index.html">← all companies</a><h1>{escape(c.name)}</h1>'
                 f'<p class="sub">{_tier(rank)} · {_taxon_label(c.category, c.subcategory)}{(" · " + escape(c.specialty)) if c.specialty else ""} · rank {_display_rank(rank or 0)} · VC-attention {c.vc_attention_score}</p>'
                 f'{("<p class=" + chr(34) + "desc" + chr(34) + ">" + escape(c.summary) + "</p>") if c.summary else ""}'
                 f'<div class="grid">{blocks}</div>{_DISCLAIMER}')


_DISCLAIMER = ('<div class="disc">OpenPitch is public-source, probabilistic intelligence — '
               'every figure carries its source, confidence, and date, refreshed daily. '
               'Not audited data, not investment advice. See methodology &amp; corrections.</div>')


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


def _market_map(companies) -> str:
    """Total tracked valuation by sector — the VC 'market map'. Hand-rolled SVG-free bars
    (pure CSS widths), dependency-free. Sums only companies with a resolved valuation."""
    from statistics import median
    agg: dict[str, dict] = {}
    for c in companies:
        v = _metric_number(c, "valuation")
        if v <= 0:
            continue
        d = agg.setdefault(c.category or "other", {"val": 0.0, "n": 0, "conf": []})
        d["val"] += v
        d["n"] += 1
        rv = c.metrics.get("valuation")
        if rv:
            d["conf"].append(rv.confidence)
    rows = sorted(agg.items(), key=lambda kv: -kv[1]["val"])
    if not rows:
        body = "<p>No resolved valuations yet.</p>"
    else:
        maxv = rows[0][1]["val"] or 1
        bars = ""
        for cat, d in rows:
            w = round(d["val"] / maxv * 100, 1)
            mc = median(d["conf"]) if d["conf"] else 0.0
            label = f'{escape(cat)} · {_money(d["val"])} · {d["n"]} cos'
            bars += (f'<div class="maprow"><div class="maplabel">{label}</div>'
                     f'<div class="maptrack"><div class="mapbar" style="width:{w}%" '
                     f'title="median confidence {mc:.2f}"></div></div></div>')
        body = f'<div class="map">{bars}</div>'
    return _html(
        "OpenPitch — AI market map",
        f'<a href="index.html">← all companies</a><h1>Market map</h1>'
        f'<p class="sub">Total tracked valuation by sector · updated {date.today()}</p>'
        f'{body}<p class="src">Sums only companies with a resolved valuation; each figure is '
        f'an OpenPitch consensus estimate, not an official market total.</p>{_DISCLAIMER}')


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

    # Filter dropdown options, grouped main → subcategories, from what's on the page.
    taxa: dict[str, set] = {}
    for _, c in display_companies:
        if c.category:
            taxa.setdefault(c.category, set()).add(c.subcategory or "")
    for _, meta in pending:
        if meta.get("category"):
            taxa.setdefault(meta["category"], set()).add(meta.get("subcategory") or "")
    opts = ['<option value="">All categories</option>']
    for main in sorted(taxa):
        opts.append(f'<optgroup label="{escape(main)}"><option value="{escape(main, quote=True)}">{escape(main)} — all</option>')
        for sub in sorted(s for s in taxa[main] if s):
            opts.append(f'<option value="{escape(main + "/" + sub, quote=True)}">↳ {escape(sub)}</option>')
        opts.append("</optgroup>")
    filter_html = (f'<label for="filter">Filter</label><select id="filter" data-filter>{"".join(opts)}</select>')
    index = _html(
        "OpenPitch — AI-startup intelligence",
        f'<h1>OpenPitch</h1><p class="sub">Free, open, sourced AI-startup intelligence · '
        f'{quality.total_profiles} companies profiled · top {len(display_companies) + len(pending)} ranked below · updated {date.today()}</p>'
        f'{_DISCLAIMER}<div class="quality"><span>Data-quality report: <strong>{quality.critical_count + quality.warning_count}</strong> '
        f'open items tracked in public</span><a href="quality.html">View data quality</a></div>'
        f'<div class="toolbar"><label for="sort">Sort</label><select id="sort" data-sort>'
        f'<option value="valuation" selected>Valuation</option><option value="revenue">Revenue (ARR)</option><option value="funding">Total funding</option>'
        f'<option value="coverage">Source coverage</option><option value="category">Category</option><option value="name">Name</option>'
        f'</select>{filter_html}<a class="maplink" href="market.html">Market map →</a></div>'
        f'<div class="grid" data-grid>{cards}</div>',
    )
    store.atomic_write_text(DIST / "index.html", index)
    store.atomic_write_text(DIST / "market.html", _market_map(companies))
    for rank, c in display_companies:
        store.atomic_write_text(DIST / "company" / f"{c.id}.html", _company_page(c, rank))
    store.atomic_write_text(DIST / ".well-known" / "agent.json", json.dumps(_agent_card(), indent=2))
    store.atomic_write_text(DIST / "quality.html", render_html(quality))
    return str(DIST)
