# Agent Coordination Log

This file is the handoff point for agentic coding tools working in this repo.
Read it before editing, especially when Codex and Claude Code are both active.

## Current Coordination Rules

- Do not revert dirty working-tree changes unless Mohamed explicitly asks.
- Treat unlisted dirty files as user/Claude Code work until proven otherwise.
- Prefer small, source-backed documentation changes over broad rewrites.
- No runtime code changes were made by Codex during the competitive-research/doc pass.
- OpenPitch's trust model remains: public sources, provenance, confidence, auditability, and conservative ToS posture.

## Codex Edits Log

### 2026-06-13 - Product/strategy documentation expansion

Codex added or enriched the project documentation to reflect that OpenPitch is still in development and should launch only after credible proof assets exist.

Files created by Codex:

- `docs/PRD.md`
- `docs/LAUNCH-GATES.md`
- `docs/METHODOLOGY.md`
- `docs/DATA-POLICY.md`
- `docs/V0-SEED-DATASET.md`
- `docs/MCP-SPEC.md`
- `docs/CORRECTIONS.md`
- `docs/EVENTS-SPEC.md`

Files modified by Codex:

- `README.md`
- `docs/GROWTH.md`

Main content changes:

- Added links from the README to product scope, trust-model, and interface docs.
- Added development-stage launch gates to the growth plan.
- Added correction workflow, contradiction-card guidance, proof-of-freshness framing, trust metrics, and launch no-go criteria.
- Documented public-source policy, confidence methodology, event feed design, MCP interface expectations, and v0 seed dataset strategy.

### 2026-06-13 - Competitive matrix and OSS/free/MCP competitor research

Codex expanded the competitive analysis with open-source, free, MCP, dataset, and social-signal research.

Files modified by Codex:

- `scripts/build_competitive_matrix.py`
- `docs/competitive-matrix.xlsx`
- `docs/OSS-LANDSCAPE.md`
- `docs/OSS-DEEP-DIVE.md`
- `docs/COMPETITIVE-ANALYSIS.md`

Main content changes:

- Regenerated `docs/competitive-matrix.xlsx` from `scripts/build_competitive_matrix.py`.
- Added workbook sheet `OSS + Free Direct Landscape`.
- Added workbook sheet `Research Backlog`.
- Expanded `Source Notes` with source type labels such as official repo, official docs, MCP registry, package registry, dataset repo, product account, social media, and third-party listing.
- Added/verified OSS/free/direct or near-direct competitors:
  - Exa Company Researcher
  - Octagon Funding Data MCP
  - Sieve MCP
  - Intelica MCP
  - CompanyLens MCP
  - FounderSignal MCP
  - Crunchbase MCP variants
  - Tavily company-research agent patterns
  - Apify company-research actors
  - ROSS Index / Runa
  - LF AI Landscape
  - OpenVC / findfunding.vc
  - YC OSS company lists
- Updated `docs/OSS-LANDSCAPE.md` with a broader research protocol and competitor categories.
- Updated `docs/OSS-DEEP-DIVE.md` with short teardowns for Exa Company Researcher, Octagon Funding MCP, Sieve MCP, CompanyLens MCP, and Intelica MCP.
- Kept `docs/COMPETITIVE-ANALYSIS.md` focused on paid incumbents, with a pointer to the expanded OSS/free matrix.

Verification performed by Codex:

- Ran `.venv/bin/python scripts/build_competitive_matrix.py`.
- Confirmed workbook sheets:
  - `Executive Summary`
  - `Core Overview`
  - `Feature Matrix`
  - `Pricing & Access`
  - `Agent Open Landscape`
  - `OSS + Free Direct Landscape`
  - `Research Backlog`
  - `Adjacent Watchlist`
  - `Positioning`
  - `Source Notes`
- Confirmed every added OSS/free competitor row has a source URL and directness classification.
- Confirmed no blank default workbook sheet.

Research limits:

- Codex used public sources only.
- Codex did not use paid subscriptions, payment cards, paywall bypassing, private documents, or auth-walled scraping.
- X/social verification was limited to public search snippets/pages; Exa had the clearest public X signals. Other social evidence was marked limited/noisy/blocked where appropriate.

### 2026-06-13 - X/social feature recommendation

Codex did not edit implementation files for X ingestion. It recommended adding an optional `x_signals` adapter rather than a default X scraper.

Recommended shape:

- Disabled by default.
- Treat X as `SourceType.SOCIAL`.
- Support `manual_urls` as the no-key path.
- Support BYO official X API credentials only if configured.
- Do not scrape login-gated pages, protected accounts, private content, or bypass rate limits/access controls.
- Store durable post URL/post ID, author handle, date, short supporting phrase, and provenance.
- Use X mainly for contradiction discovery, founder/operator metric claims, funding/customer/logo announcements, and source discovery that can be corroborated elsewhere.

