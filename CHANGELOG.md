# Changelog

All notable changes to OpenPitch are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] — 2026-06-24

First public release.

### Added
- **Pipeline** — collect → transcribe → extract → derive → reconcile → publish. The
  git-tracked `data/` tree is the database.
- **Confidence + reconciliation engine** — tier/speaker/qualifier/decay scoring with
  noisy-OR corroboration; value clustering, consensus, and same-period contradiction
  detection (independent public sources only).
- **Recency vs. confirmed** — the freshest "in talks" valuation stays the headline while
  the latest confirmed figure is surfaced as an anchor; forward-looking revenue targets
  never become the current ARR.
- **Two-level taxonomy** — controlled main category + subcategory + free-text specialty +
  a 1–2 sentence business summary, auto-classified by one LLM pass.
- **Auto-discovery** — daily news/ranking-list discovery + knowledge backfill grows the
  universe without manual additions; public/acquired companies filtered out.
- **MCP server** — 8 read-only tools (no LLM calls, no key), with read-only tool annotations.
- **Static dashboard** — sortable/filterable company cards, sourced metrics with
  confidence bands and as-of years, A2A agent card.
- **LLM provider abstraction** — Gemini with model rotation + Groq fallback on quota.
- **Validation harness** — `scripts/validate_top50.py` diffs the dashboard top-50 against
  a researched reference.

### Infrastructure
- CI (pytest + ruff on Linux/macOS × Python 3.11/3.12), PyPI Trusted Publishing release
  workflow, daily refresh + GitHub Pages deploy.

[Unreleased]: https://github.com/Avierovich/openpitch/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Avierovich/openpitch/releases/tag/v0.1.0
