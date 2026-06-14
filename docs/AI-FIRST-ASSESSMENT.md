# AI-Firstify Assessment Report

**Project:** OpenPitch
**Date:** 2026-06-14
**Mode:** Audit (read-only)
**Method:** ai-firstify skill — 7-dimension rubric (GREEN / YELLOW / RED)

## Overall Score

| Dimension | Score | Summary |
|-----------|-------|---------|
| 1. Project Structure | GREEN | Git (23 commits), `.gitignore` excludes `.env`, 13 root files, CLAUDE.md → AGENTS.md handoff, logical `src/` layout |
| 2. Agent Architecture | GREEN | LLM calls confined to the pipeline (legit batch); **MCP server makes ZERO LLM calls — reasoning delegated to the user's own agent** (textbook AI-first) |
| 3. Skill Usage | YELLOW | No `.claude/skills/` (it's a product, not a skill-pack) — but exposes agent-native MCP/A2A interfaces + reproducible scripts. One project skill would close the gap |
| 4. Scope & Complexity | GREEN | Does one thing; no heavy frontend (static HTML), no DB (git *is* the DB), no auth; scope guarded by explicit non-goals |
| 5. Context Hygiene | GREEN | Thin CLAUDE.md + AGENTS.md coordination log; `docs/` uses progressive disclosure; specs separated by concern |
| 6. Safety | GREEN | `.env` untracked + gitignored; conservative DATA-POLICY (robots/ToS, no auth-walled scraping); MIT license; read-only MCP; corrections workflow |
| 7. Workflow Design | GREEN | Prescriptive specs (FRD/MCP-SPEC/EVENTS-SPEC); 42 tests / 5 files; reproducible generators; conventional commits; sub-agent review used |

**Verdict: strongly AI-first — 6 GREEN, 1 contextual YELLOW.** OpenPitch is, structurally, a near-model AI-first project: it deliberately does *not* embed an agent, pushes all consumption-side reasoning to the user's own agent (MCP/A2A), and treats git as the database.

## Priority Recommendations

1. **[HIGH]** Verify seed data + add a demo asset before launch (LAUNCH-GATES) — *small, but launch-blocking.*
2. **[MEDIUM]** Fix the universe-ranking bug (re-score the *global* committed set in `_finalize`, not per-run — duplicate `rank: 1` observed) — *~1 hr.*
3. **[MEDIUM]** Add a project skill `.claude/skills/run-openpitch/` (prescriptive pipeline runbook) to raise Dimension 3 to GREEN — *~1 hr.*
4. **[LOW]** Clarify the CLAUDE.md ↔ AGENTS.md split (CLAUDE.md is 3 lines) — *15 min.*

## Detailed Findings

### Dimension 1: Project Structure
Git initialized with 23 well-formed, co-authored commits; `.gitignore` excludes `.env`, `.venv`, caches, and `dashboard/dist`. Root has 13 files (clean). `src/openpitch/` is logically organized (models, pipeline, reconcile, mcp_server). CLAUDE.md exists but is a 3-line pointer to AGENTS.md — fine, but slightly under-uses the convention. **GREEN.**

### Dimension 2: Agent Architecture
The standout dimension. LLM API calls exist **only** in `pipeline/llm/` and `pipeline/transcribe/` — the legitimate "batch processing via API" case — behind a swappable provider abstraction with multi-model rotation. Critically, the **MCP server makes zero LLM calls**; it serves committed JSON and the *user's own agent* does the reasoning (FRD §8.6). No embedded agent, no custom framework, no agent-in-a-webapp. This is the AI-first ideal: don't ship an agent, ship a tool agents call. **GREEN.**

### Dimension 3: Skill Usage
The rubric targets Claude skill-pack projects (`.claude/skills/`), which OpenPitch isn't — it's a product. Its AI-first equivalent is strong: agent-native MCP tools (8, per MCP-SPEC), an A2A Agent Card, and reproducible generator scripts. What's missing is a prescriptive *project* skill for operators (e.g., "run the daily pipeline / refresh data"), which would make the repo self-documenting for Claude Code. **YELLOW (contextual).**

### Dimension 4: Scope & Complexity
Tightly scoped: AI-startup intelligence, nothing else. No React/Vue/Angular (the dashboard is pre-rendered static HTML), no database (git-tracked JSON), no auth, no deployment pipeline beyond free CI. Explicit non-goals in the BRD/PRD guard against creep. File count (~451 incl. data/history) is data, not code sprawl. **GREEN.**

### Dimension 5: Context Hygiene
CLAUDE.md is minimal and delegates to AGENTS.md (the live coordination log between Codex and Claude Code). `docs/` separates concerns (BRD/PRD/FRD/METHODOLOGY/DATA-POLICY/specs) with progressive disclosure rather than one mega-file. No context pollution. **GREEN.**

### Dimension 6: Safety
`.env` is untracked and gitignored (verified); the live key was never committed. DATA-POLICY codifies a conservative posture: official APIs/RSS first, respect robots.txt/ToS, no auth-walled scraping, copyright-safe excerpts. MCP server is read-only. Corrections workflow + neutral contradiction language reduce legal risk. MIT LICENSE present. **GREEN.**

### Dimension 7: Workflow Design
Workflows are prescriptive (FRD, MCP-SPEC, EVENTS-SPEC, LAUNCH-GATES). 42 tests across 5 files cover the engine, adapters, extraction, derivation, and MCP. Reproducible generators (`scripts/`) and a quality report exist. Git discipline is strong (conventional, co-authored commits; AGENTS.md handoff protocol). A sub-agent was used for growth research (review/critique pattern). **GREEN.**

## Still Needs Human Decision

- [ ] Is launch-grade contradiction curation done to your bar? (LAUNCH-GATES gate)
- [ ] Publish target: PyPI org/name + public GitHub `OWNER/repo` for `OPENPITCH_REMOTE`.

## Recommended Next Steps

1. Close the HIGH item (verify seed + demo asset) — unblocks the launch gates.
2. Fix the universe-ranking global re-score (data correctness).
3. Add the `run-openpitch` project skill → Dimension 3 to GREEN.
4. Re-run this audit after launch prep to confirm all-GREEN.
