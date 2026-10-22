import copy
import inspect
from dataclasses import replace
from pathlib import Path
from typing import Literal, cast

import pytest

from ruleaudit.audit import audit_case, check_corpus
from ruleaudit.config import Config, Generation, config_document, parse_config
from ruleaudit.corpus import load_corpus
from ruleaudit.derive import derive
from ruleaudit.generate import generate_target, guided_attempt, random_attempt, target_attempt
from ruleaudit.io import InputError, JSONValue, content_hash
from ruleaudit.ir import Binary, Const, Unary, measure
from ruleaudit.records import EncodingBudget, case_document, make_witness
from ruleaudit.replay import replay
from ruleaudit.rewrite import RunLimits, Schedule

FIXTURES = Path(__file__).parent / "fixtures"


def test_baseline_interfaces_do_not_receive_guidance(monkeypatch: pytest.MonkeyPatch) -> None:
    import ruleaudit.generate as generation

    assert tuple(inspect.signature(random_attempt).parameters) == ("settings", "attempt")
    assert tuple(inspect.signature(target_attempt).parameters) == ("target", "settings", "attempt")

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("baseline called guided generation")

    monkeypatch.setattr(generation, "guided_attempt", forbidden)
    target = load_corpus(FIXTURES / "budget.json").rules[0]
    assert generate_target(target, Generation(cases=2, depth=0)).completed
    case = random_attempt(Generation(strategy="random", depth=0), 1)
    assert case is not None and case.guidance is None


@pytest.mark.parametrize("context", ["hole", "not", "xor-left", "sub-right"])
def test_contexts_are_seeded_and_preserve_target_occurrence(context: str) -> None:
    corpus = load_corpus(FIXTURES / "budget.json")
    settings = Generation(depth=0, contexts=(context,), max_nodes=50, max_depth=8)
    case = target_attempt(corpus.rules[0], settings, 1)
    assert case is not None and case == target_attempt(corpus.rules[0], settings, 1)
    assert case.context.kind == context
    core = Binary("add", Binary("add", dict(case.bindings)["X"], Const(0)), Const(0))
    if context == "hole":
        assert case.expression == core
    elif context == "not":
        assert case.expression == Unary("not", core)
    elif context.endswith("left"):
        assert case.context.sibling is not None
        assert case.expression == Binary("xor", core, case.context.sibling)
    else:
        assert case.context.sibling is not None
        assert case.expression == Binary("sub", case.context.sibling, core)


def test_shared_complete_input_bounds_and_random_repeatability() -> None:
    corpus = load_corpus(FIXTURES / "budget.json")
    target = corpus.rules[0]
    settings = Generation(strategy="random", depth=4, max_nodes=7, max_depth=3)
    first = [random_attempt(settings, i) for i in range(1, 50)]
    assert first == [random_attempt(settings, i) for i in range(1, 50)]
    assert any(case is None for case in first)
    assert any(case is not None for case in first)
    for case in first:
        if case is not None:
            assert measure(case.expression).nodes <= 7
            assert measure(case.expression).depth <= 3
            assert case.bindings == () and case.guidance is None
    tight = Generation(max_nodes=1, max_depth=1)
    assert target_attempt(target, tight, 1) is None
    result = generate_target(target, replace(tight, attempts=3))
    assert result.rejections == 3 and not result.completed


def test_guided_records_actual_competition_and_checked_prefix() -> None:
    corpus = load_corpus(FIXTURES / "interference.json")
    target = corpus.rules[0]
    templates = derive(target, corpus.rules).witnesses
    settings = Generation(strategy="guided", depth=0)
    schedule = Schedule("preorder", ("A", "B", "D", "C"))
    case = guided_attempt(target, settings, 1, templates, corpus.rules, schedule, RunLimits())
    assert case is not None and case.guidance is not None
    evidence = case.guidance
    # At intermediate add(x,0), D wins before C; B needs two adds and cannot match.
    assert evidence.competing.rule_id == "D"
    assert evidence.expected_rule == "C" and evidence.expected_location == ()
    assert evidence.intermediate == Binary("add", dict(case.bindings)["X"], Const(0))
    assert [step.rule_id for step in evidence.prefix] == ["B"]
    assert evidence.competing.before == evidence.intermediate
    assert case == guided_attempt(
        target, settings, 1, templates, corpus.rules, schedule, RunLimits()
    )
    no_competitor = Schedule("preorder", ("A", "B", "C", "D"))
    assert (
        guided_attempt(target, settings, 1, templates, corpus.rules, no_competitor, RunLimits())
        is None
    )
    assert guided_attempt(target, settings, 1, (), corpus.rules, schedule, RunLimits()) is None


