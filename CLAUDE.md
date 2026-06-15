# OpenPitch — for Claude Code

Open, MCP-native, zero-cost intelligence on AI startups. The git-tracked `data/`
tree is the database; the pipeline runs on free CI; the MCP server makes no LLM
calls (the user's agent reasons over committed JSON).

- **Coordinating with Codex / other agents?** Read `AGENTS.md` first (handoff log + rules).
- **Operating the pipeline?** Use the `run-openpitch` skill (`.claude/skills/run-openpitch/`).
- **Design & scope:** `docs/PRD.md`, `docs/FRD.md`, `docs/METHODOLOGY.md`, `docs/DATA-POLICY.md`.
- **Never commit `.env`** (secrets) — it's gitignored.
