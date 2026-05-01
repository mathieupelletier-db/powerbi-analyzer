from pathlib import Path

from powerbi_analyzer.config import load_config


def test_load_config_substitutes_env(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("PBI_TENANT_ID", "tid-123")
    p = tmp_path / "pba.yaml"
    p.write_text(
        "output:\n  formats: [markdown]\n  dir: r/\n"
        "workspace:\n  tenant_id: ${PBI_TENANT_ID}\n  workspace_id: ws\n  auth: device_code\n"
    )
    cfg = load_config(p)
    assert cfg.workspace.tenant_id == "tid-123"
    assert cfg.workspace.workspace_id == "ws"
