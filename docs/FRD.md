# Functional Requirements Document (FRD) / Technical Design

## Project: OpenPitch — Open-Source AI-Agent Alternative to PitchBook

| | |
|---|---|
| **Document version** | 0.1 (Draft) |
| **Date** | 2026-06-13 |
| **Author** | Mohamed Abdulhadi |
| **Status** | Draft for review |
| **Companion doc** | [BRD.md](BRD.md) — business requirements (this FRD implements it) |

> This document specifies *how* OpenPitch is built. It assumes the BRD's decisions: latency-over-coverage thesis, ~50 dynamically-selected AI companies, the full VC metric panel, MCP server as primary interface, static dashboard as secondary, and **zero marginal cost**.

---

## 1. Architecture Overview

OpenPitch is a **git-native data pipeline + read interfaces**. There is no server and no database — the **git repository *is* the database**, the **daily pipeline** runs on free public-repo CI, and **read access** happens through a local MCP server and a static dashboard.

```
                         ┌──────────────────────────────────────────┐
                         │      DAILY PIPELINE (GitHub Actions)      │
                         │                                           │
  Sources ─────────────▶ │  1. Select universe (VC-attention score)  │
  • Podcast RSS          │  2. Collect raw material per company      │
  • News / press         │  3. Transcribe (podcasts w/o transcript)  │
  • SEC EDGAR (Form D)    │  4. Extract claims (LLM, structured)      │
  • Company sites        │  5. Reconcile → resolved values           │
  • Web signals          │  6. Update source reliability             │
                         │  7. Publish (JSON, history, digest, site) │
                         │  8. git commit + push                     │
                         └────────────────────┬─────────────────────┘
                                              │ writes
                                              ▼
                         ┌──────────────────────────────────────────┐
                         │       DATA (git-tracked, in repo)         │
                         │  companies/*.json · history/*.jsonl       │
                         │  sources/registry.json · universe.json    │
                         └───────┬───────────────────────┬──────────┘
                                 │ reads                  │ reads / builds
                                 ▼                        ▼
                   ┌─────────────────────┐     ┌────────────────────────┐
                   │   MCP SERVER (local) │     │  STATIC DASHBOARD      │
                   │  primary interface   │     │  (GitHub Pages)        │
                   │  user's own agent    │     │  secondary / demo      │
                   │  (Claude Code/Codex) │     └────────────────────────┘
                   └─────────────────────┘
```

**Key properties**
- **Idempotent & incremental** — a run re-processes only changed/new material; re-running yields the same result.
- **Append-only history** — values are never destroyed; every change is a new history row and a git commit.
- **Fail-isolated** — one company (or one source) failing does not abort the run.

---

## 2. Technology Stack **[RECOMMENDATION — overridable]**

| Layer | Choice | Rationale |
|---|---|---|
| Language | **Python 3.11+** | Best data/scraping/transcription ecosystem; official MCP SDK exists; single language for contributors |
| Pipeline orchestration | Plain Python modules + a CLI (`typer`) | No heavy framework; easy to read and run locally |
| HTTP | `httpx` | Async, modern |
| Feeds | `feedparser` | Podcast/news RSS |
| Filings | SEC EDGAR full-text search + Form D API | Free, official |
| Transcription | published transcripts first; fallback `pywhispercpp` (whisper.cpp) | Runs free inside CI runner |
| LLM (pipeline) | Provider-abstracted; default **free tier** (Gemini / Groq / OpenRouter free models) | Swappable; keeps cost $0 |
| Structured output | JSON-schema-constrained LLM calls (Pydantic models) | Reliable extraction |
| Storage | JSON + JSON Lines files in git | Zero-cost, diffable, transparent |
| MCP server | Python `mcp` SDK (stdio) | Native to Claude Code/Codex |
| Dashboard | Static site (Vite + vanilla/Preact + a small chart lib) built to `dist/`, served on GitHub Pages | Zero-cost, no backend |
| CI/Schedule | GitHub Actions (cron) | Free & unlimited for public repos |

> **One open choice:** the MCP server could alternatively be TypeScript (most common MCP language). Default is Python for single-language simplicity. Confirm or override.

---

## 3. Data Model (the core)

Everything hangs off four entities: **Claim**, **Resolved Value**, **Company**, **Source**. The design principle (from BRD NFR-06/07): **never store a number without its provenance and confidence, and never overwrite — always version.**

