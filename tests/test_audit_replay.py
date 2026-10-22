import copy
from dataclasses import replace
from pathlib import Path

import pytest

from ruleaudit.audit import audit_case, check_corpus
from ruleaudit.config import Config, Generation
from ruleaudit.corpus import load_corpus
from ruleaudit.derive import derive
from ruleaudit.generate import target_attempt
from ruleaudit.io import InputError, content_hash
from ruleaudit.ir import Binary, Const, Var
from ruleaudit.records import make_witness
from ruleaudit.replay import replay
from ruleaudit.rewrite import RunLimits, Schedule
from ruleaudit.solver import SolverLimits, Z3Backend

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize("h,delta", [(0, 0), (1, 1), (2, 0)])
def test_budget_pair_uses_identical_settings_minus_exactly_target(h: int, delta: int) -> None:
    corpus = load_corpus(FIXTURES / "budget.json")
    checked = check_corpus(corpus).checked
    assert checked is not None
    expression = Binary("add", Binary("add", Var("x"), Const(0)), Const(0))
    pair = audit_case(
        expression, "A", checked, Schedule("preorder", ("A", "B", "C")), RunLimits(h=h)
    )
    assert pair.comparable
    assert pair.delta == delta
    assert pair.without_priority == ("B", "C")
    assert all(step.rule_id != "A" for step in pair.without_target.trace)


def make_example() -> tuple[Config, dict[str, object]]:
    corpus = load_corpus(FIXTURES / "interference.json")
    config = Config(
        Schedule("preorder", ("A", "B", "D", "C")),
        run=RunLimits(h=4),
        generation=Generation(cases=1, depth=0),
    )
    checked = check_corpus(corpus).checked
    assert checked is not None
    case = target_attempt(corpus.rules[0], config.generation, 1)
    assert case is not None
    pair = audit_case(case.expression, "A", checked, config.schedule, config.run)
    assert pair.comparable and pair.delta == 2
    templates = derive(corpus.rules[0], corpus.rules).witnesses
    witness = make_witness(corpus, config, case, pair, templates)
    return config, witness  # type: ignore[return-value]


def test_interference_witness_and_replay_are_self_contained() -> None:
    _, witness = make_example()
    result = replay(witness)  # type: ignore[arg-type]
    assert result["status"] == "verified"
    assert result["delta"] == 2
    assert result["alternative_checked"] is True


def test_partial_arm_or_solver_unknown_is_never_comparable() -> None:
    corpus = load_corpus(FIXTURES / "budget.json")
    checked = check_corpus(corpus).checked
    assert checked is not None
    schedule = Schedule("preorder", ("A", "B", "C"))
    expr = Binary("add", Binary("add", Var("x"), Const(0)), Const(0))
    partial = audit_case(expr, "A", checked, schedule, RunLimits(seconds=0))
    assert not partial.comparable
    unknown = audit_case(
        expr, "A", checked, schedule, RunLimits(h=1), backend=Z3Backend(SolverLimits(max_calls=0))
    )
    assert unknown.delta == 1 and not unknown.comparable


def test_replay_rejects_hash_trace_cost_seed_and_schema_tampering() -> None:
    _, witness = make_example()
    bad = copy.deepcopy(witness)
    bad["sha256"] = "0" * 64
    with pytest.raises(InputError, match="hash"):
        replay(bad)  # type: ignore[arg-type]
    for field in ("cost", "trace", "seed"):
        bad = copy.deepcopy(witness)
        payload = bad["payload"]
        assert isinstance(payload, dict)
        if field == "cost":
            payload["paired"]["with_target"]["cost"] = True
        elif field == "trace":
            payload["paired"]["without_target"]["trace"][0]["rule_id"] = "A"
        else:
            payload["provenance"]["seed"] = 999
        bad["sha256"] = content_hash(payload)
        with pytest.raises(InputError):
            replay(bad)  # type: ignore[arg-type]
    bad = copy.deepcopy(witness)
    bad["schema_version"] = 2
    with pytest.raises(InputError, match="version"):
        replay(bad)  # type: ignore[arg-type]


def test_pair_preserves_permuted_priority_and_rejects_unusable_corpora() -> None:
    corpus = load_corpus(FIXTURES / "budget.json")
    checked = check_corpus(corpus).checked
    assert checked is not None
    expression = Binary("add", Binary("add", Var("x"), Const(0)), Const(0))
    result = audit_case(
        expression, "A", checked, Schedule("postorder", ("C", "A", "B")), RunLimits(h=1)
    )
    assert result.without_priority == ("C", "B")
    assert result.with_target.trace[0].rule_id == result.without_target.trace[0].rule_id == "C"
    invalid = replace(corpus, rules=(replace(corpus.rules[0], rhs=Const(42)), *corpus.rules[1:]))
    assert check_corpus(invalid).status == "invalid"
    assert check_corpus(invalid).checked is None
    assert check_corpus(corpus, backend=Z3Backend(SolverLimits(max_calls=0))).status == "unknown"


@pytest.mark.parametrize(
    "change", ["snapshot", "config", "target_reuse", "ground_location", "template_start_bound"]
)
def test_replay_rechecks_modified_evidence_even_with_recomputed_hashes(change: str) -> None:
    _, witness = make_example()
    bad = copy.deepcopy(witness)
    payload = bad["payload"]
    assert isinstance(payload, dict)
    if change == "snapshot":
        payload["corpus_hash"] = "f" * 64
    elif change == "config":
        payload["config"]["run"]["h"] = 0
        payload["config_hash"] = content_hash(payload["config"])
    elif change == "target_reuse":
        payload["alternative"]["template"]["steps"][0]["rule_id"] = "A"
    elif change == "template_start_bound":
        payload["config"]["search"]["max_nodes"] = 3
        payload["config_hash"] = content_hash(payload["config"])
    else:
        payload["alternative"]["target_location"] = [1]
    bad["sha256"] = content_hash(payload)
    with pytest.raises(InputError):
        replay(bad)  # type: ignore[arg-type]


def test_saved_m3_v1_fixture_replays_without_regenerating_its_report() -> None:
    from ruleaudit.io import load_json

    result = replay(load_json(FIXTURES / "m3-witness-v1.json"))
    assert result["status"] == "verified"
    assert result["delta"] == 1
    assert result["alternative_checked"] is True
