# Open-Source, Free & MCP Competitor Landscape

| | |
|---|---|
| **Owner** | Mohamed Abdulhadi |
| **Date** | 2026-06-13 |
| **Method** | Public web research across GitHub, MCP registries, package/product pages, dataset repos, public social snippets, and free-access docs |
| **Companion** | [OSS-DEEP-DIVE.md](OSS-DEEP-DIVE.md), [competitive-matrix.xlsx](competitive-matrix.xlsx) |

> Question answered: **does anyone already ship what OpenPitch is — a free/open, agent-native, fresh, sourced intelligence layer for AI-startup metrics?** Short answer: **no one combines all the axes**, but the free/MCP landscape is broader than the first pass implied. The closest substitutes are open company-research agents, startup due-diligence MCPs, funding-data MCPs, Crunchbase wrappers, and open startup datasets.

## 1. Research protocol

This pass explicitly searched beyond paid incumbents:

- **GitHub/code** — `startup data`, `company research`, `funding data`, `crunchbase`, `pitchbook`, `MCP`, `due diligence`, `venture capital`, `private markets`.
- **MCP registries** — Glama, MCP.so, LobeHub, Smithery/Pipedream-style lists, awesome-mcp lists.
- **Product/docs/API pages** — install docs, pricing pages, changelogs, tool lists, examples.
- **Package registries** — npm/package links where MCP servers expose install paths.
- **Datasets** — ROSS Index, LF AI Landscape, YC/OSS lists, GitHub startup/funding data.
- **Social/public traction** — X snippets, Reddit posts, Product Hunt/HN-like mentions where accessible. Social was used as directional evidence only, never as the sole source for hard capability claims.

Account-gated products were verified from public docs/listings unless a free account was needed and feasible. No paid access, payment-card trial, private scraping, or paywall bypassing was used.

## 2. Directness scale

| Label | Meaning |
|---|---|
| `direct` | Can answer company/startup/funding intelligence questions now |
| `near-direct` | Can research companies but lacks structured startup metric database or OpenPitch-style trust model |
| `adjacent` | Useful source, dataset, workflow, or discovery competitor |
| `source/partner` | More likely an input source than a product competitor |

## 3. Open / free / MCP landscape

