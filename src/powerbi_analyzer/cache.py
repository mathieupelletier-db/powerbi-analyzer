"""Per-run cache for collector outputs with redaction."""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any

GUID_RE = re.compile(r"\b[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}\b")
PWD_RE = re.compile(r"(password|pwd|secret|token)=[^;\"\s]+", re.IGNORECASE)


def redact(value: Any) -> Any:
    if isinstance(value, str):
        v = GUID_RE.sub("<REDACTED-GUID>", value)
        v = PWD_RE.sub(r"\1=<REDACTED>", v)
        return v
    if isinstance(value, dict):
        return {k: redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


class RunCache:
    def __init__(self, root: Path | None = None, run_id: str | None = None) -> None:
        self.root = root or (Path.home() / ".cache" / "pba")
        self.run_id = run_id or uuid.uuid4().hex
        self._dir = self.root / self.run_id
        self._dir.mkdir(parents=True, exist_ok=True)

    def write(self, key: str, payload: Any) -> Path:
        path = self._dir / f"{key}.json"
        path.write_text(json.dumps(redact(payload), indent=2, default=str))
        return path

    def read(self, key: str) -> Any:
        return json.loads((self._dir / f"{key}.json").read_text())

    @property
    def short_id(self) -> str:
        return self.run_id[:6]
