"""Filesystem locations (env-overridable). The git-tracked `data/` IS the database."""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


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