| Project | Type | Directness | Open? | Agent-native? | Scope | Provenance / confidence | Status / caveat |
|---|---|---|:--:|:--:|---|:--:|---|
| **OpenBB** | Open finance data + MCP | adjacent | ✓ | ✓✓ | Public markets / finance, not startup ARR | ◐ | Major open/MCP distribution threat |
| **Exa Company Researcher** | Open-source company research app | near-direct | ✓ | ◐ | Any company; funding, PitchBook/Crunchbase/Tracxn lookups, news, social, GitHub | ◐ | Strongest OSS company-research analog; requires Exa + Anthropic keys |
| **Octagon Funding Data MCP** | Funding/private-market MCP | direct | ◐ code | ✓ | Funding rounds, valuations, investors, trends | ◐ | Free account/API key per MCP listing; proprietary backend |
| **Sieve MCP** | Startup due-diligence MCP | direct | ✓ repo | ✓ | Startup screening, IMPACT-X score, evidence-typed findings | ✓ | Closest due-diligence workflow analog |
| **Intelica MCP** | Competitive intelligence API/MCP | near-direct | ◐ docs | ✓ | Competitive/venture screening context | ◐ | Agent-native CI substitute; paid per call |
| **CompanyLens MCP** | Official-source corporate intelligence MCP | near-direct | ✓ | ✓ | SEC, Companies House, sanctions, contracts, court cases | ✓ | Strong source-layer competitor/partner, not private ARR |
| **FounderSignal MCP** | Founder/startup signal MCP | near-direct | ? | ✓ | Trends, ads, Crunchbase, LinkedIn, product reviews | ◐ | Recent MCP listing; details need deeper verification |
| **Crunchbase MCP Server** | MCP wrapper | direct | ✓ code | ✓ | Crunchbase company/funding/acquisition/people data | ✗ | Requires Crunchbase access/API; thin wrapper |
| **ThomasJanssen Crunchbase MCP** | Small Crunchbase/company MCP | near-direct | ✓ repo | ✓ | Crunchbase-style company queries via Bright Data-style retrieval | ✗ | Tiny project; validates wrapper pattern |
| **Apify company research actors** | Scraping/research marketplace | near-direct | ✗/varies | ◐ | Company profiles, PitchBook/Crunchbase/LinkedIn/news depending on actor | ◐ | Commodity paid/free-credit substitute |
| **Tavily / Agentic Company Researcher** | Open company-research agent | near-direct | ✓ | ◐ | Search-generated company reports | ◐ | Live research pattern, not committed metric DB |
| **AI Funding Tracker** | AI-startup funding site | adjacent | ✗ | ✗ | AI funding cards/roundups | ◐ | Closest content/SEO competitor for AI funding |
| **ROSS Index** | OSS startup dataset/index | adjacent | ✓ | ✗ | Trending open-source startups by GitHub star growth | ✓ | Discovery signal, not funding/ARR intelligence |
| **LF AI Landscape** | Open AI/data landscape | adjacent | ✓ | ✗ | Open-source AI/data projects, GitHub/funding metadata | ◐ | Source/partner dataset |
| **OpenBook** | "PitchBook but open" VC contacts | adjacent | ✓ | ✗ | VC firms/investors, not company metrics | ✗ | Dormant/niche but relevant in spirit |
| **OpenVC / findfunding.vc** | Investor-side databases | adjacent | ◐/✓ | ✗ | Investors/funds, not companies | ✗ | Complementary source/partner |
| **YC OSS / yc-oss lists** | Startup directories | source/partner | ✓ | ✗ | Open-source startups/company lists | ✗ | Seed/source input, not intelligence layer |
| **Kaggle/static funding datasets** | Static datasets | source/partner | ✓/varies | ✗ | Frozen company/funding snapshots | ✗ | Useful only as historical seed data |

## 4. Closest analogs by axis

| Axis OpenPitch owns | Closest existing thing | Why it is not OpenPitch |
|---|---|---|
| Open-source company research | Exa Company Researcher | Live research app; needs search/LLM keys; no committed startup metric DB, confidence decay, contradiction model, or event feed |
| Funding-data MCP | Octagon Funding Data MCP | Funding/valuation MCP, but proprietary backend and API key; no open audit trail |
| Startup due diligence MCP | Sieve MCP | Evidence-typed diligence workflow, but not an open sourced metric database with history |
| Official-source company MCP | CompanyLens MCP | Strong public-company/registry data, but not private AI-startup ARR/funding intelligence |
| Crunchbase-in-agent | Crunchbase MCP wrappers | Need proprietary Crunchbase/Bright Data access and add little trust logic |
| AI-startup funding content | AI Funding Tracker | Human website/content, not structured agent-native open data |
| OSS startup discovery | ROSS Index / LF AI Landscape | Tracks OSS ecosystems and GitHub/funding metadata, not private-company ARR/provenance |

## 5. Strategic takeaways

1. **The space is not empty.** "Startup/company research in an agent" already exists through Exa, Octagon, Sieve, CompanyLens, Crunchbase wrappers, and generic research MCPs.
2. **The specific combination is still open.** None of the found competitors combines no-key local MCP, committed open data, AI-startup focus, per-figure confidence/provenance, contradiction detection, corrections, and event feeds.
3. **Funding scraping is commodity.** Apify and Crunchbase wrappers show raw collection is easy; OpenPitch must compete on reconciliation, source quality, freshness, and auditability.
4. **OpenPitch should avoid "first" claims.** Safer claim: *"the free, open, no-key, confidence-scored AI-startup intelligence layer agents can call."*
5. **Some competitors are future sources.** CompanyLens, ROSS Index, LF AI Landscape, OpenVC, and public registries may be source partners rather than rivals.
6. **Social proof is useful but weak.** X and Reddit helped confirm Exa and Sieve traction, but hard workbook claims should still rely on repos, registries, docs, and product pages.
