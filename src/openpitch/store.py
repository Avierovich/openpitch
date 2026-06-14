"""Storage / IO layer — read & write the git-tracked `data/` database (FRD §3, §10).

JSON for documents, JSON Lines for append-only history and the event feed.
Everything round-trips through the Pydantic models in `models.py`.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from . import paths
from .models import Claim, Company, Event, ResolvedValue
from .paths import data_dir


# ── low-level helpers ────────────────────────────────────────────────────────


def _ensure(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def _data_file(relpath: str) -> Path | None:
    """Local data file if present, else the remote-cached copy (no-clone installs)."""
    local = data_dir() / relpath
    if local.exists():
        return local
    return paths.resolve_remote(f"data/{relpath}")


def _write_json(path: Path, obj) -> None:
    _ensure(path.parent)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=str) + "\n")


def _read_json(path: Path | None):
    return json.loads(path.read_text()) if path and path.exists() else None


def _append_jsonl(path: Path, rows: list[dict]) -> None:
    _ensure(path.parent)
    with path.open("a") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def _read_jsonl(path: Path | None) -> list[dict]:
    if not path or not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


# ── companies ────────────────────────────────────────────────────────────────


def write_company(company: Company) -> None:
    _write_json(data_dir() / "companies" / f"{company.id}.json", company.model_dump(mode="json"))


def read_company(company_id: str) -> Company | None:
    raw = _read_json(_data_file(f"companies/{company_id}.json"))
    return Company.model_validate(raw) if raw else None


def write_index(company_ids: list[str]) -> None:
    """Manifest of company ids — lets remote (no-clone) consumers enumerate companies."""
    _write_json(data_dir() / "index.json", {"companies": sorted(company_ids)})


def list_company_ids() -> list[str]:
    d = data_dir() / "companies"
    if d.exists():
        return sorted(p.stem for p in d.glob("*.json"))
    idx = _read_json(_data_file("index.json"))  # remote fallback
    return sorted(idx.get("companies", [])) if idx else []


def read_all_companies() -> list[Company]:
    return [c for cid in list_company_ids() if (c := read_company(cid))]


# ── claims ───────────────────────────────────────────────────────────────────


def write_claims(company_id: str, claims: list[Claim]) -> None:
    _write_json(
        data_dir() / "claims" / f"{company_id}.json",
        [c.model_dump(mode="json") for c in claims],
    )


def read_claims(company_id: str) -> list[Claim]:
    raw = _read_json(_data_file(f"claims/{company_id}.json")) or []
    return [Claim.model_validate(c) for c in raw]


# ── history (append-only per company/metric) ─────────────────────────────────


def append_history(company_id: str, metric: str, resolved: ResolvedValue) -> None:
    row = {
        "as_of": resolved.as_of,
        "value": resolved.value,
        "confidence": resolved.confidence,
        "estimate_type": resolved.estimate_type.value,
        "supporting_claims": resolved.supporting_claims,
    }
    _append_jsonl(data_dir() / "history" / company_id / f"{metric}.jsonl", [row])


def read_history(company_id: str, metric: str) -> list[dict]:
    return _read_jsonl(_data_file(f"history/{company_id}/{metric}.jsonl"))


def last_history(company_id: str, metric: str) -> ResolvedValue | None:
    rows = read_history(company_id, metric)
    if not rows:
        return None
    r = rows[-1]
    return ResolvedValue(
        metric=metric, value=r["value"], as_of=r["as_of"],
        estimate_type=r["estimate_type"], confidence=r["confidence"],
    )


# ── events feed ──────────────────────────────────────────────────────────────


def append_events(events: list[Event]) -> None:
    if not events:
        return
    rows = [e.model_dump(mode="json") for e in events]
    _append_jsonl(data_dir() / "events" / "feed.jsonl", rows)
    # also a dated shard for convenience
    if events:
        day = str(events[0].detected_at)[:10]
        _append_jsonl(data_dir() / "events" / f"{day}.jsonl", rows)


def read_events(since: str | None = None) -> list[dict]:
    rows = _read_jsonl(_data_file("events/feed.jsonl"))
    if since:
        rows = [r for r in rows if str(r.get("detected_at", ""))[:10] >= since]
    return rows


# ── universe + digest ────────────────────────────────────────────────────────


def write_universe(universe: dict) -> None:
    _write_json(data_dir() / "universe.json", universe)


def read_universe() -> dict | None:
    return _read_json(_data_file("universe.json"))


def write_digest(day: str, markdown: str) -> None:
    path = data_dir() / "digest" / f"{day}.md"
    _ensure(path.parent)
    path.write_text(markdown)
