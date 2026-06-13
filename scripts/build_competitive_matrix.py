"""Generate docs/competitive-matrix.xlsx — the competitor mapping (PM/PMM artifact).

Reproducible: `python scripts/build_competitive_matrix.py`. Mirrors
docs/COMPETITIVE-ANALYSIS.md. Single source of truth for the data lives here.
"""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

OUT = Path(__file__).resolve().parents[1] / "docs" / "competitive-matrix.xlsx"

COMPETITORS = [
    "PitchBook", "CB Insights", "Crunchbase", "Harmonic", "MAGNiTT", "Wamda", "OpenPitch",
]

# ── styling ──────────────────────────────────────────────────────────────────
NAVY = "1F2A44"
ACCENT = "2E7D6F"
HDR_FONT = Font(bold=True, color="FFFFFF", size=11)
HDR_FILL = PatternFill("solid", fgColor=NAVY)
US_FILL = PatternFill("solid", fgColor="E3F2EF")          # highlight OpenPitch col
YES_FILL = PatternFill("solid", fgColor="C8E6C9")
PARTIAL_FILL = PatternFill("solid", fgColor="FFF3C4")
NO_FILL = PatternFill("solid", fgColor="F5D5D0")
THIN = Side(style="thin", color="D0D0D0")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(wrap_text=True, vertical="top")
CENTER = Alignment(horizontal="center", vertical="center")


def _style_header(ws, ncols: int, row: int = 1) -> None:
    for c in range(1, ncols + 1):
        cell = ws.cell(row=row, column=c)
        cell.font = HDR_FONT
        cell.fill = HDR_FILL
        cell.alignment = CENTER
        cell.border = BORDER


def _grid(ws, nrows: int, ncols: int) -> None:
    for r in range(1, nrows + 1):
        for c in range(1, ncols + 1):
            ws.cell(row=r, column=c).border = BORDER


def _mark_fill(ws, header_row: list[str]) -> None:
    """Color ✓/◐/✗ cells and shade the OpenPitch column."""
    us_col = header_row.index("OpenPitch") + 1 if "OpenPitch" in header_row else None
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            v = str(cell.value).strip() if cell.value is not None else ""
            if v == "✓":
                cell.fill = YES_FILL
            elif v == "◐":
                cell.fill = PARTIAL_FILL
            elif v == "✗":
                cell.fill = NO_FILL
            if us_col and cell.column == us_col and not v.startswith(("✓", "◐", "✗")):
                cell.fill = US_FILL
            cell.alignment = CENTER if len(v) <= 3 else WRAP


# ── sheet 1: overview ────────────────────────────────────────────────────────
OVERVIEW = [
    ["Dimension", *COMPETITORS],
    ["Type", "Institutional data", "Market intelligence", "Company DB", "Sourcing graph",
     "Regional venture data", "Ecosystem media", "Open signal layer"],
    ["Region focus", "Global", "Global", "Global", "Global", "MENA + emerging", "MENA",
     "Global AI + MENA-AI"],
    ["Pricing (approx, est.)", "~$20–40k+/yr", "~$25–100k/yr", "Free / $49–99·mo / Ent",
     "Custom", "$ low-thousands/yr", "Free / paid reports", "$0 (open source)"],
    ["Free tier", "✗", "✗", "✓", "◐", "◐", "✓", "✓"],
    ["Target user", "VC/PE/IB", "Corp strategy, VC", "Sales/BD, founders", "VCs sourcing",
     "Regional VC/LP/gov", "MENA ecosystem", "AI devs, founders, VCs, press"],
    ["Coverage breadth", "Very high", "High", "Very high", "High", "High (MENA)", "Med (MENA)",
     "Narrow (by design)"],
    ["Verification", "Human-verified", "Human + ML", "Crowd + ML", "ML/graph",
     "Research + submissions", "Editorial", "Probabilistic + sourced"],
    ["Freshness", "Weeks–months", "Weeks", "Variable", "Days (team)", "Weeks", "Editorial",
     "Daily"],
    ["AI / agent-native", "Add-on copilot", "ChatCBI add-on", "Some AI", "API/agent-ish",
     "Limited", "✗", "Native (MCP)"],
    ["Open source", "✗", "✗", "✗", "✗", "✗", "✗", "✓"],
]

