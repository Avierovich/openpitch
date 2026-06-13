# Open-Source & Adjacent Competitor Landscape

| | |
|---|---|
| **Owner** | Mohamed Abdulhadi |
| **Date** | 2026-06-13 |
| **Method** | Web research (GitHub, MCP registries, product sites), June 2026 |
| **Companion** | [COMPETITIVE-ANALYSIS.md](COMPETITIVE-ANALYSIS.md) (paid incumbents) |

> Question answered: **does anyone already ship what OpenPitch is — an open/free, agent-native, fresh, sourced intelligence layer for (AI) startups?** Short answer: **no one combines all the axes.** Each closest analog nails *one* and misses the rest. That's genuine white space — but several pieces have prior art, so our defensibility is the *combination + openness + transparency*, not any single feature.

---

## 1. The landscape (what actually exists)

| Project | Type | Open? | Agent-native (MCP)? | Scope | Provenance / confidence | Status |
|---|---|:--:|:--:|---|:--:|---|
| **[OpenBook](https://github.com/iloveitaly/openbook)** | "PitchBook but open" | ✓ | ✗ | US **VC firms** (contacts), not companies/metrics | ✗ | ~54★, **dormant** |
| **[OpenVC](https://www.openvc.app/)** | Community investor DB | partly | ✗ | 10k+ **investors** | ✗ | Active, free |
| **[findfunding.vc](https://www.findfunding.vc/)** | Open VC-firm DB | ✓ | ✗ | US/Canada **VC firms** | ✗ | Active, niche |
| **[Crunchbase MCP server](https://github.com/Cyreslab-AI/crunchbase-mcp-server)** | MCP wrapper | ✓ (code) | ✓ | Whatever Crunchbase API returns | ✗ | Active — **needs paid Crunchbase key** |
| **[Apify fundraising scraper (MCP)](https://apify.com/)** | Scraper + MCP | ✗ | ✓ | TechCrunch/Crunchbase/FinSMEs | ✗ | Paid service |
| **[AI Funding Tracker](https://aifundingtracker.com/)** | Media/list site | ✗ | ✗ | **AI-startup funding** (closest content) | ✗ | Active, free-ish |
| **[Growth List](https://growthlist.co/ai-startups/)** | Paid lead DB | ✗ | ✗ | ~10k funded AI startups | ✗ | Paid |
| **[0x32e/crunchbase](https://github.com/0x32e/crunchbase)** | Funding analyzer | ✓ | ✗ | Seed/pre-seed query tool | ✗ | Small/experimental |
| **[ryukeno/VC-Startup-Funding](https://github.com/ryukeno/VC-Startup-Funding)** | EDA notebooks | ✓ | ✗ | Funding analysis | ✗ | Static project |
| **[yc-oss/open-source-companies](https://github.com/yc-oss/open-source-companies)** | Curated list | ✓ | ✗ | YC OSS startups | ✗ | List, not intelligence |
| Kaggle funding datasets | Static dataset | ✓ | ✗ | 2024–25 rounds snapshot | ✗ | Frozen snapshots |

---

## 2. Closest analogs on each axis (and why none is OpenPitch)

| Axis OpenPitch owns | Closest existing thing | Why it's not us |
|---|---|---|
| **Open + LLM extraction** | OpenBook | Extracts *investor contacts* from VC sites, not company metrics; dormant; ~54★ |
| **Agent-native (MCP)** | Crunchbase MCP server / Apify | **Wrap paid/proprietary sources** — need a Crunchbase key or paid scraper. Not free, not open data, no provenance/confidence |
| **AI-startup funding focus** | AI Funding Tracker | A website/newsletter, not open, not agent-native, no ARR/provenance/confidence/history |
| **Open investor data** | OpenVC, findfunding.vc | Investor-side (who to pitch), not company-side metrics/intelligence |
| **Funding datasets** | Kaggle / Intellizence | Static snapshots or paid; no freshness, no agent interface |

**Nobody does the full stack:** confidence-scoring **+** provenance **+** contradiction detection **+** podcast mining **+** daily freshness **+** MCP-native **+** free/open, on **AI startups (+ MENA)**. That specific combination is unoccupied.

---

## 3. Honest threats (where this gets uncomfortable)

1. **The "MCP-wraps-Crunchbase" pattern is easy and already exists.** Anyone can stand up an MCP server over a paid data API in a weekend. Our defense is *free + no key + provenance/confidence + podcast freshness + AI focus* — not novelty of "startup data in your agent."
2. **AI Funding Tracker already owns the free-AI-funding-content niche** for humans. We differ by being structured, agent-native, sourced, and confidence-scored — but they have a head start on audience.
3. **Individual features are not moats.** LLM extraction (OpenBook, Unstructured), funding data (Kaggle, Crunchbase), MCP servers — all commodity. **The moat is the combination + the transparency/provenance model + openness + agent-native distribution**, defended by execution and community, not secrecy.
4. **Low-cost to clone the idea, high-cost to clone the trust.** The reconciliation/confidence/contradiction layer and a credible track record are the hard, slow parts — lean into them.

---

## 4. Strategic takeaways

- **White space is real but the framing matters.** Don't say "first startup data in your agent" (false — Crunchbase MCP exists). Say *"the first **free, open, sourced, confidence-scored** AI-startup intelligence that lives in your agent."*
- **Differentiate hard on transparency + the contradiction-finder** — literally nobody in this list has them.
- **Co-opt, don't fight, the adjacent open projects** — e.g. OpenVC/findfunding.vc are investor-side; we could *complement* (or even consume) them rather than compete.
- **Speed matters:** the MCP-startup-data space is forming now (Runlayer, Manufact, etc. just funded). Being the *open, free, transparent* option early is the land-grab.
