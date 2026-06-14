# Feature Spec — Zero-Friction Install & Public Data

| | |
|---|---|
| **Author** | Mohamed Abdulhadi (PM) |
| **Date** | 2026-06-14 |
| **Method** | product-management plugin → `feature-spec` skill |
| **Status** | Draft for build |
| **Companions** | [PRD](PRD.md), [FRD](FRD.md), [MCP-SPEC](MCP-SPEC.md), [LAUNCH-GATES](LAUNCH-GATES.md) |

## 1. Problem Statement
An AI builder who wants OpenPitch in their agent today must clone the repo, set up a venv, install editable, and run `seed` — friction that kills the "no signup, 60-second" promise and blocks the beachhead ICP. Every extra step loses users; our own analysis shows the *agent-builder* segment is where retained usage (PMF) lives, and they expect a one-line install. Not solving it caps adoption at people willing to clone a Python repo — a tiny fraction of the target audience.

## 2. Goals
- **G1 (user):** A new user goes from zero to a sourced in-agent answer in **under 60 seconds**, with no clone and no key.
- **G2 (user):** Data stays fresh for installed users **without** them re-running the pipeline (auto-pull latest committed data).
- **G3 (business):** Maximize **activation rate** (installs that produce ≥1 successful query) — the leading PMF signal.
- **G4 (business):** Make the install command **copy-paste identical** across Claude Code and Codex docs/registries.
- **G5 (trust):** Zero degradation of provenance — remote-fetched answers carry the same sources/confidence as local.

## 3. Non-Goals
- **Hosted remote MCP endpoint** (for claude.ai web custom connectors) — separate initiative; adds hosting cost, breaks local-first. *(Premature.)*
- **Auth / user accounts** — the product is read-only and anonymous by design. *(Out of scope, forever.)*
- **Write access / user-submitted data via MCP** — corrections go through GitHub issues, not the server. *(Separate workflow.)*
- **Real-time data** — daily refresh stands; install changes don't touch cadence. *(No impact.)*
- **Windows-native packaging** — `uvx`/`pipx` cover it; no separate installer. *(Not enough impact for v1.)*

## 4. User Stories
1. As an **AI builder on Claude Code**, I want to add OpenPitch with one command so that my agent can answer AI-startup questions without me cloning anything.
2. As a **Codex user**, I want the same one-line install in my `config.toml` so that switching tools costs nothing.
3. As an **installed user**, I want the server to fetch the latest committed data automatically so that I'm never reading stale numbers without re-installing.
4. As a **privacy-minded user**, I want it to work with **no API key and no signup** so that I can try it with zero commitment.
5. As an **offline user** (edge case), I want a clear, non-hallucinatory response when the data source is unreachable so that I'm not given a fabricated answer.
6. As a **contributor**, I want `pip install -e .` + local data to still take precedence so that dev workflows aren't broken by the remote path.

## 5. Requirements

### Must-Have (P0)
- **P0-1 PyPI package** — `openpitch` published; `openpitch-mcp` console entry point resolves via `uvx`/`pipx`. `mcp` is a core dep (done).
  - *Given* a clean machine with `uv`, *when* the user runs `uvx openpitch-mcp`, *then* the server starts and lists all 8 tools.
- **P0-2 Remote data fetch** — server reads committed data/config from the public repo when absent locally, cached with TTL (done in `paths.resolve_remote` + `store`/`config`).
  - *Given* no local `data/`, *when* a tool is called, *then* it fetches from `OPENPITCH_REMOTE` and returns a correct sourced answer.
- **P0-3 No-data integrity** — unreachable source or missing metric returns an explicit `not_found`/`data_unavailable` status, never a fabricated value (MCP-SPEC).
- **P0-4 Local precedence** — if local `data/` exists (contributor), it's used over remote.
- **P0-5 One-line install docs** — README + MCP directory entries show identical copy-paste for Claude Code and Codex.

### Nice-to-Have (P1)
- **P1-1** Cache freshness indicator — surface `as_of` / "data fetched N hrs ago" in `list_companies`.
- **P1-2** `openpitch --version` / health command for support triage.
- **P1-3** Submit to MCP directories (Glama, mcp.so, awesome-mcp) for discovery.

### Future Considerations (P2)
- **P2-1** Hosted remote MCP endpoint (enables claude.ai web connectors) — design the data contract so this is additive.
- **P2-2** Signed/versioned data releases (integrity verification).

## 6. Success Metrics

**Leading (days–weeks):**
- **Activation rate** — % of installs producing ≥1 successful tool call. Target **≥60%**; stretch 75%. *(Measure: opt-in anonymous ping or directory + issue signal; 30-day window.)*
- **Time-to-first-answer** — README → first answer. Target **<60s** on a clean machine. *(Measure: timed clean-machine test.)*
- **Clean-machine install success** — Target **100%** on macOS + Linux. *(Measure: CI matrix.)*

**Lagging (weeks–months):**
- **Retained users** — distinct users querying ≥1×/week (the North Star). Target **50** by month 1.
- **Directory-sourced installs** — share of installs from MCP directories vs README.
- **Support load** — install-related issues per 100 installs trending to **<5**.

## 7. Open Questions
- **[BLOCKING · stakeholder]** PyPI package name (`openpitch` available?) and public GitHub `OWNER/repo` for `OPENPITCH_REMOTE`.
- **[BLOCKING · eng]** Cache TTL default (currently 1h) — balance freshness vs rate-limit on raw GitHub.
- **[non-blocking · data]** How to measure activation without violating the no-signup/privacy promise (opt-in only?).
- **[non-blocking · eng]** `uvx` cold-start time on first run — is it within the 60s budget on slow networks?

## 8. Timeline Considerations
- **Dependency:** must follow "verify seed data" (LAUNCH-GATES) — don't publish stale data.
- **Suggested phasing:** (1) P0-2/3/4 are already built & tested → (2) publish to PyPI + set `OPENPITCH_REMOTE` (P0-1/P0-5, account actions) → (3) P1 directory submissions during launch week.
- **No hard external deadline**, but install friction blocks the 30-day growth plan, so this gates GTM.