### 3.1 Claim — a single extracted assertion
The atomic unit. One claim = one metric mention from one source.

```jsonc
// data/claims/<company_id>/<claim_id>.json   (or batched JSONL)
{
  "id": "clm_2f9a1c",
  "company_id": "anthropic",
  "metric": "arr",                  // enum, see §3.5
  "value": 100000000,               // normalized numeric
  "unit": "USD",
  "raw_text": "we just crossed a hundred million in ARR",
  "qualifiers": ["run_rate", "rounded"],   // softeners that lower confidence
  "speaker": { "name": "…", "role": "founder" },  // role ∈ founder|exec|investor|journalist|unknown
  "source": {
    "type": "podcast",              // podcast|news|filing|web|social
    "name": "20VC",
    "url": "https://…",
    "locator": "ep1042@00:34:12",   // timestamp for audio, anchor for text
    "published_at": "2026-06-09"
  },
  "extracted_at": "2026-06-13T04:12:00Z",
  "extractor_model": "gemini-2.0-flash",
  "base_confidence": 0.60           // pre-reconciliation prior (§4)
}
```

### 3.2 Resolved Value — the reconciled best estimate
Computed from all current claims for a metric. This is what interfaces read.

```jsonc
{
  "metric": "arr",
  "value": 92000000,                // weighted central estimate
  "unit": "USD",
  "range": { "low": 80000000, "high": 110000000 },
  "as_of": "2026-06-09",            // date of the freshest supporting claim
  "estimate_type": "consensus",     // reported | implied | consensus
  "confidence": 0.62,               // 0–1 (§4)
  "supporting_claims": ["clm_2f9a1c", "clm_71b0e4"],
  "contradiction": false,           // true if high-confidence claims disagree (§5.3)
  "delta": { "previous": 75000000, "change_pct": 22.7, "since": "2026-02-01" },
  "history_ref": "history/anthropic/arr.jsonl"
}
```

### 3.3 Company profile
The aggregate document the dashboard and MCP server serve.

```jsonc
// data/companies/anthropic.json
{
  "id": "anthropic",
  "name": "Anthropic",
  "aliases": ["Anthropic PBC"],
  "website": "anthropic.com",
  "category": "foundation-model",
  "in_universe": true,
  "vc_attention_score": 98.2,       // §6
  "universe_rank": 2,
  "metrics": {
    "arr":       { /* resolved value */ },
    "valuation": { /* resolved value */ },
    "total_funding": { /* … */ },
    "latest_round": { /* … */ },
    "headcount":  { /* … */ }
    // … full panel §3.5
  },
  "last_updated": "2026-06-13"
}
```

### 3.4 History — append-only per metric
One JSONL file per (company, metric). Each line is a resolved-value snapshot. **The git log of these files is the audit trail (BRD NFR-01).**

```
// data/history/anthropic/arr.jsonl
{"as_of":"2026-02-01","value":75000000,"confidence":0.55,"estimate_type":"reported","claim":"clm_…"}
{"as_of":"2026-06-09","value":92000000,"confidence":0.62,"estimate_type":"consensus","claim":"clm_2f9a1c"}
```

### 3.5 Metric registry
Canonical metric definitions (from BRD §4.1.1), each with unit, type, and a **decay constant τ** (how fast confidence ages — §4.4).

| key | label | unit | τ (days) | implied-able? |
|---|---|---|---|---|
| `arr` | ARR / revenue | USD | 120 | yes |
| `revenue_growth` | Growth rate | % | 120 | yes |
| `valuation` | Valuation | USD | 365 | no |
| `total_funding` | Total raised | USD | 730 | no |
| `latest_round` | Latest round | object | 365 | no |
| `revenue_multiple` | Val ÷ ARR | x | 120 | derived |
| `headcount` | Employees | count | 180 | yes |
| `headcount_growth` | HC growth | % | 180 | yes |
| `subscribers` | Customers/users | count | 150 | yes |
| `nrr` | Net revenue retention | % | 240 | no |
| `notable_customers` | Logos | list | 365 | no |

### 3.6 Source registry
Tracks every source and its **learned reliability** (§5.4).

```jsonc
// data/sources/registry.json
{
  "20VC": {
    "type": "podcast", "tier_prior": 0.55,
    "reliability": 0.71,            // learned, updated over time
    "claims_made": 142, "claims_confirmed": 101, "claims_contradicted": 12,
    "last_updated": "2026-06-13"
  }
}
```

