# Recent Changes

## 2026-06-14 Snapshot

This file summarizes the product changes made during the latest build/test pass so future agents and contributors do not have to reconstruct the state from chat history.

## Product Runtime

- Completed runnable pipeline pieces around storage, publish, scoring, MCP tools, dashboard generation, and event/digest output.
- Added a 5-company committed seed database for software testing.
- Added derivation support for hard metric identities and validation-style derived claims.
- Added batched LLM extraction and model rotation to stay within free-tier quota.
- Added quota/backoff safety for live runs and bounded `--companies` execution.
- Added hosted Groq Whisper transcription support for podcast audio.
- Added Groq as a claim-extraction provider via `OPENPITCH_LLM=groq`, useful when Gemini quota is exhausted.
- Added broad-run controls: `--transcriptions`, `--max-source-items`, and `--skip-podcasts`.
- Added raw-GitHub data fetching for no-clone consumer installs.

## Security And Operations

- Added local `.env` loading for secrets; `.env` remains gitignored.
- Added SEC EDGAR fair-access headers through `OPENPITCH_SEC_USER_AGENT`.
- Wired GitHub Actions to pass `LLM_API_KEY`, `GROQ_API_KEY`, and `OPENPITCH_SEC_USER_AGENT`.
- Ran the deep test pass: `44 passed`, `ruff check` passed, `pip-audit` clean after local pip upgrade.
- Created a safe pre-push branch/commit for EDGAR/CI hardening while excluding generated data churn.

## Brand

- Created five SVG logo options under `docs/brand/logo-options/`.
- Selected option 5, **Terminal Proof**, as the current logo direction.
- Dashboard metric labels now use `config/metrics.yaml`, so `arr` renders as `ARR / revenue` and other finance metrics use product-facing labels.
- Dashboard company cards now display rank tiers for the retained top-50 universe.
- Dashboard now defaults to valuation sorting and includes user-selectable sorting by valuation, total funding, source coverage, category, and name.
- Ran a local 50-company source pass with Groq extraction, no podcast transcription, and capped source items. Result: 50 profiles rendered, 23 with extracted metrics and 27 source-checked with no supported metric claims yet.
- Fixed the first-pass top-50 quality issue: live runs no longer overwrite existing sourced profiles with empty source-checked profiles when extraction finds no claims.
- Expanded the source-backed seed baseline beyond the original 5 companies to include Perplexity, Glean, Harvey, ElevenLabs, Scale AI, Mercor, and Runway.
- Rebuilt the dashboard so valuation ranking now includes missing high-value/high-ARR companies such as Scale AI, Perplexity, ElevenLabs, Harvey, Mercor, and Glean.
- Added `openpitch quality-report`, which writes `data/quality/report.md`.
- Dashboard builds now include a quality banner and `dashboard/dist/quality.html` so coverage gaps are visible during hands-on review.
- Current quality report flags 51 critical issues and 108 warnings; these are launch blockers, not cosmetic defects.

## Current Caveats

- The seed data is suitable for software testing, not yet launch-grade.
- Public launch still needs a 10-company audited seed, selected contradiction assets, correction issue template, README demo asset, and published package/install validation.
- Once the GitHub push is complete and the clean-machine clone/MCP startup test passes, the frictionless source install gate should be marked fully complete in `docs/LAUNCH-GATES.md`.
- Generated `data/` changes from local live tests should remain separate from code commits unless intentionally audited.
