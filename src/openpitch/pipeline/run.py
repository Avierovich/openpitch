"""Pipeline orchestrator / CLI (FRD §7, §11).

Commands:
    openpitch seed             # build data/ from committed seed claims (offline, no key)
    openpitch run [--offline]  # live daily pass (collect→…→publish); needs LLM key + network
    openpitch build-dashboard  # render static company cards from committed data
    openpitch quality-report   # write data/quality/report.md

Each stage is fail-isolated: one company failing is logged, not fatal.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections import defaultdict
from datetime import date, datetime

import typer

from .. import store
from ..config import load_metrics, metric_keys
from ..models import Claim, Company, Source, SourceType, Speaker, SpeakerRole
from ..paths import data_dir
from ..reconcile.confidence import base_confidence
from ..reconcile.derive import derive_claims
from ..reconcile.engine import reconcile
from .publish import publish_company, write_digest_for
from .score import select_universe

app = typer.Typer(add_completion=False, help="OpenPitch pipeline.")


# ── seed loading (offline, hand-authored, sourced) ───────────────────────────


def _claim_from_seed(rec: dict, now: datetime) -> Claim:
    src = rec["source"]
    source = Source(
        type=SourceType(src["type"]), name=src["name"], url=src.get("url"),
        locator=src.get("locator"),
        published_at=date.fromisoformat(src["published_at"]) if src.get("published_at") else None,
    )
    speaker = Speaker(role=SpeakerRole(rec.get("speaker_role", "unknown")))
    cid = "clm_" + hashlib.sha256(
        f"{rec['company_id']}|{rec['metric']}|{rec['value']}|{source.name}".encode()
    ).hexdigest()[:10]
    claim = Claim(
        id=cid, company_id=rec["company_id"], metric=rec["metric"], value=rec["value"],
        unit=rec.get("unit"), raw_text=rec.get("raw_text", ""),
        qualifiers=rec.get("qualifiers", []), speaker=speaker, source=source,
        extracted_at=now, extractor_model="seed", base_confidence=0.0,
    )
    claim.base_confidence = round(base_confidence(claim), 4)
    return claim


def _load_seed(now: datetime) -> dict[str, tuple[dict, list[Claim]]]:
    path = data_dir() / "seed" / "claims.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text())
    groups: dict[str, tuple[dict, list[Claim]]] = {}
    for entry in payload.get("companies", []):
        from ..config import apply_taxonomy
        meta = {k: entry[k] for k in ("id", "name") if k in entry}
        meta.update({"category": entry.get("category"), "domain": entry.get("domain"),
                     "aliases": entry.get("aliases", []), "segment": entry.get("segment", "global")})
        meta = apply_taxonomy(meta)
        claims = [_claim_from_seed({**c, "company_id": entry["id"]}, now) for c in entry.get("claims", [])]
        groups[entry["id"]] = (meta, claims)
    return groups


# ── shared assembly ──────────────────────────────────────────────────────────


def _reconcile_company(meta: dict, claims: list[Claim], *, now: datetime, as_of: date) -> tuple[Company, list[Claim]]:
    defs = load_metrics()
    all_claims = claims + derive_claims(claims, now=now, as_of=as_of)
    by_metric: dict[str, list[Claim]] = defaultdict(list)
    for c in all_claims:
        by_metric[c.metric].append(c)

    metrics = {}
    for metric, cl in by_metric.items():
        md = defs.get(metric)
        if not md:
            continue
        rv = reconcile(
            metric, cl, as_of=as_of, tau=md.tau, tolerance=md.cluster_tolerance,
            unit=md.unit, previous=store.last_history(meta["id"], metric),
            history_ref=f"history/{meta['id']}/{metric}.jsonl",
        )
        if rv:
            metrics[metric] = rv

    company = Company(
        id=meta["id"], name=meta["name"], category=meta.get("category"),
        subcategory=meta.get("subcategory"), specialty=meta.get("specialty"),
        summary=meta.get("summary"),
        segment=meta.get("segment"), website=meta.get("domain"),
        aliases=meta.get("aliases", []),
        in_universe=True, metrics=metrics, last_updated=as_of,
    )
    return company, all_claims


def _finalize(pairs: list[tuple[Company, list[Claim]]], *, now: datetime, as_of: date) -> int:
    """Score the universe, publish each company, write universe + digest.

    Scoring is GLOBAL: rank over the union of all committed companies plus this
    run's, so incremental runs (e.g. `run --companies 2`) produce one consistent
    ranking instead of duplicate ranks per batch.
    """
    new_by_id = {c.id: c for c, _ in pairs}
    all_by_id = {c.id: c for c in store.read_all_companies()}
    all_by_id.update(new_by_id)  # this run's freshly-reconciled objects win
    everyone = list(all_by_id.values())

    prev = store.read_universe() or {}
    universe = select_universe(everyone, prev_ids=prev.get("selected"))  # mutates rank/score
    store.write_universe(universe)
    store.write_index(list(all_by_id.keys()))  # manifest for no-clone consumers

    # Persist refreshed rank/score for companies NOT in this run (run companies
    # are written by publish_company below, which also emits events).
    for cid, c in all_by_id.items():
        if cid not in new_by_id:
            store.write_company(c)

    all_events = []
    for company, claims in pairs:
        try:
            all_events.extend(publish_company(company, claims, now=now))
        except Exception as exc:  # noqa: BLE001 — fail-isolate per company
            typer.echo(f"  ! {company.id}: publish failed: {exc}")
    write_digest_for(as_of.isoformat(), all_events)
    return len(all_events)


# ── commands ─────────────────────────────────────────────────────────────────


@app.command()
def seed() -> None:
    """Build the data/ database from committed seed claims (offline, no key)."""
    # Deterministic timestamp so re-running on the same day is idempotent
    # (clean git diffs — the data/ tree is the database).
    as_of = date.today()
    now = datetime.combine(as_of, datetime.min.time())
    groups = _load_seed(now)
    if not groups:
        typer.echo("No seed found at data/seed/claims.json")
        raise typer.Exit(1)
    pairs = [_reconcile_company(meta, claims, now=now, as_of=as_of) for meta, claims in groups.values()]
    n_events = _finalize(pairs, now=now, as_of=as_of)
    typer.echo(f"Seeded {len(pairs)} companies; {n_events} events; wrote data/.")


@app.command()
def run(
    offline: bool = typer.Option(False, help="Skip network sources; use seed only."),
    companies: int = typer.Option(0, help="Limit to the first N watchlist companies (0 = all)."),
    ids: str = typer.Option("", help="Comma-separated company ids to run instead of the full watchlist."),
    transcriptions: int = typer.Option(3, help="Maximum podcast audio transcriptions per company."),
    max_source_items: int = typer.Option(15, help="Maximum source items to extract per company."),
    skip_podcasts: bool = typer.Option(False, help="Skip podcast RSS sources for broad/fast runs."),
    extract_sleep: float = typer.Option(0.0, help="Seconds to sleep after each extraction batch."),
) -> None:
    """Live daily pass: collect → transcribe → extract → derive → reconcile → publish."""
    if offline:
        return seed()
    now = datetime.now()
    as_of = now.date()
    from ..config import load_watchlist
    from .extract import extract_claims_batch
    from .llm import get_provider
    from .sources import ADAPTERS
    from .transcribe import transcribe

    def _chunks(seq, n):
        for i in range(0, len(seq), n):
            yield seq[i : i + n]

    def _interleave_by_type(items):
        # ponytail: round-robin across source types so one flood (e.g. 100 EDGAR
        # items for a private co) can't eat the whole max_source_items budget and
        # starve the high-yield news/web items. Preserves per-type order.
        from collections import OrderedDict
        buckets: dict = OrderedDict()
        for it in items:
            buckets.setdefault(it.source_type, []).append(it)
        out, queues = [], list(buckets.values())
        while queues:
            queues = [q for q in queues if q]
            for q in queues:
                out.append(q.pop(0))
        return out

    llm = get_provider()
    keys = metric_keys()
    watchlist = load_watchlist()
    if ids.strip():
        wanted = {cid.strip() for cid in ids.split(",") if cid.strip()}
        watchlist = [meta for meta in watchlist if meta["id"] in wanted]
    if companies > 0:
        watchlist = watchlist[:companies]
    pairs: list[tuple[Company, list[Claim]]] = []
    for meta in watchlist:
        typer.echo(f"· {meta['id']}")
        company_stub = Company(id=meta["id"], name=meta["name"], last_updated=as_of,
                               aliases=meta.get("aliases", []), website=meta.get("domain"))
        items = []
        for adapter in ADAPTERS:
            if skip_podcasts and adapter.__name__.endswith("podcast_rss"):
                continue
            try:
                items.extend(adapter.fetch(company_stub))
            except Exception as exc:  # noqa: BLE001
                typer.echo(f"  ! {meta['id']}/{adapter.__name__}: {exc}")
        # Bound audio transcriptions per company (others fall back to show-notes text).
        transcribe_budget = max(0, transcriptions)
        text_items: list = []
        for it in items:
            if it.needs_transcription and it.audio_url and transcribe_budget > 0:
                it = transcribe(it)
                transcribe_budget -= 1
            if it.text:
                text_items.append(it)
        if max_source_items > 0:
            text_items = _interleave_by_type(text_items)[:max_source_items]
        claims: list[Claim] = []
        # Batch many source items per LLM call (free-tier-quota lever, FRD §7).
        for chunk in _chunks(text_items, 15):
            try:
                claims.extend(extract_claims_batch(chunk, company_stub, llm=llm, metric_keys=keys, now=now))
            except Exception as exc:  # noqa: BLE001
                typer.echo(f"  ! extract {meta['id']}: {str(exc)[:120]}")
            if extract_sleep > 0:
                time.sleep(extract_sleep)
        if claims:
            pairs.append(_reconcile_company(meta, claims, now=now, as_of=as_of))
    n_events = _finalize(pairs, now=now, as_of=as_of)
    typer.echo(f"Run complete: {len(pairs)} companies; {n_events} events.")


@app.command()
def recompute() -> None:
    """Re-resolve all committed companies from stored claims — re-apply engine logic, no network/LLM."""
    as_of = date.today()
    now = datetime.combine(as_of, datetime.min.time())
    pairs = []
    for c in store.read_all_companies():
        claims = [cl for cl in store.read_claims(c.id) if cl.source.type.value != "derived"]
        if not claims:
            continue
        from ..config import apply_taxonomy
        meta = apply_taxonomy({"id": c.id, "name": c.name, "category": c.category,
                               "subcategory": c.subcategory, "specialty": c.specialty,
                               "summary": c.summary,
                               "segment": c.segment, "domain": c.website, "aliases": c.aliases})
        pairs.append(_reconcile_company(meta, claims, now=now, as_of=as_of))
    n = _finalize(pairs, now=now, as_of=as_of)
    typer.echo(f"Recomputed {len(pairs)} companies from committed claims; {n} events.")


@app.command()
def discover() -> None:
    """Find AI startups from funding news and add them to config/discovered.yaml (needs LLM key)."""
    from .discover import discover as run_discover, merge_discovered
    from .llm import get_provider

    found = run_discover(llm=get_provider())
    n = merge_discovered(found)
    typer.echo(f"Discovered {len(found)} candidates; {n} new added to config/discovered.yaml")


@app.command()
def classify(all: bool = typer.Option(False, "--all", help="Re-classify everyone, not just new companies.")) -> None:
    """Assign a controlled main category + subcategory + specialty + summary to every
    company (one LLM pass) and write config/taxonomy.yaml. Re-runnable (needs LLM key)."""
    from ..config import load_taxonomy, load_watchlist
    from .classify import classify as run_classify, write_taxonomy
    from .llm import get_provider

    # Classify the union of watchlist + already-profiled companies. "Done" = already
    # has a summary (the newest field), so re-runs fill gaps / new arrivals; --all redoes all.
    load_taxonomy.cache_clear()
    done = set() if all else {cid for cid, t in load_taxonomy().get("companies", {}).items() if t.get("summary")}
    seen, companies = set(), []
    for m in load_watchlist():
        cid = m.get("id")
        if cid and cid not in seen and cid not in done:
            seen.add(cid)
            companies.append({"id": cid, "name": m.get("name", cid),
                              "category": m.get("category"), "domain": m.get("domain")})
    if not companies:
        typer.echo("All companies already classified; nothing to do.")
        return
    classified = run_classify(companies, llm=get_provider())
    n = write_taxonomy(classified)
    load_taxonomy.cache_clear()
    typer.echo(f"Classified {n}/{len(companies)} companies; wrote config/taxonomy.yaml")


@app.command()
def build_dashboard() -> None:
    """Render the static dashboard/company cards from committed data (FRD §9)."""
    from .dashboard import build

    out = build()
    typer.echo(f"Dashboard written to {out}")


@app.command()
def quality_report() -> None:
    """Write a data-quality report for launch/dashboard review."""
    from .quality import write_report

    snapshot = write_report()
    typer.echo(
        "Quality report written to "
        f"{data_dir() / 'quality' / 'report.md'} "
        f"({snapshot.critical_count} critical, {snapshot.warning_count} warnings)."
    )


if __name__ == "__main__":
    app()
