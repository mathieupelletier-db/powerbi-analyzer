# tests/test_cli.py
from powerbi_analyzer.cli import app
from typer.testing import CliRunner

runner = CliRunner()


def test_pba_help_lists_subcommands():
    r = runner.invoke(app, ["--help"])
    assert r.exit_code == 0
    for sub in ["pbix", "workspace", "databricks", "scan", "init"]:
        assert sub in r.stdout


def test_pba_version_prints_version():
    r = runner.invoke(app, ["--version"])
    assert r.exit_code == 0
    assert "0.1.0" in r.stdout


def test_pba_pbix_requires_path():
    r = runner.invoke(app, ["pbix"])
    assert r.exit_code != 0


def test_pba_init_writes_yaml(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    r = runner.invoke(app, ["init"])
    assert r.exit_code == 0
    assert (tmp_path / "pba.yaml").exists()
    assert "pbix:" in (tmp_path / "pba.yaml").read_text()