---

## 4. Confidence Model

Every resolved value gets a confidence in `[0,1]`. It is **multiplicative** over independent factors, then boosted by corroboration.

```
base_confidence(claim) =
      tier_prior(source.type)        // §4.1
    × speaker_weight(speaker.role)   // §4.2
    × qualifier_penalty(qualifiers)  // §4.3

current_confidence(claim) = base_confidence × decay(age, τ_metric)   // §4.4

resolved_confidence(metric) =
    corroborate( {current_confidence(c) for c in claims} )           // §4.5
```

### 4.1 Source tier priors
| Source type | Prior |
|---|---|
| Regulatory filing (Form D, S-1) | 0.95 |
| Reputable press (The Information, Bloomberg, TechCrunch) | 0.75 |
| Podcast — primary speaker | 0.60 |
| Company blog / press release | 0.65 |
| Web signal (careers, traffic) | 0.50 |
| Social / rumor | 0.30 |

### 4.2 Speaker weight
`founder/CEO 1.0 · CFO/exec 1.0 · investor 0.8 · journalist 0.7 · unknown 0.5`
(A founder stating their own ARR is authoritative-but-biased; pairs with qualifier penalties.)

### 4.3 Qualifier penalties (multiplicative)
`run_rate ×0.9 · rounded ×0.9 · approximate ("about/around") ×0.85 · forward_looking ("on track to") ×0.7 · unconfirmed ×0.6`

### 4.4 Confidence decay
Confidence falls as a figure ages, per-metric (BRD: freshness is the product):
```
decay(age_days, τ) = exp(-age_days / τ)
```
τ from §3.5 — ARR decays fast (τ=120), valuation slowly (τ=365).

### 4.5 Corroboration
Independent agreeing claims raise confidence and tighten the range; disagreeing high-confidence claims trigger a contradiction flag (§5.3). Combine via noisy-OR on agreement:
```
resolved = 1 − Π(1 − cᵢ)   over claims agreeing within tolerance
```
capped at 0.97 (we never assert certainty — BRD NFR-06).

---

## 5. Reconciliation Engine (the hard, valuable part)

Input: all claims for a (company, metric). Output: one Resolved Value + updated history. **Never overwrites; always versions.**

### 5.1 Algorithm
```
1. Gather active claims for (company, metric).
2. Compute current_confidence per claim (§4).
3. Cluster claims by value proximity (metric-specific tolerance, e.g. ±15% for ARR).
4. Dominant cluster = highest summed confidence.
5. value  = confidence-weighted mean of dominant cluster.
   range  = [min, max] across credible (conf ≥ 0.3) claims.
6. estimate_type:
     reported  if dominant cluster has ≥1 direct reported claim
     consensus if multiple independent sources
     implied   if value came from §5.5 derivation (no reported claim)
7. confidence = corroboration over dominant cluster (§4.5).
8. contradiction = true if a non-dominant cluster also has high summed confidence (§5.3).
9. delta vs previous resolved value; append history row if changed.
```

### 5.2 Clustering tolerance per metric
ARR/revenue ±15% · valuation ±20% · headcount ±10% · subscribers ±25%.

### 5.3 Contradiction detection
If two clusters each exceed a confidence floor (e.g. both > 0.5) and lie outside tolerance → `contradiction: true`, both retained, surfaced in interfaces and the digest. *(Example: founder podcast claim vs Form D implication.)* This is a feature, not an error.

### 5.4 Source reliability update (meta-learning)
When a claim is later **confirmed** by a higher-tier source (e.g. a podcast ARR later matches a filing), bump that source's reliability; if **contradicted**, decay it. Bayesian-style:
```
reliability ← (α·confirmed + 1) / (α·(confirmed+contradicted) + 2)
```
`tier_prior` in §4.1 is then blended with the learned `reliability` so trusted sources earn weight over time.

### 5.5 Implied metrics (derive what nobody reported)
When no reported claim exists for an implied-able metric (§3.5), estimate from leading indicators and label `estimate_type: implied` with reduced confidence (cap ~0.45). **v1 ships only the defensible, self-anchored forms:**
- **Implied growth** (v1) — interpolate/extrapolate from the company's *own* dated reported points.
- **Implied momentum** (v1) — qualitative growth-direction from hiring velocity, web-traffic trend, app-store rank (e.g. "strong growth"), *not* a fabricated dollar figure.
- **Implied ARR from cross-company RPE** (**v2, deferred** — Decision 3 §13) — headcount × sector revenue-per-employee is too noisy for a credible point/band in v1.

