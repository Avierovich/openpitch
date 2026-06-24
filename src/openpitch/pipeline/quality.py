"""Data-quality report for dashboard/readiness review.

The report is intentionally simple and deterministic: it reads the generated
company JSON plus the watchlist and surfaces coverage gaps before a dashboard is
treated as credible.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from html import escape

from .. import store
from ..config import load_watchlist
from ..paths import data_dir


CORE_METRICS = ("valuation", "arr", "total_funding", "round_amount", "headcount")
HIGH_PRIORITY_CATEGORIES = {
    "foundation-model",
    "ai-infra",
    "coding-agent",
    "enterprise-ai",
    "vertical-app",
    "data-eval",
    "generative-media",
    "robotics",
}
# Categories where ARR is the expected headline metric and usually disclosed.
# Frontier labs, infra/chips, robotics and defense rarely publish ARR, so a
# missing ARR there is reality — not a fixable quality gap — and shouldn't warn.
ARR_EXPECTED_CATEGORIES = {
    "vertical-app",
    "enterprise-ai",
    "ai-agents",
    "coding-agent",
    "data-eval",
    "generative-media",
}


@dataclass(frozen=True)
class QualitySnapshot:
    generated_at: date
    total_profiles: int
    watchlist_size: int
    top50_size: int
    profiles_with_metrics: int
    top50_missing_valuation: list[str]
    top50_missing_arr: list[str]
    top50_no_metrics: list[str]
    unprofiled_high_priority: list[str]
    single_source_metrics: list[str]

    @property
    def critical_count(self) -> int:
        return len(self.top50_no_metrics) + len(self.unprofiled_high_priority)

    @property
    def warning_count(self) -> int:
        return (
            len(self.top50_missing_valuation)
            + len(self.top50_missing_arr)
            + len(self.single_source_metrics)
        )


def _metric_number(company, metric: str) -> float:
    rv = company.metrics.get(metric)
    return float(rv.value) if rv and isinstance(rv.value, (int, float)) else 0.0


def _ranked_companies():
    return sorted(
        store.read_all_companies(),
        key=lambda c: (-_metric_number(c, "valuation"), -_metric_number(c, "arr"), c.name),
    )


def _claim_source_count(company_id: str, metric: str) -> int:
    sources = set()
    for claim in store.read_claims(company_id):
        if claim.metric == metric and claim.source.type.value != "derived":
            sources.add((claim.source.name, claim.source.url, claim.source.published_at))
    return len(sources)


# Tier-1 outlets whose single report of a funding figure is reliable on its own —
# a lone story here is not a corroboration gap (same spirit as a lone filing).
TRUSTED_OUTLETS = (
    "bloomberg", "reuters", "cnbc", "wsj", "wall street journal", "techcrunch",
    "the information", "forbes", "fortune", "axios", "financial times",
    "business insider", "crunchbase", "new york times",
)


def _is_trusted_outlet(name: str) -> bool:
    n = (name or "").lower()
    return any(o in n for o in TRUSTED_OUTLETS)


def _under_corroborated(company_id: str, metric: str) -> bool:
    """A metric with <2 distinct public sources — UNLESS its lone source is
    authoritative: a filing (EDGAR), or a single tier-1 outlet (Bloomberg/Reuters/
    TechCrunch/…), which doesn't need a second source to be credible."""
    distinct, types = set(), set()
    for claim in store.read_claims(company_id):
        if claim.metric == metric and claim.source.type.value != "derived":
            distinct.add((claim.source.name, claim.source.url))
            types.add(claim.source.type.value)
    if len(distinct) >= 2:
        return False
    if "filing" in types:
        return False
    lone_name = next(iter(distinct))[0] if distinct else ""
    return not _is_trusted_outlet(lone_name)


def build_snapshot(top_n: int = 50) -> QualitySnapshot:
    companies = _ranked_companies()
    top = companies[:top_n]
    profiled_ids = {c.id for c in companies}
    watchlist = load_watchlist()

    top50_missing_valuation = [c.name for c in top if "valuation" not in c.metrics]
    # Only flag missing ARR where ARR is the expected, usually-disclosed headline
    # metric — not for frontier/infra/robotics/defense where it's rarely public.
    top50_missing_arr = [
        c.name for c in top
        if "arr" not in c.metrics and (c.category or "") in ARR_EXPECTED_CATEGORIES
    ]
    top50_no_metrics = [c.name for c in top if not c.metrics]
    unprofiled_high_priority = [
        meta["name"]
        for meta in watchlist
        if meta["id"] not in profiled_ids and meta.get("category") in HIGH_PRIORITY_CATEGORIES
    ]

    single_source_metrics = []
    for c in top:
        for metric in CORE_METRICS:
            if metric in c.metrics and _under_corroborated(c.id, metric):
                single_source_metrics.append(f"{c.name}: {metric}")

    return QualitySnapshot(
        generated_at=date.today(),
        total_profiles=len(companies),
        watchlist_size=len(watchlist),
        top50_size=len(top),
        profiles_with_metrics=sum(bool(c.metrics) for c in companies),
        top50_missing_valuation=top50_missing_valuation,
        top50_missing_arr=top50_missing_arr,
        top50_no_metrics=top50_no_metrics,
        unprofiled_high_priority=unprofiled_high_priority,
        single_source_metrics=single_source_metrics,
    )


