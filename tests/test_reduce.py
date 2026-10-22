import copy
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from types import FrameType
from typing import cast

import pytest

from ruleaudit.audit import CheckedCorpus, audit_case
from ruleaudit.config import parse_config
from ruleaudit.corpus import parse_corpus
from ruleaudit.io import InputError, JSONValue, content_hash, load_json, parse_expression
from ruleaudit.ir import Binary, Const, Var
from ruleaudit.records import verify_template
from ruleaudit.reduce import (
    ReductionConfig,
    check_candidate,
    reduce_witness,
    reduction_config_document,
    reduction_measure,
    shrinks,
)
from ruleaudit.replay import replay
from ruleaudit.rewrite import RunLimits
from ruleaudit.solver import Z3Backend

FIXTURES = Path(__file__).parent / "fixtures"
type Trace = Callable[[FrameType, str, object], Trace | None]


def origin() -> dict[str, JSONValue]:
    return cast(dict[str, JSONValue], load_json(FIXTURES / "m4-guided-witness-v1.json"))


def test_reduction_is_smaller_qualified_and_replayable() -> None:
    witness = origin()
    result = reduce_witness(witness, ReductionConfig())
    assert result["schema_version"] == 2
    payload = cast(dict[str, JSONValue], result["payload"])
    original_payload = cast(dict[str, JSONValue], witness["payload"])
    final = cast(dict[str, JSONValue], payload["final"])
    before = parse_expression({"schema_version": 1, "expression": original_payload["input"]})
    after = parse_expression({"schema_version": 1, "expression": final["input"]})
    assert reduction_measure(after) < reduction_measure(before)
    assert after == Binary("add", Binary("add", Const(0), Const(0)), Const(0))
    assert payload["status"] == "completed"
    assert payload["original"] == witness
    assert cast(int, cast(dict[str, JSONValue], final["paired"])["delta"]) > 0
    assert final["alternative"] is not None
    assert replay(result)["status"] == "verified"


def test_shrink_proposals_strictly_decrease_and_include_context_deletion() -> None:
    from ruleaudit.ir import Unary

    term = Unary("not", Binary("add", Var("x"), Const(7)))
    candidates = tuple(shrinks(term))
    assert any(candidate == term.operand for _, candidate in candidates)
    assert any(
        candidate == Unary("not", Binary("add", Var("x"), Const(1))) for _, candidate in candidates
    )
    assert len(candidates) == len({expr for _, expr in candidates})
    assert all(
        reduction_measure(candidate) < reduction_measure(term) for _, candidate in candidates
    )


def test_positive_regression_that_loses_target_path_is_rejected() -> None:
    value = cast(dict[str, JSONValue], origin()["payload"])
    corpus, config = parse_corpus(value["corpus"]), parse_config(value["config"])
    target = corpus.rules[0]
    alternative = cast(dict[str, JSONValue], value["alternative"])
    backend = Z3Backend()
    template = verify_template(alternative["template"], target, corpus, RunLimits(), backend)
    one = Binary("add", Var("x"), Const(0))
    assert audit_case(one, target.id, CheckedCorpus(corpus), config.schedule, config.run).delta > 0
    assert check_candidate(one, target, CheckedCorpus(corpus), config, template, backend) is None


def test_shrink_with_valid_path_but_no_regression_is_rejected() -> None:
    from ruleaudit.audit import check_corpus
    from ruleaudit.rewrite import Schedule
    from ruleaudit.rules import PBinary, Rule

    value = cast(dict[str, JSONValue], origin()["payload"])
    corpus, config = parse_corpus(value["corpus"]), parse_config(value["config"])
    zero = Const(0)
    fold = Rule("fold", PBinary("add", zero, zero), zero)
    corpus = replace(corpus, rules=(*corpus.rules[:2], fold, *corpus.rules[2:]))
    config = replace(config, schedule=Schedule("preorder", ("A", "B", "fold", "D", "C")))
    checked = check_corpus(corpus).checked
    assert checked is not None
    alternative = cast(dict[str, JSONValue], value["alternative"])
    template = verify_template(
        alternative["template"], corpus.rules[0], corpus, RunLimits(), Z3Backend()
    )
    candidate = Binary("add", Binary("add", zero, zero), zero)
    pair = audit_case(candidate, "A", checked, config.schedule, config.run)
    assert pair.comparable and pair.delta == 0
    assert (
        check_candidate(candidate, corpus.rules[0], checked, config, template, Z3Backend()) is None
    )


def test_solver_exhaustion_is_partial_and_never_accepts_unchecked_shrink() -> None:
    from ruleaudit.solver import SolverLimits

    result = reduce_witness(origin(), ReductionConfig(solver=SolverLimits(max_calls=0)))
    payload = cast(dict[str, JSONValue], result["payload"])
    assert payload["status"] == "partial" and payload["steps"] == []
    assert payload["solver_calls"] == 0
    assert replay(result)["status"] == "verified"


@pytest.mark.parametrize(
    "settings",
    [ReductionConfig(seconds=0), ReductionConfig(max_attempts=0), ReductionConfig(max_accepted=0)],
)
def test_exhaustion_returns_original_verified_input(settings: ReductionConfig) -> None:
    result = reduce_witness(origin(), settings)
    payload = cast(dict[str, JSONValue], result["payload"])
    assert payload["status"] == "partial"
    assert payload["steps"] == []
    assert replay(result)["status"] == "verified"


