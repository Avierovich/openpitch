# Contributing to OpenPitch

Thanks for helping build open, sourced AI-startup intelligence. There are two very
different ways to contribute, and the most valuable one needs no code.

## 1. Correct or add data (no code needed)

OpenPitch is only as good as its sources. If a figure is wrong, stale, or missing a
better source, **open a [Data correction issue](https://github.com/Avierovich/openpitch/issues/new?template=correction.yml)**.
Include the company, the metric, the correct value, and a **public source URL**. That's
the single highest-leverage contribution.

The `data/` tree *is* the database — it's regenerated and committed by the daily
pipeline, so don't hand-edit `data/*.json` in a PR; fix the source/seed instead.

## 2. Contribute code

```bash
git clone https://github.com/Avierovich/openpitch
cd openpitch
python -m venv .venv && . .venv/bin/activate
pip install -e ".[pipeline,dev]"
pytest -q          # 60+ tests, all offline (MockLLM) — no API key needed
ruff check .       # lint
```

Guidelines:
- **Tests + lint must pass.** CI runs `pytest` + `ruff check` on Linux/macOS × Python 3.11/3.12.
- **Keep it zero-cost.** No paid/auth-walled data sources; respect `robots.txt` and ToS
  (see `docs/DATA-POLICY.md`). The MCP server makes **zero LLM calls**.
- **Match the surrounding style.** The codebase favors small, direct functions; non-trivial
  logic leaves one runnable check (an `assert`-based `__main__` or a `test_*`).
- **Where things live:** sources in `pipeline/sources/`, reconciliation in `reconcile/`,
  MCP tools in `mcp_server/`, the dashboard in `pipeline/dashboard.py`. Design docs are in `docs/`.

## Pull requests

Open a PR against `main` with a clear description of *what* and *why*. Small, focused PRs
review fastest. By contributing you agree your work is licensed under the project's MIT License.
