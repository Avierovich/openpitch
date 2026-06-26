# Agent Coordination Log

This file is the handoff point for agentic coding tools working in this repo.
Read it before editing, especially when Codex and Claude Code are both active.

## Current Coordination Rules

- Do not revert dirty working-tree changes unless Mohamed explicitly asks.
- Treat unlisted dirty files as user/Claude Code work until proven otherwise.
- Prefer small, source-backed documentation changes over broad rewrites.
- No runtime code changes were made by Codex during the competitive-research/doc pass.
- OpenPitch's trust model remains: public sources, provenance, confidence, auditability, and conservative ToS posture.

## Current State (2026-06-26)

Authoritative snapshot — the dated logs below are historical and may be stale.

- **v0.1.0, functional end-to-end.** 64 tests passing; `ruff check .` clean.
- **Two-level taxonomy:** controlled main category + subcategory + free-text specialty +
  business summary (`pipeline/classify.py` VOCAB: 12 mains / 81 subs incl. `science` and
  `consumer-ai`). `config/taxonomy.yaml` is the generated overlay; `openpitch classify` (re)builds it.
- **Discovery:** news (US + EU/`gl=GB` feeds) + per-sector knowledge backfill (20 sectors),
  public/acquired filtered out, fail-isolated against 503s. `discovered.yaml` ~248 candidates.
- **Reconciliation:** recency stays the headline; an unconfirmed "in talks" valuation also
  surfaces `confirmed_value`; forward-looking revenue targets dropped; contradictions require
  independent public sources.
- **MCP:** 8 read-only tools, now declaring read-only/non-destructive annotations; exposes
  subcategory/specialty/summary.
- **P0 (local) done:** CI + release (PyPI Trusted Publishing) + Pages workflows; CONTRIBUTING/
  SECURITY/CoC/CHANGELOG + issue/PR templates; extraction cache (`data/cache/seen.json`);
  metadata → `Avierovich/openpitch`. Pending: the GitHub/PyPI push + account config.

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

### 2026-06-14 - Brand selection and documentation sync

Codex created five SVG logo options and Mohamed selected option 5, **Terminal Proof**, as the current OpenPitch logo direction.

Files created by Codex:

- `docs/brand/logo-options/01-signal-pitch.svg`
- `docs/brand/logo-options/02-receipt-node.svg`
- `docs/brand/logo-options/03-agent-bridge.svg`
- `docs/brand/logo-options/04-git-radar.svg`
- `docs/brand/logo-options/05-terminal-proof.svg`
- `docs/brand/logo-options/README.md`
- `docs/OPERATIONS.md`
- `docs/RECENT-CHANGES.md`

Files updated by Codex:

- `README.md`
- `docs/LAUNCH-GATES.md`
- `docs/PRD.md`
- `docs/FRD.md`
- `docs/DATA-POLICY.md`
- `docs/V0-SEED-DATASET.md`
- `docs/GROWTH.md`

Main content changes:

- Updated project docs to reflect recent runtime work: MCP tools, static dashboard, event feed, batched extraction, Groq transcription, raw-GitHub data fetching, daily workflow env wiring, and SEC EDGAR fair-access headers.
- Clarified that the 5-company seed is software-test-ready but not launch-grade.
- Added operational guidance for local `.env`, GitHub secrets, pre-push safety, and generated-data separation.
- Updated logo guidance to make Terminal Proof the selected direction.
- Added a post-GitHub-push rule: once clean-machine clone install and MCP startup pass, update the install gate from partial to fully complete.
- Updated dashboard behavior: metric labels must come from `config/metrics.yaml`, and company cards/pages display top-50 rank tiers.

### 2026-06-14 - Dashboard top-50 sourcing, valuation sort, and Groq extraction

Codex updated the dashboard/runtime so the hands-on demo retains the full top-50 view while distinguishing sourced metrics from source-checked profiles.

Files modified by Codex:

- `src/openpitch/pipeline/dashboard.py`
- `src/openpitch/pipeline/run.py`
- `src/openpitch/pipeline/llm/__init__.py`
- `src/openpitch/pipeline/sources/company_site.py`
- `src/openpitch/pipeline/sources/edgar.py`
- `src/openpitch/pipeline/sources/news.py`
- `src/openpitch/pipeline/sources/podcast_rss.py`
- `tests/test_pipeline.py`
- `docs/FRD.md`
- `docs/RECENT-CHANGES.md`

Main content changes:

- Dashboard now defaults to valuation-descending order.
- Dashboard adds a user sort control for valuation, total funding, source coverage, category, and name.
- Dashboard still renders exactly 50 top-50 slots.
- Pending cards are replaced by source-checked company profiles after a broad source run; profiles with no extracted metrics say `source checked; no metric claims yet`.
- Added Groq claim extraction provider behind `OPENPITCH_LLM=groq`.
- Added live-run controls: `--transcriptions`, `--max-source-items`, and `--skip-podcasts`.
- Bounded HTTP source timeouts for EDGAR, news RSS, podcast RSS, and company-site fetches.

