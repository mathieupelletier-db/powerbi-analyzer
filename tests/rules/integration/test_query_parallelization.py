from powerbi_analyzer.domain.finding import Status
from powerbi_analyzer.domain.semantic_model import ParallelismConfig
from powerbi_analyzer.rules.integration import query_parallelization as rule
from tests.builders import make_workspace_config


def test_passes_when_tuned():
    cfg = make_workspace_config(
        parallelism=ParallelismConfig(
            max_parallelism_per_query=10,
            max_simultaneous_evaluations=10,
        )
    )
    assert rule.check(cfg).status is Status.PASS


def test_fails_when_default():
    cfg = make_workspace_config(parallelism=ParallelismConfig(max_parallelism_per_query=1))
    assert rule.check(cfg).status is Status.FAIL


def test_fails_when_low_simultaneous_evaluations():
    cfg = make_workspace_config(
        parallelism=ParallelismConfig(
            max_parallelism_per_query=10,
            max_simultaneous_evaluations=2,
        )
    )
    f = rule.check(cfg)
    assert f.status is Status.FAIL
    assert any("MaxSimultaneousEvaluations" in s for s in f.evidence["settings"])