Each implied value records its derivation method in `supporting_claims` as a synthetic claim so it's auditable.

---

## 6. VC-Attention Scoring (universe selection)

Recomputed every run to pick the dynamic top-50 (BRD §4.1.2). **ARR is excluded as a selector.**

```
attention =  0.40 · norm(valuation)
           + 0.30 · funding_recency_size
           + 0.20 · investor_quality
           + 0.10 · momentum
```
- `norm(valuation)` — min-max/log-normalized latest valuation across candidates.
- `funding_recency_size` — round size × recency decay (recent raises score higher).
- `investor_quality` — score from a curated tier list of top funds backing the company.
- `momentum` — normalized buzz/traffic/hiring trend.

**Selection:** rank all candidates, take top 50. Track **entries/exits** vs previous run as their own signal (surfaced in the digest: *"X entered the top 50"*). Weights live in `config/scoring.yaml` so contributors can tune them. Candidate pool seeded from a maintained watchlist + anything appearing in collected funding news.

---

## 7. Pipeline Stages (the agent loop)

Each stage is an independent, resumable module. Orchestrated by `pipeline/run.py`.

| # | Stage | Input | Output | Notes |
|---|---|---|---|---|
| 1 | **Select universe** | watchlist + funding signals | `universe.json`, ranks | §6; logs entries/exits |
| 2 | **Collect** | universe | raw items (transcripts, articles, filings) cached by hash | per-source adapters; respects robots.txt/ToS |
| 3 | **Transcribe** | podcast audio w/o transcript | text | published transcript first; else whisper.cpp; bounded N/run |
| 4 | **Extract** | raw text | Claims | LLM structured output; one call per item; dedup by hash |
| 5 | **Reconcile** | claims | Resolved Values + history rows | §5 |
| 6 | **Score sources** | confirm/contradict events | updated `registry.json` | §5.4 |
| 7 | **Publish** | resolved values | `companies/*.json`, history JSONL, **`events/*.jsonl` + `events.xml`**, `digest/YYYY-MM-DD.md`, dashboard build | emits typed events (§8.5) for every material change |
| 8 | **Commit** | all changes | git commit + push | commit message = digest summary |

**Source adapters** implement a common interface (`fetch(company) -> list[RawItem]`) so adding a source = one file. v1 adapters: `podcast_rss`, `news`, `edgar`, `company_site`.

**MENA sourcing (honest reality).** The global freshness engine leans on SEC EDGAR + English podcasts + US tech press — **none of which map cleanly to MENA** (BRD §4.1; COMPETITIVE-ANALYSIS.md §6). The `edgar` adapter is US-only; English founder-podcast metric leaks are rarer. MENA coverage therefore needs **region-specific adapters** (roadmap):
- `mena_news` — regional outlets (Wamda, Menabytes, Magnitt blog, Zawya) RSS/press.
- `freezone_registry` — best-effort signals from ADGM / DIFC / DMCC public registries.
- `mena_podcasts` — regional shows (config-driven, same `podcast_rss` machinery).

Expectation set explicitly: **MENA launches at lower confidence/coverage**, clearly labeled in the data, rather than overstated. This is a known, documented trade-off, not a defect.

**Rich-sources roadmap (BRD pillar 2 / BR-26).** Source diversity is a scaling moat single-source rivals can't match — *if curated for signal.* Beyond the v1 four, candidate adapters (add only when each measurably lifts confidence/coverage): GitHub activity, job boards (hiring velocity), app-store ranks, Product Hunt, web-traffic trends, YouTube, earnings/press. The confidence model (§4.1, §5.4) **auto-down-weights noisy sources**, so adding a weak source degrades gracefully rather than polluting estimates. **Sequencing note:** four credible sources that produce real contradictions beat twelve noisy ones — rich sources are a *post-PMF scaling* advantage, not a launch requirement (STRATEGY-DEEP-DIVE §7.2).

**Caching/incrementality:** every fetched item keyed by content hash; unchanged items skip extraction. Keeps usage under free-tier limits (BRD §9.1).

---

## 8. MCP Server (primary interface)

Local stdio server (BRD §4.1.4). Reads the git-tracked data; **the user's own agent does all reasoning** (zero project cost). Ships with a `claude_desktop_config`/Claude Code install snippet in the README.

