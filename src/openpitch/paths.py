"""Filesystem locations (env-overridable). The git-tracked `data/` IS the database."""

from __future__ import annotations

import os
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def remote_base() -> str:
    """Public repo raw base for no-clone installs (override via OPENPITCH_REMOTE)."""
    return os.environ.get(
        "OPENPITCH_REMOTE", "https://raw.githubusercontent.com/OWNER/openpitch/main"
    ).rstrip("/")


def cache_root() -> Path:
    return Path(os.environ.get("OPENPITCH_CACHE", Path.home() / ".cache" / "openpitch"))


def resolve_remote(relpath: str) -> Path | None:
    """Fetch a repo-relative file from the public repo into a TTL cache.

    Lets `uvx openpitch-mcp` read committed data/config with NO clone. Returns a
    cached local Path, or None if unavailable. Falls back to a stale cache on
    network failure (better than nothing).
    """
    ttl = int(os.environ.get("OPENPITCH_CACHE_TTL", "3600"))
    cache = cache_root() / relpath
    if cache.exists() and (time.time() - cache.stat().st_mtime) < ttl:
        return cache
    try:
        import httpx

        r = httpx.get(f"{remote_base()}/{relpath}", timeout=20, follow_redirects=True)
        if r.status_code == 200:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_bytes(r.content)
            return cache
    except Exception:  # noqa: BLE001
        pass
    return cache if cache.exists() else None


def data_dir() -> Path:
    return Path(os.environ.get("OPENPITCH_DATA_DIR", REPO_ROOT / "data"))


def config_dir() -> Path:
    return Path(os.environ.get("OPENPITCH_CONFIG_DIR", REPO_ROOT / "config"))


def load_dotenv() -> None:
    """Load REPO_ROOT/.env into the environment (existing env vars win).

    Dependency-free. The .env file is gitignored — it holds local secrets like
    LLM_API_KEY and is never committed.
    """
    env = REPO_ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        os.environ.setdefault(key.strip(), val.strip().strip("\"'"))
