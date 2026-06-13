"""OpenPitch MCP server entrypoint (FRD §8.1).

Exposes read-only tools over the git-tracked dataset:
  list_companies · get_company · get_metric · compare_companies
  what_moved · get_provenance · get_events · search

Scaffold only — tools to be implemented with the FastMCP SDK.
"""

from __future__ import annotations


def main() -> None:
    """Start the stdio MCP server."""
    raise SystemExit(
        "openpitch-mcp: not yet implemented. "
        "See FRD §8 for the tool spec and the roadmap in README.md."
    )


if __name__ == "__main__":
    main()
