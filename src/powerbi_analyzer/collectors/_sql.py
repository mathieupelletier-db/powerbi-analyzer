"""Thin SQL executor abstraction so tests can stub system-table queries."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class SqlExecutor(ABC):
    @abstractmethod
    def execute(self, query: str) -> list[dict[str, Any]]: ...

    @abstractmethod
    def describe_extended(self, table: str) -> dict[str, Any]: ...
