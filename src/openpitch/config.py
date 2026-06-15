"""Config loaders for the metric registry, scoring weights, watchlist, and podcasts."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import yaml

from . import paths
from .paths import config_dir


def _config_file(name: str):
    """Local config if present, else the remote-cached copy (no-clone installs)."""
    local = config_dir() / name
    if local.exists():
        return local
    remote = paths.resolve_remote(f"config/{name}")
    return remote if remote else local


@dataclass(frozen=True)
class MetricDef:
    key: str
    label: str
    unit: str
    tau: float
    cluster_tolerance: float
    implied_v1: bool


@lru_cache(maxsize=1)
def load_metrics() -> dict[str, MetricDef]:
    raw = yaml.safe_load(_config_file("metrics.yaml").read_text())["metrics"]
    return {
        k: MetricDef(
            key=k, label=v["label"], unit=str(v["unit"]),
            tau=float(v["tau"]), cluster_tolerance=float(v["cluster_tolerance"]),
            implied_v1=bool(v["implied_v1"]),
        )
        for k, v in raw.items()
    }


def metric_keys() -> list[str]:
    return list(load_metrics().keys())


@lru_cache(maxsize=1)
def load_scoring() -> dict:
    return yaml.safe_load(_config_file("scoring.yaml").read_text())


@lru_cache(maxsize=1)
def load_watchlist() -> list[dict]:
    """Global + MENA companies, each tagged with a `segment`."""
    raw = yaml.safe_load(_config_file("watchlist.yaml").read_text())
    out: list[dict] = []
    for c in raw.get("companies", []):
        out.append({**c, "segment": c.get("segment", "global")})
    for c in raw.get("mena", []):
        out.append({**c, "segment": c.get("segment", "mena")})
    # Auto-discovered companies (config/discovered.yaml) — curated file stays untouched.
    disc = config_dir() / "discovered.yaml"
    if disc.exists():
        have = {c["id"] for c in out}
        for c in (yaml.safe_load(disc.read_text()) or {}).get("companies", []):
            if c.get("id") and c["id"] not in have:
                out.append({**c, "segment": c.get("segment", "global")})
    return out


@lru_cache(maxsize=1)
def load_podcasts() -> list[dict]:
    path = _config_file("podcasts.yaml")
    if not path or not path.exists():
        return []
    data = yaml.safe_load(path.read_text()) or {}
    return [f for f in data.get("feeds", []) if f.get("feed_url")]
