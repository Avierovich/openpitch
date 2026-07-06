# Changelog

All notable changes to OpenPitch are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.2] — 2026-07-07

### Fixed
- MCP Registry ownership markers use the case-exact namespace (io.github.Avierovich).

## [0.1.1] — 2026-07-07

### Added
- **`openpitch-mcp` launcher package** — `uvx openpitch-mcp` now works directly (uvx
  resolves package names; previously required `uvx --from openpitch openpitch-mcp`).
- **Official MCP Registry metadata** — `server.json` (`io.github.avierovich/openpitch`)
  + PyPI ownership markers; the registry feeds PulseMCP and other aggregators.
- **News ingestion overhaul** — metric-signal ranking of feed headlines, entity-mismatch
  demotion for name collisions, extraction company-context, and a gap-fill second pass
  that hunts article bodies when funding is known but valuation is missing (the fix that
  moved Sierra from #75 to the top 20 with a 10-source consensus valuation).
- **Quality gates** — funded-but-no-valuation is a critical flag over all profiles;
  discovery backlog is tracked separately from critical issues.

### Fixed
- Valuation plausibility floor (drops scraped junk below the round just raised).
- Derived claims no longer launder forward-looking/unconfirmed qualifiers.
- Claim retention across feed windows; extraction-cache edge cases; hermetic test suite.
- Company pages escape crawled text (XSS); wrong-entity claims corrected (Modal).

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