def test_guided_competing_ancestor_in_context_is_observed() -> None:
    from ruleaudit.rules import Meta, PUnary, Rule

    corpus = load_corpus(FIXTURES / "budget.json")
    ancestor = Rule("ancestor", PUnary("not", Meta("Y", "expr")), PUnary("not", Meta("Y", "expr")))
    rules = (*corpus.rules, ancestor)
    target = rules[0]
    settings = Generation(strategy="guided", depth=0, contexts=("not",))
    schedule = Schedule("preorder", ("A", "B", "C", "ancestor"))
    case = guided_attempt(
        target, settings, 1, derive(target, rules).witnesses, rules, schedule, RunLimits()
    )
    assert case is not None and case.guidance is not None
    assert case.guidance.expected_location == (0,)
    assert case.guidance.competing.location == ()
    assert case.guidance.competing.rule_id == "ancestor"
    assert case.guidance.target_location == (0,)


@pytest.mark.parametrize("strategy", ["random", "target", "guided"])
def test_context_witnesses_replay_and_guidance_tampering_fails(
    strategy: Literal["random", "target", "guided"],
) -> None:
    corpus = load_corpus(FIXTURES / "interference.json")
    target = corpus.rules[0]
    settings = Generation(
        strategy=strategy, depth=3 if strategy == "random" else 0, contexts=("not",)
    )
    schedule = Schedule("preorder", ("A", "B", "D", "C"))
    config = Config(schedule, run=RunLimits(h=4), generation=settings)
    checked = check_corpus(corpus).checked
    assert checked is not None
    templates = derive(target, corpus.rules).witnesses
    witness = None
    for attempt in range(1, 1001):
        if strategy == "random":
            case = random_attempt(settings, attempt)
        elif strategy == "target":
            case = target_attempt(target, settings, attempt)
        else:
            case = guided_attempt(
                target, settings, attempt, templates, corpus.rules, schedule, config.run
            )
        if case is None:
            continue
        pair = audit_case(case.expression, target.id, checked, schedule, config.run)
        if pair.comparable and pair.delta > 0:
            witness = make_witness(corpus, config, case, pair, templates)
            break
    if strategy == "random" and witness is None:
        # Random mode may find nothing; its provenance still independently regenerates.
        candidate = random_attempt(settings, 1)
        assert candidate is not None
        assert case_document(candidate, EncodingBudget())["guidance"] is None
        return
    assert witness is not None
    assert replay(witness)["status"] == "verified"
    if strategy == "guided":
        bad = copy.deepcopy(witness)
        payload = cast(dict[str, JSONValue], bad["payload"])
        provenance = cast(dict[str, JSONValue], payload["provenance"])
        guidance = cast(dict[str, JSONValue], provenance["guidance"])
        cast(dict[str, JSONValue], guidance["competing"])["rule_id"] = "C"
        bad["sha256"] = content_hash(payload)
        with pytest.raises(InputError, match="provenance"):
            replay(bad)


def test_config_v2_roundtrip_and_v1_compatibility() -> None:
    config = Config(
        Schedule("preorder", ("A",)), generation=Generation(strategy="random", max_depth=4)
    )
    document = config_document(config)
    assert document["schema_version"] == 2
    assert parse_config(document) == config
    from ruleaudit.io import load_json

    envelope = cast(dict[str, JSONValue], load_json(FIXTURES / "m3-witness-v1.json"))
    legacy = cast(dict[str, JSONValue], envelope["payload"])["config"]
    assert parse_config(legacy).generation.max_depth == 64