def _section(title: str, items: list[str], empty: str = "None.") -> list[str]:
    lines = [f"## {title}", ""]
    if items:
        lines.extend(f"- {item}" for item in items)
    else:
        lines.append(empty)
    lines.append("")
    return lines


def render_markdown(snapshot: QualitySnapshot) -> str:
    lines = [
        f"# OpenPitch Data Quality Report - {snapshot.generated_at.isoformat()}",
        "",
        "## Summary",
        "",
        f"- Profiles generated: {snapshot.total_profiles}",
        f"- Watchlist candidates: {snapshot.watchlist_size}",
        f"- Top-50 cards: {snapshot.top50_size}",
        f"- Profiles with at least one metric: {snapshot.profiles_with_metrics}",
        f"- Critical issues: {snapshot.critical_count}",
        f"- Warnings: {snapshot.warning_count}",
        "",
    ]
    lines += _section("Top-50 Companies With No Metrics", snapshot.top50_no_metrics)
    lines += _section("Top-50 Missing Valuation", snapshot.top50_missing_valuation)
    lines += _section("Top-50 Missing ARR / Revenue", snapshot.top50_missing_arr)
    lines += _section("High-Priority Watchlist Candidates Not Profiled", snapshot.unprofiled_high_priority)
    lines += _section("Single-Source Core Metrics", snapshot.single_source_metrics)
    lines += [
        "## Review Rule",
        "",
        "Do not treat the dashboard as launch-ready while critical issues remain. "
        "Warnings may be acceptable for early demos if the affected cards show provenance and confidence.",
        "",
    ]
    return "\n".join(lines)


def render_html(snapshot: QualitySnapshot) -> str:
    def list_html(items: list[str]) -> str:
        if not items:
            return "<p>None.</p>"
        return "<ul>" + "".join(f"<li>{escape(item)}</li>" for item in items) + "</ul>"

    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>OpenPitch Data Quality</title>
  <style>
    body{{margin:0;background:#0f1320;color:#e8ecf5;font:15px/1.5 -apple-system,Segoe UI,Roboto,sans-serif}}
    a{{color:#7fd1c1;text-decoration:none}} .wrap{{max-width:960px;margin:0 auto;padding:32px 20px}}
    h1{{font-size:26px;margin:0 0 4px}} h2{{font-size:18px;margin-top:28px}}
    .sub{{color:#9aa3b8;margin:0 0 22px}} .stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px}}
    .stat{{background:#171c2e;border:1px solid #232a40;border-radius:8px;padding:12px}}
    .n{{font-size:24px;font-weight:700}} .k{{color:#9aa3b8;font-size:12px;text-transform:uppercase}}
    li{{margin:5px 0}} .warn{{color:#e3b341}}
  </style>
</head>
<body><div class="wrap">
  <a href="index.html">Back to dashboard</a>
  <h1>OpenPitch Data Quality</h1>
  <p class="sub">Generated {snapshot.generated_at.isoformat()}</p>
  <div class="stats">
    <div class="stat"><div class="n">{snapshot.total_profiles}</div><div class="k">Profiles</div></div>
    <div class="stat"><div class="n">{snapshot.top50_size}</div><div class="k">Top-50 Cards</div></div>
    <div class="stat"><div class="n">{snapshot.critical_count}</div><div class="k">Critical Issues</div></div>
    <div class="stat"><div class="n">{snapshot.warning_count}</div><div class="k">Warnings</div></div>
  </div>
  <h2>Top-50 Companies With No Metrics</h2>{list_html(snapshot.top50_no_metrics)}
  <h2>Top-50 Missing Valuation</h2>{list_html(snapshot.top50_missing_valuation)}
  <h2>Top-50 Missing ARR / Revenue</h2>{list_html(snapshot.top50_missing_arr)}
  <h2>High-Priority Watchlist Candidates Not Profiled</h2>{list_html(snapshot.unprofiled_high_priority)}
  <h2>Single-Source Core Metrics</h2>{list_html(snapshot.single_source_metrics)}
</div></body></html>"""


def write_report() -> QualitySnapshot:
    snapshot = build_snapshot()
    out = data_dir() / "quality" / "report.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_markdown(snapshot))
    return snapshot