def test_interrupt_after_acceptance_keeps_last_verified_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import ruleaudit.reduce as reducer

    accepted = False
    actual = reducer.check_candidate

    def interrupted(*args: object, **kwargs: object) -> dict[str, JSONValue] | None:
        nonlocal accepted
        if accepted:
            raise KeyboardInterrupt
        result = actual(*args, **kwargs)  # type: ignore[arg-type]
        accepted = result is not None
        return result

    monkeypatch.setattr(reducer, "check_candidate", interrupted)
    result = reduce_witness(origin(), ReductionConfig())
    payload = cast(dict[str, JSONValue], result["payload"])
    assert payload["status"] == "interrupted"
    assert len(cast(list[JSONValue], payload["steps"])) == 1
    monkeypatch.setattr(reducer, "check_candidate", actual)
    assert replay(result)["status"] == "verified"


def test_interrupt_at_acceptance_commit_keeps_consistent_evidence() -> None:
    import sys

    def interrupt(frame: FrameType, event: str, arg: object) -> Trace | None:
        if event == "line" and frame.f_code is reduce_witness.__code__:
            local = frame.f_locals
            committed = local.get("steps") or (local.get("state", (None, None, ()))[2])
            if committed:
                sys.settrace(None)
                raise KeyboardInterrupt
        return interrupt

    previous = sys.gettrace()
    try:
        sys.settrace(interrupt)
        result = reduce_witness(origin(), ReductionConfig())
    finally:
        sys.settrace(previous)
    payload = cast(dict[str, JSONValue], result["payload"])
    assert payload["status"] == "interrupted"
    assert len(cast(list[JSONValue], payload["steps"])) == 1
    assert replay(result)["status"] == "verified"


@pytest.mark.parametrize(
    "mutation", ["input", "measure", "hash", "step", "cost", "final", "version"]
)
def test_rehashed_reduction_tampering_fails(mutation: str) -> None:
    result = reduce_witness(origin(), ReductionConfig())
    bad = copy.deepcopy(result)
    payload = cast(dict[str, JSONValue], bad["payload"])
    steps = cast(list[dict[str, JSONValue]], payload["steps"])
    step = steps[0]
    if mutation == "version":
        bad["schema_version"] = 999
    elif mutation == "input":
        cast(dict[str, JSONValue], step["record"])["input"] = {"op": "const", "value": 0}
    elif mutation == "measure":
        step["measure_after"] = [0, 0, 0]
    elif mutation == "hash":
        step["before_hash"] = "wrong"
    elif mutation == "step":
        cast(dict[str, JSONValue], step["shrink"])["location"] = [True]
    elif mutation == "cost":
        record = cast(dict[str, JSONValue], step["record"])
        cast(dict[str, JSONValue], record["paired"])["delta"] = 999
    else:
        payload["final"] = {}
    bad["sha256"] = content_hash(payload)
    with pytest.raises(InputError):
        replay(bad)


def test_no_alternative_or_nested_reduction_is_rejected() -> None:
    witness = origin()
    payload = cast(dict[str, JSONValue], witness["payload"])
    payload["alternative"] = None
    witness["sha256"] = content_hash(payload)
    with pytest.raises(InputError, match="alternative"):
        reduce_witness(witness, ReductionConfig())
    reduced = reduce_witness(origin(), ReductionConfig(max_attempts=0))
    with pytest.raises(InputError, match="original"):
        reduce_witness(reduced, ReductionConfig())


def test_strict_reduction_config_roundtrip_and_limits() -> None:
    from ruleaudit.reduce import parse_reduction_config

    settings = ReductionConfig(max_attempts=7)
    assert parse_reduction_config(reduction_config_document(settings)) == settings
    invalid = reduction_config_document(settings)
    invalid["schema_version"] = 99
    with pytest.raises(InputError, match="version"):
        parse_reduction_config(invalid)
    invalid = reduction_config_document(settings)
    invalid["extra"] = 0
    with pytest.raises(InputError, match="unknown"):
        parse_reduction_config(invalid)
    with pytest.raises(ValueError):
        ReductionConfig(max_attempts=True)


def test_saved_m5_reduced_witness_replays_without_regeneration() -> None:
    result = replay(load_json(FIXTURES / "m5-reduced-witness-v2.json"))
    assert result["status"] == "verified"
    assert result["reduced_nodes"] == 5 and result["delta"] == 2


def test_interrupt_at_final_clock_still_returns_verified_input() -> None:
    calls = 0
    interrupt_at: int | None = None

    def now() -> float:
        nonlocal calls
        calls += 1
        if calls == interrupt_at:
            raise KeyboardInterrupt
        return 1.0

    settings = ReductionConfig(max_attempts=0)
    reduce_witness(origin(), settings, now=now)
    interrupt_at, calls = calls, 0
    try:
        result = reduce_witness(origin(), settings, now=now)
    except KeyboardInterrupt:
        pytest.fail("final clock interrupt escaped without the last verified input")
    assert cast(dict[str, JSONValue], result["payload"])["status"] == "interrupted"
    assert replay(result)["status"] == "verified"