### 8.1 Tools
| Tool | Args | Returns |
|---|---|---|
| `list_companies` | `filter?`, `sort_by?`, `limit?` | ranked companies w/ headline metrics |
| `get_company` | `id` | full profile (all resolved metrics) |
| `get_metric` | `company_id`, `metric`, `with_history?` | resolved value (+ history series), with provenance & confidence |
| `compare_companies` | `ids[]`, `metrics[]` | side-by-side table |
| `what_moved` | `since?` | changes since date (deltas, new rounds, contradictions, universe entries/exits) |
| `get_provenance` | `company_id`, `metric` | the underlying claims + sources for a figure |
| `get_events` | `since?`, `type?`, `company_id?`, `min_confidence?` | filtered event stream (§8.5) for in-loop agents |
| `search` | `query` | companies/metrics matching free text |

**Every numeric response includes** `value, range, confidence, estimate_type, as_of, sources[]` — provenance is never stripped (BRD NFR-07). The server is read-only.

---

## 8.5 Events & Integration Layer

OpenPitch is a **composable primitive** (BRD §4.1.5): pull via MCP (§8) **plus push** via events. During publish (stage 7), any material change to a resolved value produces a typed event.

### 8.5.1 Event taxonomy
| Type | Fires when |
|---|---|
| `funding_round` | a new round is detected |
| `valuation_update` | valuation changes beyond tolerance |
| `metric_update` | any tracked metric materially changes (carries `metric`) |
| `metric_threshold_crossed` | a metric crosses a notable threshold (e.g. ARR > $100M, headcount > 500) |
| `universe_entry` / `universe_exit` | a company joins/leaves the dynamic top-50 |
| `contradiction_flagged` | high-confidence claims disagree (§5.3) |
| `new_notable_customer` / `leadership_change` | logo / key hire-departure detected |

### 8.5.2 Event schema (stable, versioned)
```jsonc
// data/events/2026-06-13.jsonl  (appended to rolling data/events/feed.jsonl)
{
  "id": "evt_8a1f",
  "schema_version": "1.0",
  "type": "valuation_update",
  "company_id": "anthropic",
  "company_name": "Anthropic",
  "summary": "Anthropic valuation $40B → $60B",
  "payload": { "metric": "valuation", "previous": 4.0e10, "current": 6.0e10, "change_pct": 50.0 },
  "confidence": 0.82,
  "estimate_type": "reported",
  "sources": [{ "name": "The Information", "url": "https://…", "published_at": "2026-06-13" }],
  "detected_at": "2026-06-13T05:00:00Z"
}
```
JSON Schemas for events and resolved values live in `schemas/` and are published with the dashboard so integrators can validate. **Schema changes are versioned; breaking changes bump `schema_version`** (BRD BR-22).

### 8.5.3 Channels (all zero-cost)
| Channel | Mechanism | Consumer |
|---|---|---|
| MCP | `get_events` tool + `events` resource (§8.1) | in-loop AI coding agents |
| Raw feed | `data/events/feed.jsonl` via raw.githubusercontent | any script/agent (poll) |
| RSS/Atom | `events.xml` built in stage 7, served on Pages | press tools, no-code (Zapier/IFTTT), newsletter agents |
| Webhook | GitHub-native commit/release webhooks | push to subscriber endpoints |

### 8.5.4 Consumer filter recipes (BRD personas)
```
content_agent:   all events                              → expand to newsletter copy
press_workflow:  type∈{funding_round,valuation_update}
                 AND confidence ≥ 0.8                     → alert journalist to confirm
investor_outbound: type∈{universe_entry,
                   metric_threshold_crossed}              → trigger targeted outreach
```
`docs/integrations/` ships these as copy-paste **integration recipes** (one per persona) so adopters wire in fast.

## 8.6 API keys — who needs what

There are **two entirely separate LLM roles**; they never share a key, and the end user supplies nothing.

| | **Pipeline LLM** (Gemini Flash) | **Consumption LLM** |
|---|---|---|
| Job | extract claims, reconcile | answer the user's question in-agent |
| Runs in | *maintainer's* GitHub Actions, daily | the *user's* Claude Code / Codex |
| Key provided by | **maintainer** — one Gemini key as a repo GitHub Secret | **nobody** — the user's existing agent |
| Cost borne by | free tier (maintainer account) | the user's existing subscription |

