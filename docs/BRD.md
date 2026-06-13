# Business Requirements Document (BRD)

## Project: OpenPitch — Open-Source AI-Agent Alternative to PitchBook

| | |
|---|---|
| **Document version** | 0.1 (Draft) |
| **Date** | 2026-06-13 |
| **Author** | Mohamed Abdulhadi |
| **Status** | Draft for review |
| **Working name** | OpenPitch *(confirmed)* |

> **Note on assumptions:** This draft encodes decisions made during scoping. Items marked **[ASSUMPTION]** are my best inference and should be confirmed or corrected.

---

## 1. Executive Summary

OpenPitch is an open-source AI research agent that produces **fresh, fully-sourced, confidence-scored intelligence on the top 50 AI companies**, with a focus on financial and growth metrics (ARR, valuation, funding rounds, headcount).

Unlike incumbent platforms (PitchBook, CB Insights), which rely on slow human verification and therefore lag fast-moving private markets, OpenPitch's core thesis is **latency, not coverage**: for hypergrowth AI startups, a fresh-but-probabilistic figure — properly contextualized with its source and confidence — is more useful than a verified-but-stale one.

The agent mines non-traditional sources (notably **podcasts**, where founders disclose metrics weeks before any database) alongside public filings, news, and web signals. It runs on a **daily schedule**, publishes version-tracked profiles, and surfaces a **"what moved today" digest**. All data carries provenance, a confidence score, and a tracked history of how each figure evolved.

Critically, OpenPitch is designed as a **composable primitive, not a destination** — an open data/event layer that *other people's AI agents build on top of*. Beyond on-demand lookups (pull), it **emits typed, confidence-scored events** (push) when something material changes, so downstream agents can react: a content agent turns a valuation update into a newsletter, a press workflow gets alerted to a confirmed round, a growth investor's outbound agent triggers on a startup entering the radar.

---

## 2. Business Objectives & Goals

| # | Objective | Success looks like |
|---|---|---|
| O1 | Demonstrate a credible, fresher alternative to incumbent private-market data for a focused niche | Data points routinely newer than CB Insights for the covered 50 companies |
| O2 | Make AI reasoning visible and trustworthy via provenance + confidence | Every published figure has a clickable source, confidence score, and history |
| O3 | Ship a defensible open-source project that attracts a community | GitHub stars, contributors, and forks; inbound interest |
| O4 | Serve as a high-signal portfolio/credibility asset for the author | Used as evidence of AI-agent, data-engineering, and product skill |
| O5 | Be a **composable building block** other AI agents/workflows integrate with | Third parties wire OpenPitch (pull + event push) into their own agents (content, press, investing) |

### Non-goals
- Replicating PitchBook's proprietary, human-verified deal-terms database.
- Global coverage of all startups.
- Guaranteeing 100% accuracy of any single figure (the product is **transparently probabilistic**).

---

## 3. Background & Problem Statement

Private-market data is self-reported, unregulated, and incomplete. Incumbents add value through human verification — which is accurate but **slow and expensive (~$20k+/yr)**. For AI companies growing 2–4x annually, a metric verified six months ago can be off by multiples.

Meanwhile, **real, current signals exist in the open**: founders state ARR on podcasts, hiring velocity reveals growth, SEC Form D filings disclose raises, and headcount trends are public. These signals are scattered, unstructured, and contradictory — **exactly the problem an AI agent is suited to solve.**

**The gap:** No accessible tool continuously mines these fresh, open signals and presents them with honest provenance and confidence.

---

## 4. Project Scope

