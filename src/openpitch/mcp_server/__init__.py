"""Local MCP server — the primary read interface (FRD §8).

Runs on the user's machine (stdio), plugged into Claude Code / Codex.
Makes ZERO LLM calls of its own: it reads the git-tracked JSON and returns
structured data; the user's own agent does the reasoning (FRD §8.6).
Every numeric response carries value, range, confidence, estimate_type,
as_of, and sources — provenance is never stripped.
"""