**The MCP server makes zero LLM calls of its own.** By the time a user queries OpenPitch, extraction/reconciliation already ran centrally and was committed as plain JSON; the server is a dumb data reader, and the "intelligence" at query time is the **user's own agent** reasoning over pre-computed data.

```
MAINTAINER (once/day, central)            USER (on demand, local)
GitHub Action → Gemini extracts    git    Claude Code/Codex asks → MCP reads
→ commits clean JSON ──────────────────▶  JSON → user's agent phrases answer
   ↑ Gemini key lives here ONLY              ↑ NO key, NO Gemini, NO LLM call by MCP
```

**End-user install = add the MCP server to config. No signup, no key, no cost.**
The *only* party needing a Gemini key is the maintainer (or an advanced user who forks and self-hosts their own daily pipeline instead of consuming the published data). This is documented prominently in the README.

## 8.7 A2A (agent-to-agent) interface — OpenPitch as a delegate agent

MCP exposes OpenPitch as a **tool**; A2A exposes it as an **agent** other agents can discover and delegate to (BRD §4.1.6). The two are **complementary** (MCP = vertical tool access; A2A = horizontal agent coordination), which is the emerging default for agent systems.

- **Agent Card** (`/.well-known/agent.json`) advertising OpenPitch's skills, e.g. `research_company`, `compare_companies`, `whats_moved`, `find_contradictions`.
- A thin A2A server wraps the **same read layer** the MCP server uses (the git-tracked data) — no new data path, and still **zero LLM calls of its own** for pure-data skills.
- Hostable as a static Agent Card + a lightweight endpoint; for the fully-static/zero-cost posture, the Agent Card + JSON feed can satisfy discovery and simple delegation, with a richer hosted A2A endpoint as an optional add-on.

This turns OpenPitch from "a data source you query" into "a specialist agent your agent hires" — and is, to our knowledge, the first **free, open A2A startup-intelligence agent**. Implemented behind the same data contract, so MCP and A2A never diverge.

## 8.8 Ease of implementation (a first-class design goal — BRD pillar 1)

Frictionless adoption is an explicit requirement (BR-25), not a nicety. Target: **working in an agent in <60s, no key, no signup.** Surfaces, cheapest-first:

| Surface | Effort for adopter |
|---|---|
| MCP server | one line in agent config (`uvx openpitch-mcp`) |
| A2A agent | point an agent at the Agent Card URL |
| Raw JSON | fetch `data/companies/*.json` from raw GitHub |
| RSS/Atom events | subscribe — works with no-code tools |

A measured **<60s "first answer"** is tracked as a product metric; the README leads with a GIF proving it.

## 9. Dashboard (secondary interface)

Static site built from the same JSON, deployed to GitHub Pages (BRD §4.1.3). Two views:
- **Overview** — sortable/filterable grid of all 50 × key metrics; "What moved today" banner.
- **Detail (on select)** — full metric panel, per-metric history chart, provenance + confidence per figure, contradiction badges.

Built in stage 7; no runtime backend.

---

## 10. Repository Structure

```
openpitch/
├── README.md                  # the pitch + MCP install snippet + dashboard link
├── docs/                      # BRD, FRD, COMPETITIVE-ANALYSIS, GROWTH, competitive-matrix.xlsx, integrations/
├── scripts/                   # build_competitive_matrix.py (regenerates the xlsx)
├── schemas/                   # versioned JSON Schema (events, resolved values)
├── config/
│   ├── watchlist.yaml         # candidate companies
│   ├── scoring.yaml           # VC-attention weights
│   └── metrics.yaml           # metric registry + τ
├── data/                      # THE DATABASE (git-tracked)
│   ├── universe.json
│   ├── companies/*.json
│   ├── claims/<company>/*.json
│   ├── history/<company>/<metric>.jsonl
│   ├── sources/registry.json
│   ├── events/feed.jsonl + YYYY-MM-DD.jsonl + events.xml   # §8.5 push layer
│   └── digest/YYYY-MM-DD.md
├── pipeline/
│   ├── run.py                 # orchestrator (CLI)
│   ├── sources/               # adapters (podcast_rss, news, edgar, company_site)
│   ├── transcribe/
│   ├── extract/               # LLM extraction + schemas
│   ├── reconcile/             # confidence + reconciliation engine
│   ├── score/                 # VC-attention + source reliability
│   ├── publish/               # writers + digest + dashboard build
│   └── llm/                   # provider abstraction (free-tier swappable)
├── mcp_server/
│   └── server.py              # MCP tools (§8)
├── dashboard/                 # static site source → builds to dist/
└── .github/workflows/
    └── daily.yml              # cron: run pipeline, commit, deploy Pages
```