### 4.1 In Scope
- Coverage of **~50 AI companies selected by active VC interest** — i.e., the AI companies attracting the most venture-capital attention and funding activity (recent/rumored rounds, investor focus, notable backers). The list is **dynamic**: companies enter or exit as VC attention shifts, consistent with the project's daily-refresh thesis. *(Metrics captured per company: §4.1.1. Selection criteria: §4.1.2.)*
- Automated **daily** data collection from open sources.
- **Podcast ingestion**: transcription + metric extraction.
- Public-source ingestion: SEC EDGAR (Form D), news/press, company websites/careers pages.
- **Reconciliation engine**: matching new claims to stored values, scoring confidence, flagging deltas and contradictions, never silently overwriting.
- **Implied/derived metrics** from leading indicators (hiring, headcount, traffic) when no figure is reported.
- **Consensus estimates** with ranges when sources disagree.
- **Source reliability scoring** that improves over time.
- **Confidence decay** as data ages.
- Version-tracked storage (git history as the audit log).
- A **"what moved today" digest**.
- A **natural-language query interface** over the dataset.
- An **MCP server** (primary interface) exposing the dataset as tools any AI coding agent (Claude Code, Codex) can call in-agent — runs locally on the user's machine; the user brings their own agent/LLM (see §4.1.4).
- A **read-only dashboard** (secondary interface) that displays all companies and metrics in an overview, and lets the user **select/filter/drill down** into a single company's full profile, metric history, and sources (see §4.1.3).
- An **events / integration layer**: material changes emitted as typed, confidence-scored events on multiple free channels (MCP, JSONL feed, RSS/Atom, webhooks) with stable, versioned schemas, so third-party agents can subscribe and react (see §4.1.5).

#### 4.1.1 Metrics captured per company
The agent tracks the **broad panel of metrics a VC evaluates for a growth/late-stage company** — not a single figure. Each metric below is stored with its value, provenance, confidence score, and full history.

**Financial / funding**
- ARR / revenue (and run-rate)
- Revenue growth rate (YoY, QoQ)
- Valuation (last round + implied)
- Total funding raised
- Latest round: stage, amount, date, lead + notable investors
- Revenue multiple (valuation ÷ ARR)
- Burn rate / runway *(when signalled)*
- Gross margin *(when signalled)*

**Customers / usage**
- Number of subscribers / customers / users (and DAU/MAU where relevant)
- Notable / enterprise logos
- Net revenue retention (NRR) / churn *(when available)*
- Free-to-paid conversion *(when available)*

**Team / talent**
- Headcount (employees) and headcount growth
- Hiring velocity / open roles
- Key hires & departures (talent flow)

**Product / market**
- Product launches & major releases
- Market / category positioning and share of conversation
- Web traffic and app-store rank trajectory
- Developer signals (e.g., GitHub activity) for dev-tooling companies

> Not every metric is public for every company. Where a metric is unreported, the agent attempts an **implied estimate** from leading indicators (see BR-09) and labels it accordingly.

