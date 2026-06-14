"""Pipeline orchestrator / CLI (FRD §7, §11).

Commands:
    openpitch seed             # build data/ from committed seed claims (offline, no key)
    openpitch run [--offline]  # live daily pass (collect→…→publish); needs LLM key + network
    openpitch build-dashboard  # render static company cards from committed data

Each stage is fail-isolated: one company failing is logged, not fatal.
"""

from __future__ import annotations

import hashlib
import json
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
        meta = {k: entry[k] for k in ("id", "name") if k in entry}
        meta.update({"category": entry.get("category"), "domain": entry.get("domain"),
                     "aliases": entry.get("aliases", []), "segment": entry.get("segment", "global")})
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
        segment=meta.get("segment"), website=meta.get("domain"),
        aliases=meta.get("aliases", []),
        in_universe=True, metrics=metrics, last_updated=as_of,
    )
    return company, all_claims


def _finalize(pairs: list[tuple[Company, list[Claim]]], *, now: datetime, as_of: date) -> int:
    """Score the universe, publish each company, write universe + digest."""
    companies = [c for c, _ in pairs]
    prev = store.read_universe() or {}
    universe = select_universe(companies, prev_ids=prev.get("selected"))
    store.write_universe(universe)
    store.write_index([c.id for c in companies])  # manifest for no-clone consumers

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

    llm = get_provider()
    keys = metric_keys()
    watchlist = load_watchlist()
    if companies > 0:
        watchlist = watchlist[:companies]
    pairs: list[tuple[Company, list[Claim]]] = []
    for meta in watchlist:
        typer.echo(f"· {meta['id']}")
        company_stub = Company(id=meta["id"], name=meta["name"], last_updated=as_of,
                               aliases=meta.get("aliases", []), website=meta.get("domain"))
        items = []
        for adapter in ADAPTERS:
            try:
                items.extend(adapter.fetch(company_stub))
            except Exception as exc:  # noqa: BLE001
                typer.echo(f"  ! {meta['id']}/{adapter.__name__}: {exc}")
        # Bound audio transcriptions per company (others fall back to show-notes text).
        transcribe_budget = 3
        text_items: list = []
        for it in items:
            if it.needs_transcription and it.audio_url and transcribe_budget > 0:
                it = transcribe(it)
                transcribe_budget -= 1
            if it.text:
                text_items.append(it)
        claims: list[Claim] = []
        # Batch many source items per LLM call (free-tier-quota lever, FRD §7).
        for chunk in _chunks(text_items, 15):
            try:
                claims.extend(extract_claims_batch(chunk, company_stub, llm=llm, metric_keys=keys, now=now))
            except Exception as exc:  # noqa: BLE001
                typer.echo(f"  ! extract {meta['id']}: {str(exc)[:120]}")
        if claims:
            pairs.append(_reconcile_company(meta, claims, now=now, as_of=as_of))
    n_events = _finalize(pairs, now=now, as_of=as_of)
    typer.echo(f"Run complete: {len(pairs)} companies; {n_events} events.")


@app.command()
def build_dashboard() -> None:
    """Render the static dashboard/company cards from committed data (FRD §9)."""
    from .dashboard import build

    out = build()
    typer.echo(f"Dashboard written to {out}")


if __name__ == "__main__":
    app()
