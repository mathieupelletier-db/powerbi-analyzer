from powerbi_analyzer.domain.finding import Status
from powerbi_analyzer.domain.semantic_model import Parameter
from powerbi_analyzer.rules.integration import use_parameters as rule

from tests.builders import make_semantic_model


def test_passes_when_endpoint_param():
    m = make_semantic_model(parameters=[Parameter(name="warehouse_endpoint", data_type="text")])
    assert rule.check(m).status is Status.PASS


def test_fails_when_no_endpoint_param():
    assert rule.check(make_semantic_model()).status is Status.FAIL


def test_passes_when_server_param():
    m = make_semantic_model(parameters=[Parameter(name="server_hostname", data_type="text")])
    assert rule.check(m).status is Status.PASS