#### 4.1.2 "Top 50" selection criteria **[CONFIRMED]**
The covered set is **dynamic** — recomputed on the refresh cycle, with entries/exits tracked as their own signal (faster, more recent data is the product's core value, so the list itself must move).

Selection is driven by a composite **"VC-attention score,"** weighted toward **publicly observable signals that actually move** — deliberately **not** ARR:

| Signal | Weight role | Rationale |
|---|---|---|
| **Latest valuation** | Primary | Most consistently reported; direct readout of VC conviction |
| **Funding recency & size** | Primary | Observable as discrete events (announcements, Form D); the natural trigger for a dynamic list |
| **Investor quality / buzz** | Secondary | Backing by top-tier funds = the "VCs are looking into it" signal |

**ARR is explicitly excluded as a selector** to avoid a circular dependency (ARR is a primary *output* of the agent and is rarely observable in real time). ARR remains a **core tracked metric** per §4.1.1 — a headline result *within* the list, not the gate into it. Exact scoring weights and entry/exit thresholds deferred to the technical spec.

#### 4.1.3 Dashboard (secondary interface) **[CONFIRMED]**
The dashboard is the **public storefront/demo** — the screenshot in the README, the surface for non-CLI users — not the primary consumption channel (that's the MCP server, §4.1.4). It uses a **"show everything, then select" model**:

- **Overview view** — a master grid of all ~50 companies against their key metrics (ARR/implied, valuation, latest round, headcount, growth), **sortable and filterable**, with the **"what moved today"** changelog surfaced at the top.
- **Detail view (on select)** — selecting a company opens its full profile: the complete metric panel (§4.1.1), a **history chart per metric**, and **provenance + confidence for every figure**.
- **Filtering/selection** — the user narrows by company, metric, stage, or recency rather than being shown a single pre-baked view.

**Implementation principle:** a **read-only static dashboard generated from the git-tracked data** (deployable free, e.g. GitHub Pages), preserving the "git is the database" model (NFR-01) and the zero-cost constraint (NFR-03).

#### 4.1.4 MCP server (primary interface) **[CONFIRMED]**
The **primary** way target users consume OpenPitch is an **MCP server** they install and run **locally** (stdio), plugged into their existing AI coding agent (Claude Code, Codex). Example in-agent experience:

> *"What's Mistral's latest ARR and who led their last round?"* → the OpenPitch MCP tool returns the figure with provenance, confidence, and history, inline in the agent.

- Exposes the git-tracked dataset as callable tools (e.g., lookup-company, compare-companies, what-moved-today, query-metric-history).
- **Runs on the user's machine** — there is no hosted service to operate.
- **The user brings their own agent/LLM**, so all consumption-side reasoning is paid for by the user's existing subscription, not the project.

This channel is what makes the product native to its audience and is central to the zero-cost model (§9).

#### 4.1.5 Events & integration layer **[CONFIRMED]**
OpenPitch is a **composable primitive** supporting two interaction modes:
- **Pull** — agents query on demand (MCP server, §4.1.4).
- **Push** — when something material changes, OpenPitch **emits a typed, confidence-scored event** that downstream agents subscribe to and act on.

**Event channels (all zero-cost):**

| Channel | Consumer |
|---|---|
| MCP tool/resource (`get_events`) | AI coding agents polling in-loop |
| `events/feed.jsonl` in the repo | any script/agent reading raw GitHub |
| RSS/Atom feed on Pages | press tools, no-code automation, newsletter agents |
| GitHub-native webhooks (commit/release) | push notifications to subscribers |

Each event carries **type, company, before→after payload, confidence, estimate_type, and sources**, with a **`schema_version`** and a published JSON Schema so integrations are stable. Downstream consumers filter by type/confidence to get exactly the events they care about.

**Representative integration use cases:**

| Integrator | Subscribes to | Acts by |
|---|---|---|
| Content / newsletter agent | all material events | expanding a valuation/ARR update into newsletter copy |
| Press / PR workflow | `funding_round`, `valuation_update` with **confidence ≥ 0.8** | alerting a journalist to reach the company for confirmed commentary |
| Growth-investor outbound agent | `universe_entry`, `metric_threshold_crossed` | triggering targeted outreach to a newly-qualifying startup |

### 4.2 Out of Scope (initial release)
- Companies beyond the top-50 list.
- Proprietary/paid data sources.
- Real-time (sub-daily) updates.
- Aggressive scraping of ToS-protected platforms (e.g., LinkedIn at scale).
- A **server-backed application** with user accounts, authentication, or write access (the dashboard is read-only and static — see §4.1.3).
- Investment advice or recommendations.

### 4.3 Future / Phase 2 candidates
- Investor co-investment graph; talent-flow tracking; valuation sanity-checks vs peers; expanded coverage; hosted UI; email newsletter distribution.

---

## 5. Stakeholders

| Stakeholder | Role / Interest |
|---|---|
| Project author (Mohamed) | Owner, developer, maintainer |
| Open-source contributors | Extend sources, fix data, add features |
| **Primary end users — developers using AI coding agents (Claude Code, Codex)** | Consume OpenPitch intelligence **in-agent via the MCP server**; bring their own agent/LLM |
| Secondary users — founders/VCs/analysts/researchers | Browse the static dashboard / digest |
| **Integrators — builders wiring OpenPitch into their own agents** | Consume pull data + event feed downstream (content/newsletter agents, press/PR workflows, growth-investor outbound) |
| Data sources (podcasts, filings, news) | Upstream inputs; ToS compliance required |
| LLM/API providers | Underlying model + transcription services |

---

## 6. Business Requirements

### 6.1 Functional (business-level)

| ID | Requirement | Priority |
|---|---|---|
| BR-01 | The system shall maintain profiles for the defined set of ~50 AI companies. | Must |
| BR-02 | The system shall collect data automatically on a daily schedule. | Must |
| BR-03 | The system shall ingest podcast audio, transcribe it, and extract metric claims. | Must |
| BR-04 | The system shall ingest public filings, news, and web signals. | Must |
| BR-05 | Every data point shall carry provenance (source, date, link/timestamp). | Must |
| BR-06 | Every data point shall carry a confidence score. | Must |
| BR-07 | The system shall track the full history of each metric over time. | Must |
| BR-08 | The system shall reconcile conflicting claims rather than overwrite, flagging deltas and contradictions. | Must |
| BR-09 | The system shall derive implied growth indicators when no metric is reported. | Should |
| BR-10 | The system shall produce consensus estimates with ranges when sources disagree. | Should |
| BR-11 | The system shall score and adapt source reliability over time. | Should |
| BR-12 | Confidence shall decay as a data point ages. | Should |
| BR-13 | The system shall generate a daily "what moved today" digest. | Should |
| BR-14 | Users shall be able to query the dataset in natural language. | Could |
| BR-15 | The system shall provide a dashboard that displays all companies/metrics in an overview and lets the user select/filter/drill into a single company's full profile, metric history, and sources. | Should |
| BR-16 | The dashboard shall be read-only and generated from the git-tracked data (static, free hosting). | Should |
| BR-17 | The system shall provide a locally-run MCP server exposing the dataset as tools callable from AI coding agents (Claude Code, Codex). | Must |
| BR-18 | The MCP server shall require no hosted backend and shall rely on the user's own agent/LLM for reasoning (zero consumption-side cost to the project). | Must |
| BR-19 | The entire system shall operate at **zero marginal cost to the maintainer**, using only free tiers (public-repo CI, free static hosting, free-tier/BYO LLM, local MCP execution). | Must |
| BR-20 | The system shall emit typed, confidence-scored **events** when material changes occur (new round, valuation/ARR/metric update, threshold crossed, universe entry/exit, contradiction). | Must |
| BR-21 | Events shall be published on multiple free channels (MCP, JSONL feed, RSS/Atom, webhooks) so third-party agents can subscribe. | Must |
| BR-22 | Events and data shall expose **stable, versioned schemas** (published JSON Schema) so downstream integrations don't break. | Must |
| BR-23 | Consumers shall be able to **filter events** by type, company, and minimum confidence. | Should |

### 6.2 Non-Functional

| ID | Requirement |
|---|---|
| NFR-01 | **Transparency** — all data and history publicly inspectable (git-tracked). |
| NFR-02 | **Legal/ethical compliance** — respect source ToS and robots.txt; favor open/legitimate sources. |
| NFR-03 | **Zero marginal cost** — the project must run entirely on free tiers (see §9.1): public-repo CI for compute, free static hosting, free-tier or bring-your-own LLM, locally-run MCP server. No paid infrastructure. |
| NFR-04 | **Reproducibility** — anyone can clone and run the pipeline. |
| NFR-05 | **Extensibility** — adding a new source is straightforward for contributors. |
| NFR-06 | **Honest uncertainty** — the product never presents a probabilistic figure as fact. |
| NFR-07 | **Auditability** — every figure traceable to its originating source. |

---

## 7. Success Metrics / KPIs

- **Freshness:** % of metrics newer than incumbent public references.
- **Coverage:** % of the 50 companies with a current ARR/valuation estimate (reported or implied).
- **Provenance integrity:** % of data points with a valid, linkable source (target: 100%).
- **Community:** GitHub stars, forks, contributors, issues.
- **Reliability calibration:** accuracy of confidence scores when figures are later confirmed.
- **Engagement:** digest subscribers / consumers (if distributed).

---

## 8. Assumptions

- [A1] **Metrics captured per company are confirmed** — the broad VC panel (ARR, subscribers, headcount, valuation, funding, etc.) per §4.1.1. Each carries provenance, confidence, and history.
- [A1b] **Resolved** — the 50 are a **dynamic** list selected by a composite VC-attention score (valuation + funding activity + investor quality; **not** ARR), per §4.1.2. Exact scoring weights deferred to the technical spec.
- [A2] Founders/operators disclose enough metrics across public sources to make the agent useful.
- [A3] Open sources + bounded transcription are sufficient; no paid data required for v1.
- [A4] **Daily** refresh is the v1 cadence. Rationale: underlying signals (podcasts, rounds) arrive slowly, so the freshness value-curve is logarithmic — quarterly→daily is the entire win vs incumbents; daily→hourly is marginal; sub-hourly is net-negative (source-ToS risk, rate-limit burn, event noise) for no business gain. A cheap intra-day *funding/news fast-lane* (every 6–8h, no transcription) is a documented **future** option, added only on demand.
- [A5] Users value contextualized estimates over false precision.
- [A6] Free-tier LLM + transcription capacity is sufficient for ~50 companies on a daily cadence (bounded volume + caching keep usage under limits).
- [A7] Target users already run an AI coding agent (Claude Code/Codex) and will install a local MCP server.

## 9. Constraints

- **Zero budget — hard constraint.** The project must run at zero marginal cost to the maintainer (see §9.1).
- Legal/ToS limits on scraping certain platforms.
- LLM/transcription accuracy and **free-tier rate limits**.
- Single maintainer initially — scope must stay focused.

### 9.1 Zero-cost operating model
Every cost center is pushed to a free tier or onto the user's side:

| Cost center | Zero-cost approach |
|---|---|
| Compute / scheduling | GitHub Actions — free & unlimited for **public** repos |
| Data storage | The git repo *is* the database |
| Dashboard hosting | GitHub Pages — free for public repos |
| MCP server hosting | None — runs **locally** on the user's machine (stdio) |
| Consumption-side LLM | **User brings their own agent/LLM** (Claude Code/Codex) — $0 per query to the project |
| Pipeline-side LLM | Free-tier API keys (e.g., Gemini/Groq) via GitHub Secrets, with bounded volume + caching |
| Transcription | Prefer already-published transcripts (Apple/YouTube/show sites); fallback `whisper.cpp` inside the free Actions runner |

**Primary risk:** free-tier rate limits on the daily pipeline. **Mitigation:** small fixed universe (~50 companies), bounded episodes/run, caching, and incremental (changed-only) processing.

## 10. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Data inaccuracy damages credibility | High | Provenance + confidence + ranges; never assert false precision |
| Source ToS / legal exposure | High | Use open/legitimate sources; respect robots.txt; document sourcing |
| Transcription/LLM cost overruns | Medium | Bound episodes/run; cache; cheap models for extraction |
| Scope creep beyond 50 companies | Medium | Enforce niche; defer expansion to Phase 2 |
| Low community adoption | Medium | Strong README pitch, "what moved today" growth loop, shareable contradiction findings |
| Source blocking / rate limits | Medium | Backoff, rotate sources, graceful degradation |

## 11. Dependencies

- LLM provider (extraction, reconciliation, Q&A).
- Speech-to-text (podcast transcription).
- Public data sources: SEC EDGAR, podcast RSS feeds, news/press, company sites.
- Hosting/scheduling (e.g., GitHub Actions or equivalent).

## 12. High-Level Phasing **[ASSUMPTION — to refine]**

| Phase | Focus |
|---|---|
| **P0 — Foundation** | Define the 50; design data schema (claim/provenance/confidence/history); repo scaffold. |
| **P1 — Core pipeline** | Public-source ingestion + reconciliation + version-tracked profiles. |
| **P2 — Podcast intelligence** | RSS → transcription → metric extraction. |
| **P3 — Intelligence layer** | Implied metrics, consensus ranges, source reliability, confidence decay. |
| **P4 — Interfaces & distribution** | **MCP server (primary)** exposing the dataset to AI coding agents; read-only static dashboard (overview grid → select → company detail with history & sources); "what moved today" digest. |

## 13. Glossary

| Term | Definition |
|---|---|
| ARR | Annual Recurring Revenue. |
| Form D | SEC filing disclosing an exempt private securities offering (a raise). |
| Claim | A single extracted assertion about a metric, with source and date. |
| Provenance | The origin (source, link, timestamp) of a data point. |
| Confidence score | System's assessed reliability of a data point. |
| Reconciliation | Process of merging a new claim with existing data without silent overwrite. |
| Consensus estimate | A point estimate + range synthesized from conflicting sources. |

---

*End of BRD v0.1 — draft for review.*
