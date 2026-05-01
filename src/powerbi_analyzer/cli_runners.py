# src/powerbi_analyzer/cli_runners.py
"""CLI command implementations. Stubs until collectors land."""

from __future__ import annotations

from pathlib import Path


def run_pbix(**_: object) -> int:
    raise NotImplementedError("pba pbix wiring lands in a later task")


def run_workspace(**_: object) -> int:
    raise NotImplementedError("pba workspace wiring lands in a later task")


def run_databricks(**_: object) -> int:
    raise NotImplementedError("pba databricks wiring lands in a later task")


def run_scan(_config: Path) -> int:
    raise NotImplementedError("pba scan wiring lands in a later task")
