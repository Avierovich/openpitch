# Changelog

All notable changes to OpenPitch are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.4] - 2026-11-19

### Fixed
- The daily pipeline survives an LLM model being retired. A retired Gemini model returns 404,
  which used to crash every scheduled run (the dashboard served 37-day-old data). A 404 now
  rotates to the next model, then falls back to the next provider.
- `openpitch run --max-runtime-minutes` stops collecting at the budget and still publishes
  what finished. A budgeted run refreshes the stalest companies in the universe first, then
  the rest of the watchlist.
- The `openpitch-mcp` launcher now requires `openpitch>=0.1.4`, so it always installs a
  version with the plausibility gate.

### Added
- A serving-time plausibility gate (`src/openpitch/serving_gate.py`, thresholds in
  `config/serving_gate.yaml`). It withholds figures that cannot be right from the MCP tools,
  the dashboard and the market map: values whose source stated them in another currency, a
  ratio, or with a scale word that was never applied; money figures too small to be real;
  values outside a believable range; and the less reliable side of a contradiction such as a
  valuation below total funding. Committed data is not edited. On 2026-11-18 it withheld 435
  of 1,925 published figures: 53 implausible values and 382 malformed ones. It caught 14 of 17
  known-bad figures, and the other 3 were judged correct or not detectable at serving time.
  It hid none of the reference figures checked.
- The quality report gains a section listing implausible figures, so it measures wrong numbers
  as well as missing ones. The critical count rises accordingly, from 125 to 178.

### Changed
- MCP: `get_metric` can return `status: "withheld"`, with a `message` and a `next` pointer to
  `get_provenance`. Withheld metrics keep every key with the figure keys set to `null`, plus a
  `gate` block. Summary cells in `list_companies` and `compare_companies` become
  `{"value": null, "status": "withheld", ...}`, while `null` still means no data. Events about
  a withheld figure lose their numbers, including in the summary. `get_provenance` is
  unchanged apart from an added `gate` verdict and `gate_flag` on claims.
- Tool descriptions tell the agent it may say a withheld figure exists and why, but must not
  state it.
- `schemas/resolved_value.schema.json` is now 1.1: it adds `status` and `gate`, and allows
  `null` for `range` and `delta`. The old schema already rejected 1,457 of 1,925 served
  metrics, because a metric with no range is served as `range: null`.

### Notes
- `OPENPITCH_GATE=off`, or `enabled: false` in the config, serves every figure ungated.
- A plain confidence floor was considered and rejected. Only 4 of the 17 known-bad figures sat
  below 0.2 confidence, while a 0.2 floor would hide 42% of all figures. The floor exists in
  the config but ships at 0.
- `universe_rank` is still computed upstream from raw values, so a company whose valuation is
  withheld can keep an inflated rank in `list_companies` until the ranking is gated as well.

## [0.1.3] — 2026-07-09

### Fixed
- **MCP discovery tools no longer overflow the client's tool-result limit.** `what_moved`
  and `get_events` returned the entire event feed (unbounded, oldest-first) and `search`
  returned all hits — a large payload the client truncated, forcing agents to guess
  filters. Now: newest-first, a `limit` param (defaults 50/50/25), `total`/`truncated`
  fields, `what_moved` defaults to a 30-day window (echoed back), and events are slimmed to
  outlet names (full source URLs remain one `get_provenance` call away). Payload for the
  live feed dropped ~45K → ~14K chars. (Found via an independent third-party install.)

### Added
- **Dashboard visualizations** (hand-rolled inline SVG, zero new dependency): low—consensus—high
  **range bars** on ranged metrics (the probabilistic spread, made visible); **history
  sparklines** on company pages (value-over-time, only when there's real movement); and a new
  **sector market-map page** (`market.html`) — total tracked valuation by sector.
- `_money` now renders a trillion (`$X.XT`) tier.

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