@pytest.mark.parametrize(
    "settings",
    [
        {"contexts": ()},
        {"contexts": ("hole", "hole")},
        {"contexts": ("exec",)},
        {"max_nodes": True},
        {"max_depth": 65},
        {"strategy": "fallback"},
    ],
)
def test_new_generation_limits_are_strict(settings: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        Generation(**settings)  # type: ignore[arg-type]


def test_guidance_work_budget_and_deadline_stop_before_more_matches() -> None:
    from ruleaudit.generate import GuidanceBudget
    from ruleaudit.report import IncompleteError

    corpus = load_corpus(FIXTURES / "interference.json")
    target = corpus.rules[0]
    templates = derive(target, corpus.rules).witnesses
    args = (
        target,
        Generation(strategy="guided", depth=0),
        1,
        templates,
        corpus.rules,
        Schedule("preorder", ("A", "B", "D", "C")),
        RunLimits(),
    )
    budget = GuidanceBudget(1)
    with pytest.raises(IncompleteError, match="generation-match-limit"):
        guided_attempt(*args, budget=budget)
    assert budget.matches == 1
    deadline = GuidanceBudget(100, allow_work=lambda: False)
    with pytest.raises(IncompleteError, match="overall-time-limit"):
        guided_attempt(*args, budget=deadline)
    assert deadline.matches == 0


def test_guard_unsatisfied_guided_attempts_never_fall_back() -> None:
    from ruleaudit.rules import Guard, Meta, PBinary, Rule

    x, c = Meta("X", "expr"), Meta("C", "const")
    target = Rule("A", PBinary("add", x, c), x, (Guard("eq", "C", Const(7)),))
    assert (
        guided_attempt(
            target,
            Generation(strategy="guided", constants=(0,)),
            1,
            (),
            (target,),
            Schedule("preorder", ("A",)),
            RunLimits(),
        )
        is None
    )


def test_postorder_first_match_in_disjoint_sibling_is_not_overlap() -> None:
    from ruleaudit.rules import Rule

    corpus = load_corpus(FIXTURES / "budget.json")
    leaf = Rule("leaf", Const(0), Const(0))
    rules = (*corpus.rules, leaf)
    target = rules[0]
    settings = Generation(strategy="guided", depth=0, constants=(0,), contexts=("add-right",))
    templates = derive(target, rules).witnesses
    schedule = Schedule("postorder", ("A", "B", "C", "leaf"))
    examined = 0
    for attempt in range(1, 21):
        baseline = target_attempt(target, settings, attempt)
        assert baseline is not None
        if baseline.context.sibling == Const(0):
            examined += 1
            assert (
                guided_attempt(target, settings, attempt, templates, rules, schedule, RunLimits())
                is None
            )
    assert examined > 0


def test_all_three_audit_modes_use_caps_and_report_explicit_no_overlap(tmp_path: Path) -> None:
    from ruleaudit.experiment import audit_experiment
    from ruleaudit.io import load_json
    from ruleaudit.report import ReportWriter

    corpus = load_corpus(FIXTURES / "budget.json")
    config = Config(
        Schedule("preorder", ("A", "B", "C")), generation=Generation(cases=2, attempts=10, depth=0)
    )
    for strategy in ("random", "target", "guided"):
        settings = replace(
            config,
            generation=replace(config.generation, strategy=strategy),
        )
        out = tmp_path / strategy
        code = audit_experiment(
            corpus, settings, corpus.rules[0], ReportWriter(out, settings.max_output_bytes)
        )
        result = cast(dict[str, JSONValue], load_json(out / "audit.json"))
        assert cast(int, result["cases_tested"]) <= 2
        assert cast(int, cast(dict[str, JSONValue], result["generation"])["attempts"]) <= 10
        if strategy == "guided":
            assert code == 3 and result["cases_tested"] == 0
            assert "no-overlap-candidate-within-bounds" in cast(list[JSONValue], result["reasons"])
        else:
            assert code == 0 and result["cases_tested"] == 2
            assert cast(dict[str, JSONValue], result["generation"])["match_attempts"] == 0


def test_saved_m4_guided_witness_replays() -> None:
    from ruleaudit.io import load_json

    result = replay(load_json(FIXTURES / "m4-guided-witness-v1.json"))
    assert result["status"] == "verified"
    assert result["alternative_checked"] is True
