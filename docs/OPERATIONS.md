# Operations

## Purpose

This document captures the local and GitHub operational setup needed to run OpenPitch safely.

## Local Environment

Local secrets live in `.env`, which is gitignored.

Required for live extraction:

```env
OPENPITCH_LLM=gemini
LLM_API_KEY=...
```

Optional but recommended:

```env
GROQ_API_KEY=...
OPENPITCH_SEC_USER_AGENT=OpenPitch/0.1 you@example.com
```

Do not commit `.env`, personal emails, API keys, bearer tokens, audio files, model weights, or dashboard build output.

## GitHub Actions Secrets

The scheduled daily refresh workflow expects these repository secrets:

- `LLM_API_KEY` - enables live LLM extraction.
- `GROQ_API_KEY` - enables hosted podcast transcription.
- `OPENPITCH_SEC_USER_AGENT` - provides SEC EDGAR fair-access identification.

If `LLM_API_KEY` is missing, the workflow falls back to the committed seed path.

## Pre-Push Safety

Before pushing, run:

```bash
PYTHONPATH=src .venv/bin/python -m pytest
.venv/bin/ruff check src tests
git diff --check
.venv/bin/python -m pip_audit
```

Check staged files explicitly:

```bash
git diff --cached --name-only
git diff --cached
```

Do not stage generated `data/` refreshes with code changes unless the data diff is intentionally being reviewed.

## Current Operational Notes

- The selected logo direction is `docs/brand/logo-options/05-terminal-proof.svg`.
- The dashboard builds to `dashboard/dist/`, which is ignored by git.
- The MCP server and dashboard read committed JSON data; they should not make LLM calls at query time.

## Post-GitHub-Push Install Completion

After the repository is pushed to GitHub, validate the frictionless source install from a clean directory:

```bash
git clone <repo-url> /tmp/openpitch-install-test
cd /tmp/openpitch-install-test
python -m venv .venv
source .venv/bin/activate
pip install -e ".[mcp]"
openpitch seed
openpitch-mcp --help
```

Then verify the MCP config snippet in the README can start `openpitch-mcp` from a real agent client.

If the clone install, `openpitch seed`, and agent MCP startup all pass, update:

- `docs/LAUNCH-GATES.md` clean-machine install status to **Fully complete**.
- `README.md` install language from "run it now from source" to "install from GitHub/source" with the real repo URL.

Keep `uvx --from openpitch openpitch-mcp` labeled as a future release-channel path until the package is actually published and tested.
