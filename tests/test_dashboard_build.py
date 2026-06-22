"""Regression tests for the flaky build-dashboard bug.

Two failure modes were observed: (1) a dashboard build racing a concurrent `run`
that rewrites data/companies/*.json crashed with JSONDecodeError because the
non-atomic write truncated a file a reader caught mid-write; (2) a short read
silently shipped a near-empty "all pending" dashboard. Atomic writes fix (1); a
fail-loud guard in build() fixes (2).
"""

from __future__ import annotations

import json
import threading
import time

import pytest

from openpitch import store
from openpitch.models import Company
from openpitch.pipeline import dashboard


def test_atomic_write_no_partial_reads_under_concurrency(tmp_path):
    """A reader must never see an empty/torn file while it's being rewritten."""
    path = tmp_path / "c.json"
    store.atomic_write_text(path, json.dumps({"id": "acme", "metrics": list(range(50))}))

    stop = False

    def writer():
        while not stop:
            store._write_json(path, {"id": "acme", "metrics": list(range(50))})

    t = threading.Thread(target=writer, daemon=True)
    t.start()
    errors = 0
    t0 = time.time()
    reads = 0
    while time.time() - t0 < 1.5:
        try:
            json.loads(path.read_text())  # would raise JSONDecodeError on a torn read
            reads += 1
        except json.JSONDecodeError:
            errors += 1
    stop = True
    t.join(timeout=1)

    assert reads > 0
    assert errors == 0, f"{errors} torn reads — atomic write is not atomic"
    # the os.replace temp files must not pile up
    assert not list(tmp_path.glob(".tmp-*"))


def test_atomic_write_replaces_content(tmp_path):
    p = tmp_path / "x.json"
    store.atomic_write_text(p, "first")
    store.atomic_write_text(p, "second")
    assert p.read_text() == "second"
    assert not list(tmp_path.glob(".tmp-*"))


def _company(cid: str, *, in_universe: bool = True) -> Company:
    from datetime import date

    return Company(id=cid, name=cid.title(), last_updated=date(2026, 6, 14),
                   in_universe=in_universe, universe_rank=1)


def test_build_aborts_on_short_read(tmp_path, monkeypatch):
    """If fewer companies load than exist on disk, build() must raise, not ship."""
    monkeypatch.setenv("OPENPITCH_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(store, "list_company_ids", lambda: ["a", "b", "c", "d"])
    monkeypatch.setattr(store, "read_all_companies", lambda: [_company("a")])  # 1 of 4
    monkeypatch.setattr(store, "read_universe", lambda: {"selected": []})

    with pytest.raises(RuntimeError, match="read 1 of 4"):
        dashboard.build()


def test_build_aborts_when_universe_undercount(tmp_path, monkeypatch):
    """Even if the file count matches, far fewer in-universe than last time -> abort."""
    monkeypatch.setenv("OPENPITCH_DATA_DIR", str(tmp_path))
    loaded = [_company("a")]
    monkeypatch.setattr(store, "list_company_ids", lambda: ["a"])
    monkeypatch.setattr(store, "read_all_companies", lambda: loaded)
    monkeypatch.setattr(store, "read_universe", lambda: {"selected": [str(i) for i in range(50)]})

    with pytest.raises(RuntimeError, match="universe.json selects 50"):
        dashboard.build()