Verification performed by Codex:

- Ran `OPENPITCH_LLM=groq .venv/bin/openpitch run --companies 50 --transcriptions 0 --skip-podcasts --max-source-items 6`.
- Result: `Run complete: 50 companies; 3 events.`
- Rebuilt dashboard with `.venv/bin/openpitch build-dashboard`.
- Browser verification at `http://localhost:8765/index.html`:
  - 50 total cards.
  - 50 sourced profile cards.
  - 0 pending cards.
  - 23 profiles with extracted metrics.
  - 27 source-checked profiles without supported metric claims yet.
  - Default sort selected: valuation.
  - Sort-by-name interaction worked, then the page was reset to valuation sort.
- Ran focused checks: `PYTHONPATH=src .venv/bin/python -m pytest tests/test_pipeline.py tests/test_adapters.py` (`16 passed`) and `ruff check` on touched pipeline/test files.

Source reliability notes:

- Several EDGAR searches returned SEC `500 Internal Server Error`; the pipeline continued through news/site extraction. Treat these as external-source reliability findings, not local test failures.
- Podcast RSS was intentionally skipped for the broad run to avoid audio/transcription drag during hands-on testing.

### 2026-06-14 - Corrected top-50 quality issue after hands-on review

Mohamed flagged that the valuation-ranked dashboard missed obvious billion-dollar/high-ARR startups. Codex confirmed the root cause: the broad run used `--companies 50`, which meant the first 50 YAML watchlist rows, not the best 50 companies, and the run path was also overwriting prior sourced profiles with empty profiles when no claims extracted.

Files modified by Codex:

- `src/openpitch/pipeline/run.py`
- `data/seed/claims.json`
- `docs/RECENT-CHANGES.md`
- `AGENTS.md`

Main content changes:

- Live runs now publish a company only when extraction produced claims; source-checked/no-claim runs no longer degrade existing profiles.
- Added `--ids` for targeted live sourcing.
- Added `--extract-sleep` to throttle extraction under provider rate limits.
- Expanded the source-backed seed baseline with Perplexity, Glean, Harvey, ElevenLabs, Scale AI, Mercor, and Runway.

Verification performed by Codex:

- Ran `.venv/bin/python -m json.tool data/seed/claims.json`.
- Ran `.venv/bin/openpitch seed`.
- Ran `.venv/bin/openpitch build-dashboard`.
- Ran `PYTHONPATH=src .venv/bin/python -m pytest` (`45 passed`, 1 warning).
- Browser verification at `http://localhost:8765/index.html` showed valuation sort with top 20 including Anthropic, OpenAI, Anysphere, Thinking Machines, Safe Superintelligence, VAST Data, Scale AI, Cognition, Cerebras, Mistral, Perplexity, ElevenLabs, Harvey, Mercor, Glean, and Cohere.

Important caution:

- The seed baseline uses public source claims and should be audited before committing as canonical data.
- The automated extractor still misses many obvious public metrics; improving source retrieval/extraction quality remains a launch blocker.

### 2026-06-14 - Added data-quality gate and dashboard quality page

Codex added a data-quality report so dashboard coverage problems are visible before launch or push review.

Files modified by Codex:

- `src/openpitch/pipeline/quality.py`
- `src/openpitch/pipeline/dashboard.py`
- `src/openpitch/pipeline/run.py`
- `tests/test_pipeline.py`
- `docs/FRD.md`
- `docs/RECENT-CHANGES.md`
- `AGENTS.md`

Main content changes:

- Added `openpitch quality-report`.
- Writes `data/quality/report.md`.
- Dashboard builds now write `dashboard/dist/quality.html`.
- Dashboard overview now includes a quality banner with critical issue and warning counts.
- Quality report flags:
  - top-50 cards with no metrics;
  - top-50 cards missing valuation;
  - top-50 cards missing ARR / revenue;
  - high-priority watchlist candidates not profiled;
  - single-source core metrics.

Verification performed by Codex:

- Ran `.venv/bin/openpitch quality-report`.
- Ran `.venv/bin/openpitch build-dashboard`.
- Ran `PYTHONPATH=src .venv/bin/python -m pytest` (`46 passed`, 1 warning).
- Browser verification at `http://localhost:8765/index.html` showed:
  - 50 sourced profiles;
  - valuation sort active;
  - quality banner: `51 critical quality issues · 108 warnings`;
  - top cards: Anthropic, OpenAI, Anysphere, Thinking Machines, Safe Superintelligence, VAST Data, Scale AI, Cognition, Cerebras, Mistral.

Current quality status:

- (Historical, 2026-06-13) `data/quality/report.md` reported 51 critical issues and 108 warnings; the quality model and coverage have since changed materially — see Current State above.
- Treat these as launch blockers until the no-metric top-50 cards, missing valuation/ARR gaps, and unprofiled high-priority candidates are reduced intentionally.

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
