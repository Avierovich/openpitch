"""Suite-wide hermetic guards.

`store._data_file` falls back to fetching missing files from the PUBLIC repo
(paths.resolve_remote) — the moment Avierovich/openpitch went public, tests that
build against an empty tmp data dir started silently pulling the real committed
universe over the network (2 CI failures + a 70s slowdown). Point the remote at
an unroutable address and the fetch cache at a throwaway dir so no test can ever
touch the network or a developer's real ~/.cache/openpitch.
"""

import pytest


@pytest.fixture(autouse=True)
def _hermetic_remote(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENPITCH_REMOTE", "http://127.0.0.1:1")
    monkeypatch.setenv("OPENPITCH_CACHE", str(tmp_path / "remote-cache"))
