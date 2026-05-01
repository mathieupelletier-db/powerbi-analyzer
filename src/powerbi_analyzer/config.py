"""pba.yaml loader with env-var interpolation."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

VAR_RE = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)\}")


def _interp(value: Any) -> Any:
    if isinstance(value, str):
        return VAR_RE.sub(lambda m: os.environ.get(m.group(1), ""), value)
    if isinstance(value, list):
        return [_interp(v) for v in value]
    if isinstance(value, dict):
        return {k: _interp(v) for k, v in value.items()}
    return value


class OutputConfig(BaseModel):
    formats: list[str] = ["markdown"]
    dir: str = "reports/"


class PbixConfig(BaseModel):
    files: list[str] = Field(default_factory=list)


class WorkspaceCfg(BaseModel):
    tenant_id: str = ""
    workspace_id: str = ""
    datasets: list[str] | str = "auto"
    auth: str = "device_code"


class DatabricksCfg(BaseModel):
    profile: str = "DEFAULT"
    warehouse_id: str = ""
    catalogs: list[str] = Field(default_factory=list)
    query_history_lookback_days: int = 30


class RulesCfg(BaseModel):
    ignore: list[str] = Field(default_factory=list)


class Thresholds(BaseModel):
    large_table_gb: int = 10
    visuals_per_page_max: int = 12
    string_max_length: int = 1000


class PbaConfig(BaseModel):
    output: OutputConfig = OutputConfig()
    pbix: PbixConfig = PbixConfig()
    workspace: WorkspaceCfg = WorkspaceCfg()
    databricks: DatabricksCfg = DatabricksCfg()
    rules: RulesCfg = RulesCfg()
    thresholds: Thresholds = Thresholds()


def load_config(path: Path) -> PbaConfig:
    raw = yaml.safe_load(path.read_text()) or {}
    return PbaConfig.model_validate(_interp(raw))