### 2026-06-14 - SEC EDGAR fair-access header fix

Codex updated the EDGAR source adapter after a live pipeline run returned `403 Forbidden` from the SEC EDGAR full-text search endpoint.

Files modified by Codex:

- `src/openpitch/pipeline/sources/edgar.py`
- `tests/test_adapters.py`

Main content changes:

- Added `edgar.sec_headers()`.
- The EDGAR adapter now reads `OPENPITCH_SEC_USER_AGENT` from `.env`.
- Added SEC-friendly request headers: `User-Agent`, `Accept-Encoding`, and `Accept`.
- Added adapter tests proving the env-backed user agent is sent without making network calls.

Verification performed by Codex:

- Ran `PYTHONPATH=src .venv/bin/python -m pytest tests/test_adapters.py`.
- Result: `11 passed`.

Follow-up required:

- Add a real contact-bearing user agent to local `.env`, for example:

```env
OPENPITCH_SEC_USER_AGENT=OpenPitch/0.1 your-email@example.com
```

Do not commit `.env`; it is gitignored and should remain local.

### 2026-06-14 - Daily workflow env wiring

Codex updated the GitHub Actions daily refresh workflow so CI can pass optional live-source credentials.

Files modified by Codex:

- `.github/workflows/daily.yml`
- `src/openpitch/pipeline/publish/events.py`
- `src/openpitch/pipeline/publish/publish.py`
- `src/openpitch/pipeline/sources/base.py`
- `src/openpitch/store.py`

Main content changes:

- Added `GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}` to the pipeline step.
- Added `OPENPITCH_SEC_USER_AGENT: ${{ secrets.OPENPITCH_SEC_USER_AGENT }}` to the pipeline step.
- Updated the workflow comment to clarify that `LLM_API_KEY` controls live extraction, while Groq and SEC user-agent improve transcription and EDGAR reliability.
- Removed unused imports found by the pre-push `ruff check`; no behavior change.

Follow-up required:

- Add repository secrets `GROQ_API_KEY` and `OPENPITCH_SEC_USER_AGENT` in GitHub before relying on the scheduled live pipeline.

## Claude Code Edits Log

### 2026-06-13 - Core engine implementation (committed)

Claude Code built and committed the runtime logic core (36 tests passing). These
supersede the "dirty files not attributed" note below — they are now committed.

- `01d6cbf` scaffold: data model, repo structure, packaging, schemas, configs
- `66829ce` confidence model + reconciliation engine (`reconcile/confidence.py`,
  `reconcile/engine.py`, `reconcile/reliability.py`)
- `9b87afd` source adapters (`pipeline/sources/`: edgar, news, podcast_rss,
  company_site) — I/O separated from pure parsers
- `f6f773f` LLM extraction stage (`pipeline/llm/`, `pipeline/extract/`) + OSS research
- `84617fb` derivation & validation engine (`reconcile/derive.py`): hard identities
  (MRR->ARR, round/equity->valuation, subs*ACV->ARR, valuation/ARR->multiple),
  hiring surge/concordance, segment-aware soft benchmark (gated). Added `Derivation`
  model + `SourceType.DERIVED`; confidence model special-cases DERIVED.

Aligned with Codex specs (METHODOLOGY, MCP-SPEC, EVENTS-SPEC) — implementation
matches the documented confidence formula, identities, tools, and event types.

Not yet built (next): storage/IO layer, run.py orchestration, transcribe stage
(must store only short phrases per DATA-POLICY), publish stage (events thresholds
per EVENTS-SPEC), MCP server (per MCP-SPEC), dashboard, A2A.

Strategy/competitive docs authored by Claude Code earlier (also committed):
`COMPETITIVE-ANALYSIS.md`, `OSS-LANDSCAPE.md`, `OSS-DEEP-DIVE.md`,
`STRATEGY-DEEP-DIVE.md`, `GROWTH.md` (later enriched by Codex).

## Dirty Files Not Attributed To Codex In This Log

At the time this handoff file was created, these dirty/untracked files existed but were not part of the Codex documentation/competitive-research pass above:

- `config/metrics.yaml`
- `src/openpitch/models.py`
- `src/openpitch/reconcile/confidence.py`
- `src/openpitch/reconcile/derive.py`
- `tests/test_derive.py`

Treat these as user or Claude Code work unless Mohamed says otherwise.

## Suggested Next-Agent First Step

Before making new edits, run:

```bash
git status --short
```

Then read this file and inspect any file you plan to touch. If implementing the X/social adapter, start from:

- `docs/DATA-POLICY.md`
- `docs/METHODOLOGY.md`
- `src/openpitch/models.py`
- `src/openpitch/pipeline/sources/base.py`
- existing adapters in `src/openpitch/pipeline/sources/`