# ── sheet 2: feature matrix ──────────────────────────────────────────────────
FEATURES = [
    ["Feature", *COMPETITORS],
    ["Funding-round data", "✓", "✓", "✓", "✓", "✓", "◐", "✓"],
    ["Valuations", "✓", "✓", "◐", "◐", "◐", "✗", "✓"],
    ["ARR / revenue estimates", "◐", "◐", "✗", "✗", "✗", "✗", "✓"],
    ["Verified financial statements", "✓", "◐", "✗", "✗", "◐", "✗", "✗"],
    ["Headcount / growth signals", "✓", "✓", "◐", "✓", "◐", "✗", "✓"],
    ["People / founder graph", "◐", "◐", "◐", "✓", "◐", "✗", "✗"],
    ["Podcast / alt-data mining", "✗", "◐", "✗", "◐", "✗", "✗", "✓"],
    ["Source citations per figure", "◐", "◐", "◐", "✗", "◐", "◐", "✓"],
    ["Confidence scoring", "✗", "◐", "✗", "◐", "✗", "✗", "✓"],
    ["Contradiction detection", "✗", "✗", "✗", "✗", "✗", "✗", "✓"],
    ["Daily freshness", "✗", "✗", "◐", "◐", "✗", "✗", "✓"],
    ["MCP / agent-native", "✗", "✗", "✗", "◐", "✗", "✗", "✓"],
    ["Public API", "✓", "✓", "✓", "✓", "◐", "✗", "✓"],
    ["Event / webhook feed", "◐", "◐", "◐", "✓", "✗", "✗", "✓"],
    ["MENA AI coverage", "◐", "◐", "◐", "◐", "✓", "✓", "✓"],
    ["Analyst reports / market maps", "✓", "✓", "✗", "✗", "◐", "✓", "✗"],
    ["Free / open source", "✗", "✗", "◐", "✗", "✗", "◐", "✓"],
]

# ── sheet 3: pricing ─────────────────────────────────────────────────────────
PRICING = [
    ["Provider", "List price (est.)", "Free tier", "Pricing model", "Public?", "Notes"],
    ["PitchBook", "~$20–40k+/yr", "No", "Per-seat annual", "No", "Morningstar-owned; quote-based"],
    ["CB Insights", "~$25–100k/yr", "No", "Enterprise annual", "No", "Wide range by org/modules"],
    ["Crunchbase", "Free / $49–99·mo / Ent", "Yes", "Freemium + API", "Partly", "API priced separately"],
    ["Harmonic", "Custom", "Limited", "Seat / API", "No", "Sourcing-focused; quote-based"],
    ["MAGNiTT", "$ low-thousands/yr", "Limited", "Subscription + reports", "No", "Best MENA/EM data"],
    ["Wamda", "Free / paid reports", "Yes", "Media + research", "Partly", "Not a data platform"],
    ["OpenPitch", "$0", "Yes (all)", "Open source", "Yes", "Free to run & to use"],
]

# ── sheet 4: positioning ─────────────────────────────────────────────────────
POSITIONING = [
    ["Where OpenPitch COMPETES (the wedge)", "Where OpenPitch does NOT compete"],
    ["Price — free & open vs $20k–100k/yr", "Coverage breadth (millions of companies)"],
    ["Latency — daily, podcast-driven", "Verified deal accuracy (diligence-grade)"],
    ["AI-agent-native (MCP, in Claude Code/Codex)", "Historical depth (decades of data)"],
    ["Transparency — source + confidence + history", "People / founder graph (Harmonic)"],
    ["Contradiction detection (uniquely ours)", "Analyst services & market maps"],
    ["Composability — event layer for other agents", "Institutional trust / compliance / SLAs"],
    ["Focus — AI startups + MENA-AI", "Non-AI sectors"],
    ["", ""],
    ["Positioning statement:", ""],
    ["\"The free, fresh, AI-native first look at AI-startup intelligence — every number "
     "sourced, confidence-scored, tracked in git — before you pull the expensive verified report.\"", ""],
]


def write_sheet(wb, title: str, rows: list[list], widths: list[int]) -> None:
    ws = wb.create_sheet(title)
    for r, row in enumerate(rows, start=1):
        for c, val in enumerate(row, start=1):
            ws.cell(row=r, column=c, value=val)
    _grid(ws, len(rows), len(rows[0]))
    _style_header(ws, len(rows[0]))
    if title in ("Feature Matrix", "Overview"):
        _mark_fill(ws, rows[0])
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "B2"


def main() -> None:
    wb = Workbook()
    wb.remove(wb.active)
    write_sheet(wb, "Overview", OVERVIEW, [22] + [18] * len(COMPETITORS))
    write_sheet(wb, "Feature Matrix", FEATURES, [30] + [13] * len(COMPETITORS))
    write_sheet(wb, "Pricing", PRICING, [14, 24, 12, 22, 9, 34])
    write_sheet(wb, "Positioning", POSITIONING, [52, 44])
    wb.save(OUT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
