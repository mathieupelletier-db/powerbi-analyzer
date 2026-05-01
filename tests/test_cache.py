# tests/test_cache.py
from pathlib import Path

from powerbi_analyzer.cache import RunCache


def test_run_cache_writes_and_reads(tmp_path: Path):
    cache = RunCache(root=tmp_path, run_id="abc123")
    cache.write("warehouse", {"id": "wh1", "type": "serverless"})
    assert cache.read("warehouse") == {"id": "wh1", "type": "serverless"}


def test_run_cache_redacts_sensitive_keys(tmp_path: Path):
    cache = RunCache(root=tmp_path, run_id="abc123")
    payload = {
        "tenant_id": "11111111-2222-3333-4444-555555555555",
        "connection_string": "Server=myserver;User=foo;Password=secret",
        "rows": [{"name": "ok"}],
    }
    cache.write("workspace", payload)
    raw = (tmp_path / "abc123" / "workspace.json").read_text()
    assert "secret" not in raw
    assert "11111111-2222-3333-4444-555555555555" not in raw
