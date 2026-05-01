"""Typer CLI entry point."""

from __future__ import annotations

from importlib import resources
from pathlib import Path

import typer

from powerbi_analyzer import __version__

app = typer.Typer(
    name="pba",
    help="Audit Power BI on Databricks setups against the cheat-sheet best practices.",
    no_args_is_help=True,
)


def _version_callback(show: bool) -> None:
    if show:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        help="Print version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """pba — Power BI on Databricks Analyzer."""


@app.command()
def init(
    path: Path = typer.Option(Path("pba.yaml"), "--out", help="Where to write the config."),
) -> None:
    """Write a starter pba.yaml in the current directory."""
    template = resources.files("powerbi_analyzer").joinpath("pba.example.yaml").read_text()
    path.write_text(template)
    typer.echo(f"wrote {path}")


@app.command()
def pbix(
    paths: list[Path] = typer.Argument(..., help="One or more .pbix or .pbip paths."),
    out: Path | None = typer.Option(None, "--out", help="Output path."),
    out_dir: Path | None = typer.Option(None, "--out-dir"),
    formats: str = typer.Option("markdown", "--formats", help="Comma list: markdown,html"),
    severity_threshold: str = typer.Option("info", "--severity-threshold"),
    ignore: list[str] = typer.Option([], "--ignore"),
    fail_on: str = typer.Option("none", "--fail-on"),
) -> None:
    """Mode A — analyze .pbix / .pbip files."""
    from powerbi_analyzer.cli_runners import run_pbix

    raise typer.Exit(
        run_pbix(
            paths=paths,
            out=out,
            out_dir=out_dir,
            formats=formats,
            severity_threshold=severity_threshold,
            ignore=set(ignore),
            fail_on=fail_on,
        )
    )


@app.command()
def workspace(
    workspace_id: str = typer.Option(..., "--workspace-id"),
    tenant_id: str | None = typer.Option(None, "--tenant-id"),
    dataset_id: list[str] = typer.Option([], "--dataset-id"),
    auth: str = typer.Option("device_code", "--auth"),
    out: Path | None = typer.Option(None, "--out"),
    formats: str = typer.Option("markdown", "--formats"),
    ignore: list[str] = typer.Option([], "--ignore"),
    fail_on: str = typer.Option("none", "--fail-on"),
) -> None:
    """Mode B — analyze a live Power BI workspace."""
    from powerbi_analyzer.cli_runners import run_workspace

    raise typer.Exit(
        run_workspace(
            workspace_id=workspace_id,
            tenant_id=tenant_id,
            dataset_ids=dataset_id,
            auth=auth,
            out=out,
            formats=formats,
            ignore=set(ignore),
            fail_on=fail_on,
        )
    )


@app.command()
def databricks(
    profile: str = typer.Option("DEFAULT", "--profile"),
    warehouse_id: str = typer.Option(..., "--warehouse-id"),
    catalog: list[str] = typer.Option(..., "--catalog"),
    lookback_days: int = typer.Option(30, "--lookback-days"),
    out: Path | None = typer.Option(None, "--out"),
    formats: str = typer.Option("markdown", "--formats"),
    ignore: list[str] = typer.Option([], "--ignore"),
    fail_on: str = typer.Option("none", "--fail-on"),
) -> None:
    """Mode C — analyze a Databricks SQL warehouse + catalog."""
    from powerbi_analyzer.cli_runners import run_databricks

    raise typer.Exit(
        run_databricks(
            profile=profile,
            warehouse_id=warehouse_id,
            catalogs=catalog,
            lookback_days=lookback_days,
            out=out,
            formats=formats,
            ignore=set(ignore),
            fail_on=fail_on,
        )
    )


@app.command()
def scan(
    config: Path = typer.Option(Path("pba.yaml"), "--config"),
) -> None:
    """Run all configured modes from pba.yaml."""
    from powerbi_analyzer.cli_runners import run_scan

    raise typer.Exit(run_scan(config))
