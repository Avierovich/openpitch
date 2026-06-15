---
name: run-openpitch
description: Operate the OpenPitch pipeline and interfaces — build the dataset, run the live refresh, serve the MCP server, build the dashboard, and run tests. Use when asked to run, refresh, seed, serve, or test OpenPitch, or to regenerate its data/dashboard.
---

# Run OpenPitch

Prescriptive runbook for operating the OpenPitch pipeline. The git-tracked
`data/` tree is the database; everything is reproducible and zero-cost.

## 0. Environment (once)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[pipeline]"        # core + Gemini provider
```

Secrets go in a gitignored `.env` (never commit it):
- `LLM_API_KEY` — free Gemini key (extraction). Without it, only `seed` works.
- `GROQ_API_KEY` — free Groq key (hosted Whisper transcription). Optional.
- `OPENPITCH_SEC_USER_AGENT` — `OpenPitch/0.1 you@example.com` (EDGAR fair-access).

## 1. Build the dataset (offline, no key)

```bash
openpitch seed          # reconcile committed seed claims -> data/ (idempotent same-day)
```
Produces `data/companies/*.json`, history, events, digest, universe, index.

## 2. Live refresh (needs LLM key + network)

```bash
openpitch run                       # all watchlist companies
openpitch run --companies 5         # first 5 (quota-safe for a test)
openpitch run --ids openai,mistral  # specific companies
openpitch run --offline             # falls back to seed
```
Stages: collect → transcribe → extract (batched) → derive → reconcile → publish.
Fail-isolated per company. Scoring is global (ranks the full committed set).

## 3. Build the dashboard + A2A card

```bash
openpitch build-dashboard           # -> dashboard/dist/ (open index.html)
```

## 4. Serve the MCP server (read-only, no LLM, no key)

```bash
openpitch-mcp                       # stdio MCP server over committed data
```
Register it: `claude mcp add openpitch -- openpitch-mcp` (Claude Code) or add
`[mcp_servers.openpitch]` to `~/.codex/config.toml`.

## 5. Test & verify

```bash
PYTHONPATH=src pytest tests/ -q     # full suite
openpitch quality-report            # data-quality gaps -> data/quality/report.md
```

## Guardrails

- Never commit `.env` or real secrets (DATA-POLICY).
- Prefer published transcripts; transcription stores only short phrases, never full transcripts.
- Respect source ToS / robots; official APIs and RSS first.
- Data is probabilistic public-source intelligence — every figure keeps its source + confidence.
