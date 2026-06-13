<div align="center">

# 🪧 OpenPitch

**The open, real-time intelligence layer for AI startups — that any agent can build on.**

*A free, open-source alternative to PitchBook & CB Insights, focused on the AI companies VCs actually care about.*

`MCP-native` · `zero-cost` · `fully-sourced` · `updated daily`

> ⚠️ **Status: early development.** Specs are complete ([BRD](docs/BRD.md) · [FRD](docs/FRD.md)); implementation is in progress.

</div>

---

## Why OpenPitch exists

PitchBook and CB Insights cost **$20k+/year** — and for fast-moving AI startups, their data is often **months stale**, because human verification is slow. For a company growing 3× a year, a figure verified six months ago can be off by multiples.

Meanwhile, the real numbers are **already public**: founders state ARR on podcasts weeks before any database, funding hits SEC filings, hiring velocity reveals growth. They're just scattered, unstructured, and contradictory — exactly the problem an AI agent is built to solve.

**OpenPitch's bet is latency, not coverage.** For ~50 top AI companies, a *fresh, fully-sourced, confidence-scored* number beats a *verified-but-stale* one. We don't claim certainty — we show you the receipts.

## What you get

Ask your coding agent, get an answer with receipts:

```
> what's Mistral's latest ARR and who led their last round?

  Mistral AI
  ARR        ~€30M (implied, medium confidence) · as of 2026-05
  Last round $640M Series B · led by General Catalyst
  ↳ source: founder on 20VC ep.1042 · SEC filing · The Information
  ↳ ARR moved €18M → €30M (+67%) since 2026-01
```

Every number carries **its source, a confidence score, and a tracked history** of how it changed.

## Features

- 🎙️ **Mines podcasts** — founders leak metrics on podcasts before any database catches them. We transcribe and extract them.
- 🧾 **Always sourced** — every figure links to its origin (podcast timestamp, filing, article). No black-box numbers.
- 📊 **Confidence-scored** — built from source reliability, speaker authority, corroboration, and freshness (confidence *decays* as data ages).
- 🔀 **Reconciles conflicts** — when sources disagree, you get a consensus range + a contradiction flag, not a silent guess.
- 🧠 **Learns which sources to trust** — sources that prove right over time earn more weight.
- 🕒 **Version-tracked** — the git history *is* the audit log. See exactly how a company's reported ARR evolved.
- 📡 **Composable** — emits typed events other agents subscribe to (newsletters, press alerts, investor outbound).
- 🤝 **Agent-to-agent (A2A)** — not just an MCP *tool* but an A2A *agent* your agents can delegate research to.
- 🧯 **Grounding** — give your AI a sourced, confidence-scored fact base so it stops making up AI-company numbers.
- ⚡ **60-second install** — no key, no signup; works in your agent in under a minute.
- 💸 **Genuinely free** — runs entirely on free tiers. No cost to run, no cost to use.

## Quickstart — use it in Claude Code / Codex

**No API key. No signup. No cost.** The data is already built and committed; the MCP server just reads it, and *your* agent does the reasoning.

```jsonc
// add to your MCP config (e.g. Claude Code / Codex)
{
  "mcpServers": {
    "openpitch": { "command": "uvx", "args": ["openpitch-mcp"] }
  }
}
```

Then just ask your agent about any covered AI company. *(Install snippet finalized at first release.)*

### Or just browse the data
- 🌐 **Dashboard** — all 50 companies, sortable, with history charts *(GitHub Pages link at release)*
- 📁 **Raw data** — [`data/companies/`](data/) — plain JSON, diffable, yours to use

## How it works

```
  Sources              Daily pipeline (free GitHub Actions)         Interfaces
  ──────────           ───────────────────────────────────         ──────────
  Podcasts ─┐          1. select top-50 (VC-attention score)        ┌─ MCP server (local, BYO agent)
  News ─────┤    ───▶  2. collect · 3. transcribe · 4. extract ───▶ ├─ static dashboard
  SEC EDGAR ┤          5. reconcile · 6. score sources              ├─ event feed (JSONL / RSS)
  Web ──────┘          7. publish → git commit (the database)       └─ "what moved today" digest
```

The git repo **is** the database. There's no server to run. See the [FRD](docs/FRD.md) for the full design.

## Build on it (composability)

OpenPitch emits typed, confidence-scored **events** when something material changes — so other agents can react:

