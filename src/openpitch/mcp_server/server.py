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
        """List covered AI companies with headline metrics.

        A metric with status 'withheld' failed a plausibility check: say it exists and why, never state its value.
        """
        return tools.list_companies(filter, segment, sort_by, limit)

    @mcp.tool(annotations=_READONLY)
    def get_company(id: str, include_sources: bool = True) -> dict:
        """Full profile for one company: all resolved metrics with provenance.

        A metric with status 'withheld' failed a plausibility check: say it exists and why, never state its value.
        """
        return tools.get_company(id, include_sources)

    @mcp.tool(annotations=_READONLY)
    def get_metric(company_id: str, metric: str, with_history: bool = False) -> dict:
        """One metric with value/range, confidence, estimate_type, as_of, and sources.

        Returns status 'withheld' (no value) when the figure failed a plausibility
        check: say it exists and why, never state its value. get_provenance has the raw claims.
        """
        return tools.get_metric(company_id, metric, with_history)

    @mcp.tool(annotations=_READONLY)
    def get_provenance(company_id: str, metric: str) -> dict:
        """Underlying claims + confidence factors behind a metric.

        The audit path: raw claims are returned even for a withheld figure. When
        `gate.action` is 'withhold', do not cite any claim's value as the figure;
        `gate_flag` marks the claims behind it.
        """
        return tools.get_provenance(company_id, metric)

    @mcp.tool(annotations=_READONLY)
    def compare_companies(ids: list[str], metrics: list[str]) -> dict:
        """Side-by-side metric comparison across companies.

        A null cell means no data; a {"status": "withheld"} cell means the figure failed a
        plausibility check. Never state a withheld value.
        """
        return tools.compare_companies(ids, metrics)

    @mcp.tool(annotations=_READONLY)
    def what_moved(since: str | None = None, min_confidence: float = 0.0,
                   include_contradictions: bool = True, limit: int = 50) -> dict:
        """Material changes, contradictions, and universe entries/exits.

        Newest-first, capped at `limit` (default 50). If `since` is omitted, defaults to a
        30-day window (echoed back as `since`). Narrow with `since`/`min_confidence` when
        `truncated` is true; `total` is the pre-cap count. Events about a withheld
        figure carry no numbers.
        """
        return tools.what_moved(since, min_confidence, include_contradictions, limit)

    @mcp.tool(annotations=_READONLY)
    def get_events(since: str | None = None, type: str | None = None,
                   company_id: str | None = None, min_confidence: float = 0.0,
                   limit: int = 50) -> dict:
        """Filtered event stream (the push layer).

        Newest-first, capped at `limit` (default 50). Narrow with `since` (YYYY-MM-DD),
        `type`, `company_id`, or `min_confidence` when `truncated` is true; `total` is the
        pre-cap count. Events about a withheld figure carry no numbers.
        """
        return tools.get_events(since, type, company_id, min_confidence, limit)

    @mcp.tool(annotations=_READONLY)
    def search(query: str, limit: int = 25) -> dict:
        """Lexical search over companies, aliases, categories, and metric keys.

        Capped at `limit` (default 25); `total`/`truncated` report if more matched.
        """
        return tools.search(query, limit)

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
