"""Filesystem locations (env-overridable). The git-tracked `data/` IS the database."""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def data_dir() -> Path:
    return Path(os.environ.get("OPENPITCH_DATA_DIR", REPO_ROOT / "data"))


def config_dir() -> Path:
    return Path(os.environ.get("OPENPITCH_CONFIG_DIR", REPO_ROOT / "config"))