| You're building… | Subscribe to | OpenPitch becomes… |
|---|---|---|
| A newsletter agent | all material events | your content pipeline's data source |
| A press/PR workflow | funding/valuation events, confidence ≥ 0.8 | your "time to call the company" trigger |
| Investor outbound | universe entries, growth thresholds | your targeting signal |

Events ship on MCP, a raw `events/feed.jsonl`, and RSS/Atom. Schemas are versioned. See [`docs/integrations/`](docs/).

## How we compare

OpenPitch is **complementary to the incumbents, not a rip-and-replace.** We win a narrow wedge; we lose on breadth and verification — and we're honest about both.

| | PitchBook / CB Insights | Crunchbase | Harmonic | MAGNiTT / Wamda | **OpenPitch** |
|---|:--:|:--:|:--:|:--:|:--:|
| Price | $20k–100k/yr | Freemium | Custom | $/regional | **Free & open** |
| Freshness | Weeks–months | Variable | Days | Weeks | **Daily** |
| In your AI agent (MCP) | ✗ | ✗ | ◐ | ✗ | **✓** |
| Every figure sourced + confidence-scored | ◐ | ◐ | ◐ | ◐ | **✓** |
| Contradiction detection | ✗ | ✗ | ✗ | ✗ | **✓** |
| Coverage breadth | **✓✓✓** | **✓✓✓** | **✓✓** | ✓ (MENA) | narrow (by design) |
| Verified, diligence-grade | **✓** | ◐ | ◐ | ◐ | ✗ (probabilistic) |

**The honest pitch:** *the free, fresh, AI-native first look — every number sourced — before you pull the expensive verified report.* For an investment decision, you still need the incumbents. Full mapping, feature matrix & pricing: [docs/COMPETITIVE-ANALYSIS.md](docs/COMPETITIVE-ANALYSIS.md) · [spreadsheet](docs/competitive-matrix.xlsx).

## Coverage

**Global AI startups** — ~50, **dynamically selected** by VC attention (valuation + funding activity + investor quality — *not* ARR, to avoid circularity). The list moves as attention shifts; companies entering/leaving the top-50 is itself a tracked signal.

**MENA AI/tech segment** — a dedicated regional set (an open, AI-native alternative to MAGNiTT/Wamda). Honest caveat: MENA disclosure is lighter than the US, so this segment launches with lower confidence/coverage, clearly labeled.

Seed universe: [`config/watchlist.yaml`](config/watchlist.yaml).

## Honest disclaimer

OpenPitch is **transparently probabilistic**. Many figures are estimates derived from public, self-reported, sometimes-contradictory sources. We surface confidence and provenance precisely so you can judge for yourself. **This is not investment advice, and figures are not guaranteed accurate.** Always verify before acting.

## Roadmap

- [x] Business + technical specs ([BRD](docs/BRD.md) · [FRD](docs/FRD.md))
- [x] Competitive analysis: [incumbents](docs/COMPETITIVE-ANALYSIS.md) · [matrix xlsx](docs/competitive-matrix.xlsx) · [OSS landscape](docs/OSS-LANDSCAPE.md) · [**free/open deep-dive**](docs/OSS-DEEP-DIVE.md) · [strategy & viability](docs/STRATEGY-DEEP-DIVE.md) · [growth plan](docs/GROWTH.md)
- [x] Seed universe (global AI + MENA segment)
- [x] Core data model + reconciliation engine (confidence, consensus, contradiction) — *tested*
- [x] Source adapters: podcast, news, EDGAR, company-site — *tested*
- [ ] Extraction stage (LLM claim extraction) — *the launch gate: real data + contradictions*
- [ ] MCP server
- [ ] Daily GitHub Actions pipeline
- [ ] Static dashboard
- [ ] Event feed + integration recipes
- [ ] A2A agent interface (Agent Card) — delegate research agent-to-agent
- [ ] MENA adapters (regional news, free-zone registries)
- [ ] Rich-source expansion (GitHub, hiring, app-ranks) — *post-PMF scaling*
- [ ] *v2:* implied-ARR model, intra-day funding fast-lane

## Contributing

Contributions welcome — especially **new source adapters** (one file each) and **watchlist curation**. See the [FRD](docs/FRD.md) for architecture.

## License

MIT *(to be confirmed)*

---

<div align="center">
<sub>Built in the open. Free forever. If a number looks wrong, open an issue — provenance means you can check our work.</sub>
</div>
