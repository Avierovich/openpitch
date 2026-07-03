# Open-Source / Free Competitor Deep-Dive (the *real* competitive set)

| | |
|---|---|
| **Owner** | Mohamed Abdulhadi (PM/PMM) |
| **Date** | 2026-06-13 |
| **Why this doc** | Correction: for a **free, easy-to-install** product, the paid incumbents (PitchBook, CB Insights…) are *not* the real threat — we beat them on price & ease by default. The genuine competition is **other free/open tools that can match us on both.** This is the deep-dive on *that* set. |
| **Companions** | survey: [OSS-LANDSCAPE.md](OSS-LANDSCAPE.md) · incumbents: [STRATEGY-DEEP-DIVE.md](STRATEGY-DEEP-DIVE.md) |

> **Reframe:** "free + easy" is our moat *against incumbents* but the **table stakes** against this set. Here, differentiation must come from the layers free tools *don't* have — transparency/provenance/confidence/contradictions, multi-source (podcast) mining, AI-startup+MENA focus, active maintenance, and A2A. The honest risk below is **low barriers to entry**, not any single existing tool.

---

## 1. ⚠️ The competitor I'd missed — OpenBB (most important)

| | |
|---|---|
| **What it is** | "Financial data platform for analysts, quants, **and AI agents**" — one of the largest open-source finance projects (tens of thousands of GitHub stars), VC-backed. |
| **Agent posture** | **Workspace MCP** explicitly works with "Claude Code, Codex, and any MCP-compatible agent." ODP = "connect once, consume everywhere" (Python, Excel, MCP, REST). |
| **Data** | Broad **public-markets / financial** data via provider extensions (equities, crypto, macro, fundamentals). |
| **Focus** | **Public markets & quant/analyst workflows — NOT private startup intelligence / ARR / funding rounds.** |

**Pros:** huge community + stars, well-funded, actively maintained, genuinely agent-native, the de-facto "open + MCP financial data" brand, multi-surface.
**Cons (vs our niche):** not private-company/startup data; no ARR/valuation-for-private-cos; no provenance/confidence model; many providers need their own API keys (so not zero-config); not AI-startup or MENA focused.

**OpenPitch vs OpenBB**
| | OpenBB | OpenPitch |
|---|:--:|:--:|
| Agent-native (MCP) | ✓✓ | ✓ |
| Open source + community | ✓✓✓ | (new) |
| **Private AI-startup intelligence (ARR/valuation/funding)** | ✗ | ✓ |
| Provenance + confidence + contradictions | ✗ | ✓ |
| Zero-config (no provider keys) | ◐ | ✓ |
| MENA focus | ✗ | ✓ |

**Threat: MEDIUM (highest in this set).** Not a direct competitor *today* (different data domain), but it's the proof that **a well-resourced open project can own "agent-native financial data."** If OpenBB — or a clone with its distribution — pointed at private/startup data, that's the real danger. **Strategic implication: move fast, and consider being *complementary* (an OpenBB provider extension / interoperable), not a rival.**

---

## 2. Exa Company Researcher (strongest open company-research analog)

| | |
|---|---|
| **What it is** | Open-source app that researches any company from a URL and generates a structured company profile. |
| **Data posture** | Uses Exa search over company pages, LinkedIn, funding details, Crunchbase/PitchBook/Tracxn profile pages, news, social, GitHub, and 10-Ks. |
| **Access reality** | Open-source code, but requires Exa and Anthropic API keys; optional YouTube/GitHub keys. |
| **Agent posture** | The repo is a web app, while public X snippets mention a related Exa Company Researcher MCP tool. |

**Why it matters:** This is the closest open-source proof that developers want "company research in a tool." It is broad, simple, and already has visible GitHub traction.

**What it lacks vs OpenPitch:** no committed/open metric database, no daily pipeline, no per-figure confidence decay, no contradiction clustering, no event feed, and no zero-key user experience.

**Threat: HIGH as an OSS/company-research analog.** It could satisfy many casual users who want a report, but it does not replace a sourced metric layer.

---

## 3. Octagon Funding Data MCP (closest funding-data MCP)

| | |
|---|---|
| **What it is** | MCP-accessible funding/private-market intelligence. |
| **Data posture** | MCP listings describe funding rounds, valuations, investor activity, investment trends, and market benchmarking. |
| **Access reality** | Public listings say it is free after signup/API key; deeper limits were not verified without account access. |
| **Agent posture** | MCP-first. Octagon also ships broader market/filings/financial research MCP servers. |

**Why it matters:** It directly overlaps with OpenPitch's funding/valuation MCP surface. It proves users can already ask agents for funding-round intelligence.

**What it lacks vs OpenPitch:** proprietary backend, account/API key dependency, no open committed data, no public correction/audit trail, and no visible OpenPitch-style confidence/contradiction model.