---

## 11. Daily Workflow (CI)

```yaml
# .github/workflows/daily.yml (sketch)
on:
  schedule: [{ cron: "0 5 * * *" }]   # daily 05:00 UTC
  workflow_dispatch:
jobs:
  refresh:
    runs-on: ubuntu-latest            # free for public repos
    steps:
      - checkout
      - setup-python
      - pip install -e .
      - run: python -m pipeline.run --all      # stages 1–7
        env: { LLM_API_KEY: ${{ secrets.LLM_API_KEY }} }
      - run: python -m pipeline.run --build-dashboard
      - commit & push data/ + dist/            # git is the DB
      - deploy GitHub Pages
```
Concurrency-guarded so runs don't overlap; per-company failures logged, not fatal.

---

## 12. Non-Functional Implementation Notes

| Concern | Approach |
|---|---|
| **Zero cost** (NFR-03) | public-repo CI, Pages, local MCP, BYO agent, free-tier pipeline LLM, bounded volume + caching |
| **Rate limits** | per-provider throttle + backoff; cap episodes/articles per run; incremental processing |
| **Legal/ToS** (NFR-02) | robots.txt honored; official APIs (EDGAR) and published transcripts preferred; no auth-walled scraping |
| **Reproducibility** | deterministic given inputs; cached raw items committed or hashed; pinned deps |
| **Extensibility** | new source = one adapter file; weights/metrics in `config/` |
| **Auditability** | every figure → claims → sources; git history = full audit log |
| **Honest uncertainty** | confidence capped < 1; ranges always shown; implied/consensus labeled |

---

## 13. Resolved Technical Decisions

| # | Decision | Choice | Rationale |
|---|---|---|---|
| 1 | MCP server language | **Python** | One language across pipeline + server = low contributor friction; mature `FastMCP` SDK |
| 2 | Pipeline LLM provider | **Gemini Flash** (default, swappable via `pipeline/llm/`) | Long context for transcripts, generous free tier, native structured output; Groq/Ollama as escape hatches |
| 3 | Implied ARR | **Not shipped in v1** | Cross-company revenue-per-employee is too noisy. v1 ships self-anchored estimates + qualitative growth-direction signals only; hard implied-ARR (versioned RPE bands, wide range, conf ≤ 0.4) deferred to v2 |
| 4 | Watchlist seeding | **Hand-seed ~80 in `config/watchlist.yaml`**, scoring picks top 50 | Concrete starting universe; funding-news discovery grows it over time |
| 5 | Dashboard framework | **Astro + interactive islands** (`uPlot` for charts) | Zero-JS-by-default static output for Pages, islands only where needed (grid, charts) |

**Note on Decision 3:** this is the one with credibility stakes. v1 must not present a fabricated dollar ARR derived from headcount — it would undermine the provenance pitch. "Reported + how fresh + growth direction" is the trustworthy v1 posture.

---

## 14. Traceability (FRD → BRD)

| BRD requirement | FRD section |
|---|---|
| BR-01 universe of ~50 | §6, §7-stage1 |
| BR-02 daily collection | §7, §11 |
| BR-03 podcast ingest/transcribe/extract | §7-stages 2-4, §2 |
| BR-04 public sources | §7-stage2 adapters |
| BR-05 provenance | §3.1, §8, §12 |
| BR-06 confidence | §4 |
| BR-07 history | §3.4 |
| BR-08 reconcile, no overwrite | §5 |
| BR-09 implied metrics | §5.5 |
| BR-10 consensus + range | §5.1 |
| BR-11 source reliability | §5.4 |
| BR-12 confidence decay | §4.4 |
| BR-13 digest | §7-stage7 |
| BR-14 NL query | §8 (MCP) |
| BR-15/16 dashboard | §9 |
| BR-17/18 MCP server | §8 |
| BR-19 zero cost | §2, §11, §12 |
| BR-20 emit events | §7-stage7, §8.5.1 |
| BR-21 multi-channel | §8.5.3 |
| BR-22 versioned schemas | §8.5.2, §10 (`schemas/`) |
| BR-23 event filtering | §8.1 `get_events`, §8.5.4 |

---

*End of FRD v0.1 — draft for review.*
