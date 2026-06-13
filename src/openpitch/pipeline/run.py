"""Pipeline orchestrator / CLI (FRD §7, §11).

Usage:
    openpitch run --all          # full daily pass, stages 1–7
    openpitch run --stage extract
    openpitch build-dashboard

Each stage is fail-isolated: one company (or one source) failing is logged,
not fatal. Runs are idempotent and incremental (cache by content hash).

NOTE: stages are scaffolded stubs — see the roadmap in README.md.
"""

from __future__ import annotations

import typer

app = typer.Typer(add_completion=False, help="OpenPitch daily pipeline.")


@app.command()
def run(
    all: bool = typer.Option(False, "--all", help="Run all stages 1–7."),
    stage: str | None = typer.Option(None, help="Run a single stage by name."),
) -> None:
    """Run the daily pipeline (or a single stage)."""
    stages = ["select", "collect", "transcribe", "extract", "reconcile", "score", "publish"]
    to_run = stages if all else ([stage] if stage else [])
    if not to_run:
        typer.echo("Nothing to do. Pass --all or --stage <name>.")
        raise typer.Exit(1)
    for name in to_run:
        typer.echo(f"[stage] {name}: not yet implemented")  # TODO: wire stages
    raise typer.Exit(0)


@app.command()
def build_dashboard() -> None:
    """Build the static dashboard from git-tracked data (FRD §9)."""
    typer.echo("build-dashboard: not yet implemented")


if __name__ == "__main__":
    app()
