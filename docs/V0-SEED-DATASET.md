# v0 Seed Dataset Plan

## Purpose

The first public dataset should prove OpenPitch's method before it tries to prove breadth.

Target: **10 companies, 3+ sourced metrics each, 2-3 strong public-source discrepancies, and a working MCP/demo path.**

Current status: **5 companies are committed and runnable for software testing.** They still need a launch-grade source audit, and five additional seed companies are needed before the public launch bar is met.

The seed is not the universe. OpenPitch should still retain the dynamic top-50 watchlist, displayed by tiers:

- Tier 1: ranks 1-10.
- Tier 2: ranks 11-25.
- Tier 3: ranks 26-50.
- Watchlist: candidates outside the selected 50.

## Selection Criteria

Pick companies that are:

- high-interest to AI builders and investors;
- likely to have public metric/funding claims;
- covered by multiple source types;
- recognizable enough for launch assets;
- not fully public or out of scope.

The seed should include a mix of foundation models, coding agents, AI infrastructure, and vertical AI.

## Proposed Seed Candidates

| Priority | Company | Category | Why it belongs | Seed status |
|---:|---|---|---|---|
| 1 | OpenAI | foundation-model | Highest interest; many public sources | Committed; needs launch audit |
| 2 | Anthropic | foundation-model | High interest; funding/valuation coverage | Committed; needs launch audit |
| 3 | Mistral AI | foundation-model | Global AI leader; EU angle | Committed; needs launch audit |
| 4 | Perplexity | enterprise-ai | Search/product metrics often discussed | Candidate |
| 5 | Anysphere (Cursor) | coding-agent | Core audience cares; valuation/ARR interest | Committed; needs launch audit |
| 6 | Cognition (Devin) | coding-agent | High buzz; public run-rate claims reported | Committed; needs launch audit |
| 7 | Sierra | ai-agents | Strong ARR/funding interest | Candidate |
| 8 | Harvey | vertical-app | Legal AI; funding and ARR interest | Candidate |
| 9 | ElevenLabs | generative-media | Recognizable; funding and usage signals | Candidate |
| 10 | Runway | generative-media | Video AI; funding/valuation coverage | Candidate |

These are candidates, not commitments. Replace any company that lacks enough public sources.

## Minimum Metrics Per Company

Each seed company should have at least 3 of:

- latest valuation;
- latest round amount;
- total funding;
- ARR/revenue/run-rate;
- headcount;
- headcount growth;
- notable customers/users;
- net revenue retention, when public;
- customer/user count;
- growth rate;
- revenue multiple if derivable.

If a headline metric is unknown, state that explicitly rather than inventing one.

## Source Requirements

Minimum per company:

- 2 independent source items;
- 1 source with a clear published date;
- all displayed claims linked to a source URL or durable locator.

Minimum across seed:

- at least 30 sourced claims;
- at least 4 source types represented;
- at least 2 filing/official-source-backed claims if available;
- at least 2 podcast/interview-derived claims if available.

## Contradiction Candidate Tracker

| Company | Metric | Claim A | Claim B | Source strength | Launch-worthy? | Notes |
|---|---|---|---|---|---|---|
| TBD | TBD | TBD | TBD | TBD | TBD | Add only with public evidence |
| TBD | TBD | TBD | TBD | TBD | TBD | Add only with public evidence |
| TBD | TBD | TBD | TBD | TBD | TBD | Add only with public evidence |

Do not force contradictions. A weak contradiction is worse than none.

## Data Completeness Tracker

| Company | Claims | Metrics | Provenance complete? | MCP works? | Card/dashboard ready? |
|---|---:|---:|---|---|---|
| OpenAI | Committed | Committed | Needs launch audit | Tested via MCP tools | Generated |
| Anthropic | Committed | Committed | Needs launch audit | Tested via MCP tools | Generated |
| Mistral AI | Committed | Committed | Needs launch audit | Tested via MCP tools | Generated |
| Perplexity | 0 | 0 | No | No | No |
| Anysphere (Cursor) | Committed | Committed | Needs launch audit | Tested via MCP tools | Generated |
| Cognition (Devin) | Committed | Committed | Needs launch audit | Tested via MCP tools | Generated |
| Sierra | 0 | 0 | No | No | No |
| Harvey | 0 | 0 | No | No | No |
| ElevenLabs | 0 | 0 | No | No | No |
| Runway | 0 | 0 | No | No | No |

## Seed Acceptance Criteria

The seed dataset is launch-ready when:

- all 10 companies have real data or are intentionally replaced;
- each company has 3+ sourced metrics;
- all visible values validate against schemas;
- MCP can answer a metric/provenance question for each company;
- dashboard/company cards show no empty placeholder sections;
- 2-3 public-source discrepancies are strong enough for external scrutiny;
- correction workflow and methodology are linked.

## What Not To Do

- Do not add weak companies just to hit 10.
- Do not show "unknown" as a failure; show it as honest coverage.
- Do not use ARR as a universe selector.
- Do not convert headcount into ARR as a headline v0.1 value.
- Do not launch contradiction copy before correction policy exists.