**Threat: HIGH for funding/valuation use cases.** OpenPitch must win on no-key, transparency, auditability, and AI-startup metric depth.

---

## 4. Sieve MCP (closest startup-due-diligence workflow)

| | |
|---|---|
| **What it is** | Startup due-diligence MCP that scores companies across IMPACT-X dimensions. |
| **Data posture** | Real-time web research and evidence-typed findings: Documented, Discovered, Inferred, Missing. |
| **Access reality** | Public repo/registry/social listings visible; account/free-tier details need deeper verification. |
| **Agent posture** | MCP connector for VCs, solo GPs, and angel investors. |

**Why it matters:** Sieve has the same trust-language instinct OpenPitch needs: show what is verified and what is missing. It competes for the "agent does startup diligence" job.

**What it lacks vs OpenPitch:** not a maintained open metric database, not focused on AI-startup ARR/funding history, and not designed as a reusable data/event layer.

**Threat: HIGH for VC workflow positioning.** OpenPitch should not position as a generic diligence tool; it should position as the source-backed metric layer that diligence tools can call.

---

## 5. CompanyLens MCP (official-source company intelligence)

| | |
|---|---|
| **What it is** | MCP server for corporate intelligence from official/public sources. |
| **Data posture** | SEC EDGAR, UK Companies House, OpenSanctions, USAspending.gov, SAM.gov, CourtListener. |
| **Access reality** | Public MCP/package listing; install via `npx companylens-mcp`; free limits/backend details not fully verified. |
| **Agent posture** | MCP-first across Claude Desktop, Claude Code, Cursor, Windsurf. |

**Why it matters:** It is strong on official-source provenance, which is one of OpenPitch's trust pillars. For public companies and registries, it may be a better source than OpenPitch should try to rebuild.

**What it lacks vs OpenPitch:** private AI-startup focus, ARR/funding reconciliation, podcast/news mining, dynamic universe, and contradiction artifacts.

**Threat: MEDIUM; partner/source potential: HIGH.** Treat it as a possible source-layer complement for public filings, sanctions, contracts, and registry data.

---

## 6. Intelica MCP (agent-native competitive intelligence)

| | |
|---|---|
| **What it is** | Competitive-intelligence API/MCP for autonomous agents, with modes for competitive analysis, fundraising, acquisition, market entry, and venture screening. |
| **Data posture** | Structured JSON output claimed; data-source depth and provenance not fully verified from public docs. |
| **Access reality** | Public posts describe per-call x402 payments; not a free/open-data equivalent. |
| **Agent posture** | MCP and A2A positioned explicitly. |

**Why it matters:** It competes with the "agents need market context before acting" story and is built for autonomous agent workflows.

**What it lacks vs OpenPitch:** not a startup metric database, not open data, not zero-cost, and no visible public correction/history model.

**Threat: MEDIUM.** Important as positioning pressure: OpenPitch must be much more concrete and trusted on startup metrics.

---

## 7. Crunchbase MCP server (Cyreslab-AI)

| | |
|---|---|
| **What it is** | Open-source (MIT) MCP server exposing Crunchbase data (search/company/funding/acquisitions/people). |
| **Reality** | **Requires a paid Crunchbase API key** — so "free + easy" is *false*: you pay Crunchbase and self-host. |
| **Maturity** | ~16★, ~5 commits. Thin wrapper, no value-add. |
| **Missing** | No ARR, confidence, freshness guarantees, or provenance. |

**OpenPitch vs Crunchbase-MCP**
| | Crunchbase-MCP | OpenPitch |
|---|:--:|:--:|
| Agent-native | ✓ | ✓ |
| **Free to *use*** | ✗ (needs paid key) | ✓ |
| Value-add (confidence/ARR/contradictions) | ✗ | ✓ |
| Maintained / mature | ✗ | (active) |

**Threat: LOW.** It's a wrapper, not a competitor — and crucially **it's not actually free to use.** This is the clearest validation of our **ease-of-implementation pillar**: we need *no* key; it needs a paid one.

---

## 8. AI Funding Tracker (aifundingtracker.com)

| | |
|---|---|
| **What it is** | Free website: curated **monthly** AI-funding roundups (cards: company, amount, valuation, lead investors). |
| **Has** | Some ARR mentions (Sierra $150M, Cognition $492M run-rate); SEO/audience. |
| **Lacks** | No queryable data, **no API, no MCP/agent access**, minimal citations, no confidence, selective (top ~15/mo), monthly (not daily). |

**OpenPitch vs AI Funding Tracker**
| | AI Funding Tracker | OpenPitch |
|---|:--:|:--:|
| AI-startup funding focus | ✓ | ✓ |
| Human audience / SEO today | ✓ | (new) |
| Structured / queryable / API | ✗ | ✓ |
| Agent-native (MCP/A2A) | ✗ | ✓ |
| Per-figure sources + confidence | ✗ | ✓ |
| Freshness | Monthly | Daily |

