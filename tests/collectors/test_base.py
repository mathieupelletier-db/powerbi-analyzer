# tests/collectors/test_base.py
import pytest
from powerbi_analyzer.collectors.base import Collector, CollectorError


def test_collector_error_message_field():
    e = CollectorError("auth failed", mode="workspace")
    assert e.mode == "workspace"
    assert "auth failed" in str(e)


def test_collector_subclass_must_implement_collect():
    class Stub(Collector):
        mode = "stub"

    with pytest.raises(NotImplementedError):
        Stub().collect()
