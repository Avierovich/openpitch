# Security Policy

## Reporting a vulnerability

Please **do not** open a public issue for security vulnerabilities.

Report privately via GitHub's [Report a vulnerability](https://github.com/Avierovich/openpitch/security/advisories/new)
(Security → Advisories). Include a description, reproduction steps, and impact. We aim to
acknowledge within 72 hours and to coordinate a fix and disclosure timeline with you.

## Scope

OpenPitch is a zero-cost, read-mostly project. The most relevant areas:

- **The MCP server (`openpitch-mcp`)** — read-only over local committed JSON; makes no LLM
  calls and holds no credentials. Report anything that lets it write, execute, or exfiltrate.
- **The pipeline** — fetches public web/RSS/EDGAR sources and calls an LLM with a user-supplied
  key. Report SSRF, unsafe deserialization, or key-leakage paths.
- **Secrets** — `.env` is gitignored and never committed. Report any path that would commit or
  log a key (`LLM_API_KEY`, `GROQ_API_KEY`).

## Supported versions

The latest `main` and the most recent release receive fixes.