**Threat: LOW-MEDIUM.** Our closest *content/audience* competitor for humans, and they have a head start on SEO — but they're a newsletter-style site, not structured/agent-native data. We win decisively for *machine* consumption; we'd need to earn the human audience.

---

## 9. OpenBook (iloveitaly/openbook)

| | |
|---|---|
| **What it is** | "Like PitchBook, but open." LLM-extraction (OpenAI + LangChain) of **VC-firm contact info** from VC websites; DoltHub storage. |
| **Status** | ~54★, **dormant**; TypeScript; US VC firms, **not companies/ARR/metrics**. |

**Threat: LOW.** The closest analog *in spirit* (open + LLM extraction) but different scope (investor contacts, not company intelligence), dormant, tiny. Mostly a cautionary tale: open + clever ≠ traction.

---

## 10. Investor-side open DBs — OpenVC, findfunding.vc

Free/community databases of **investors** (who to pitch), not company intelligence. **Threat: LOW** (adjacent, different side of the market). **Opportunity:** *complement* — we could even consume/link them rather than compete.

## 11. Apify fundraising scraper (MCP)

Freemium scraper (TechCrunch/Crunchbase/FinSMEs) with an MCP interface. Commoditizes *funding-news scraping* but is paid-per-use and has **no reconciliation/confidence/ARR layer**. **Threat: LOW-MEDIUM** — proves scraping funding news is cheap/commodity (so don't claim that as the moat); doesn't replicate our intelligence layer.

## 12. Static datasets (Kaggle, ROSS, LF AI Landscape, etc.)

Frozen snapshots. No freshness, no agent interface. **Threat: LOW.**

---

## 13. Head-to-head — the expanded free/MCP set vs OpenPitch

| Capability | Exa Co. Researcher | Octagon Funding MCP | Sieve MCP | CompanyLens MCP | CB-MCP | OpenBB | **OpenPitch** |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| Free to **use** without paid data key | ◐ | ◐ | ◐ | ◐ | ✗ | ◐ | **✓** |
| Open-source code | ✓ | ◐ | ✓ | ✓ | ✓ | ✓ | **✓** |
| Agent-native / MCP | ◐ | ✓ | ✓ | ✓ | ✓ | ✓ | **✓** |
| Private/startup funding data | ◐ | ✓ | ◐ | ✗ | ✓ | ✗ | **✓** |
| Private ARR/revenue metrics | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| Per-figure provenance/confidence | ◐ | ◐ | ✓ evidence-typed | ✓ official-source | ✗ | ◐ | **✓** |
| Contradiction detection | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| Committed open data/history | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| Event/feed layer | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **✓ planned** |
| AI-startup focus | ◐ | ◐ | ◐ | ✗ | ◐ | ✗ | **✓** |

---

## 14. The honest risk (it's not any one tool — it's the barrier height)

1. **Low barriers to entry.** Crunchbase-MCP, Octagon-style MCP listings, Exa/Tavily research apps, and Apify prove anyone can stand up an agent/company-research workflow quickly. *Wrapping data or search is commodity.* Our non-commodity parts are the **reconciliation/confidence/contradiction layer + curated multi-source mining + active maintenance + trust** — lean on those, never on "we have startup data in an MCP."
2. **A strong open incumbent could pivot.** OpenBB owns "open + agent-native financial data" with massive distribution. The danger isn't them today; it's them (or a funded clone) aiming at private/startup data. **Mitigation: speed + niche depth + interoperate (be an OpenBB provider, not only a rival).**
3. **Distribution, not features, is where we're behind.** Every meaningful free competitor that matters (OpenBB, AI Funding Tracker) has an audience; we have none yet. Features we win; reach we must build (see the distribution plan).

---

## 15. Revised viability verdict (vs the free set)

**Good news:** against the *correct* competitive set, OpenPitch looks **more** differentiated, not less. The free competitors are mostly **weak, narrow, dormant, paid-key-gated, or public-markets-only** — *none* combines our intelligence layer, and several aren't even truly free to use. The combination is genuinely unoccupied.

**Sobering news:** "free + easy" buys *entry*, not *defensibility*. Because barriers are low, the moat must be **execution speed, community, and the hard-to-copy trust/transparency/multi-source layer** — not the idea. The audience≠pain risk (STRATEGY-DEEP-DIVE §6) still dominates.

**Net:** viability **improves** under this corrected lens — *if* we (a) win on the ease-of-implementation pillar (we already out-zero-config Crunchbase-MCP and OpenBB), (b) make transparency/contradictions the visible differentiator, (c) build distribution fast before a funded open player notices the niche, and (d) consider **interoperating with OpenBB** rather than only competing. The window is open but not wide — **speed is the strategy.**
