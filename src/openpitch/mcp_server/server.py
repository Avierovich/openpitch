"""OpenPitch MCP server (FRD §8, MCP-SPEC).

Local stdio server exposing the committed data to the user's agent. Read-only,
no LLM calls, no API key. Tool logic lives in `tools.py` (unit-tested); this
file is just the FastMCP wiring.
"""

from __future__ import annotations

from . import tools


def build_server():
    from mcp.server.fastmcp import FastMCP
    from mcp.types import ToolAnnotations

    mcp = FastMCP("openpitch")

    # Every tool here only READS the committed JSON: no writes, no side effects, no
    # network/LLM. Declare that so clients know they're safe to call freely.
    _READONLY = ToolAnnotations(
        readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False,
    )

    @mcp.tool(annotations=_READONLY)
    def list_companies(filter: str | None = None, segment: str = "all",
                       sort_by: str = "universe_rank", limit: int = 50) -> dict:
        """List covered AI companies with headline metrics."""
        return tools.list_companies(filter, segment, sort_by, limit)

    @mcp.tool(annotations=_READONLY)
    def get_company(id: str, include_sources: bool = True) -> dict:
        """Full profile for one company: all resolved metrics with provenance."""
        return tools.get_company(id, include_sources)

    @mcp.tool(annotations=_READONLY)
    def get_metric(company_id: str, metric: str, with_history: bool = False) -> dict:
        """One metric with value/range, confidence, estimate_type, as_of, and sources."""
        return tools.get_metric(company_id, metric, with_history)

    @mcp.tool(annotations=_READONLY)
    def get_provenance(company_id: str, metric: str) -> dict:
        """Underlying claims + confidence factors behind a metric."""
        return tools.get_provenance(company_id, metric)

    @mcp.tool(annotations=_READONLY)
    def compare_companies(ids: list[str], metrics: list[str]) -> dict:
        """Side-by-side metric comparison across companies."""
        return tools.compare_companies(ids, metrics)

    @mcp.tool(annotations=_READONLY)
    def what_moved(since: str | None = None, min_confidence: float = 0.0,
                   include_contradictions: bool = True) -> dict:
        """Material changes, contradictions, and universe entries/exits since a date."""
        return tools.what_moved(since, min_confidence, include_contradictions)

    @mcp.tool(annotations=_READONLY)
    def get_events(since: str | None = None, type: str | None = None,
                   company_id: str | None = None, min_confidence: float = 0.0) -> dict:
        """Filtered event stream (the push layer)."""
        return tools.get_events(since, type, company_id, min_confidence)

    @mcp.tool(annotations=_READONLY)
    def search(query: str) -> dict:
        """Lexical search over companies, aliases, categories, and metric keys."""
        return tools.search(query)

    return mcp


def main() -> None:
    try:
        server = build_server()
    except ModuleNotFoundError:
        raise SystemExit(
            "The 'mcp' package is required. Install with: pip install 'openpitch[mcp]' "
            "(or pip install mcp). See README."
        )
    server.run()


if __name__ == "__main__":
    main()
