"""Collector base + shared error type."""

from __future__ import annotations

from typing import Any


class CollectorError(RuntimeError):
    def __init__(self, message: str, *, mode: str) -> None:
        super().__init__(message)
        self.mode = mode


class Collector:
    mode: str = "base"

    def collect(self) -> Any:
        raise NotImplementedError
