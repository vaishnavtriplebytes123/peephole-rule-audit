from dataclasses import replace

import pytest

from ruleaudit.config import Config, Generation, config_document, parse_config
from ruleaudit.generate import generate_target, target_attempt
from ruleaudit.io import InputError
from ruleaudit.ir import Const
from ruleaudit.rewrite import Schedule
from ruleaudit.rules import Guard, Meta, PBinary, Rule


def test_config_roundtrip_and_strict_fields() -> None:
    config = Config(Schedule("preorder", ("A",)))
    assert parse_config(config_document(config)) == config
    bad = config_document(config)
    bad["extra"] = 0
    with pytest.raises(InputError, match="unknown"):
        parse_config(bad)
    bad = config_document(config)
    bad["schema_version"] = True
    with pytest.raises(InputError, match="version"):
        parse_config(bad)


@pytest.mark.parametrize(
    "settings",
    [
        {"seed": True},
        {"seed": -1},
        {"depth": 5},
        {"attempts": -1},
        {"constants": (0, 0)},
        {"constants": (True,)},
        {"cases": 0},
    ],
)
def test_generation_limits(settings: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        Generation(**settings)  # type: ignore[arg-type]


def test_seeded_generation_attempts_and_duplicate_exhaustion() -> None:
    x = Meta("X", "expr")
    rule = Rule("A", PBinary("add", x, Const(0)), x)
    settings = Generation(seed=19, cases=4, attempts=100, depth=0)
    first = generate_target(rule, settings)
    assert first == generate_target(rule, settings)
    assert first.completed
    assert len(first.cases) == len({case.expression for case in first.cases}) == 4
    for case in first.cases:
        assert target_attempt(rule, settings, case.attempt) == case
    exhausted = generate_target(rule, replace(settings, cases=100, attempts=20))
    assert not exhausted.completed
    assert exhausted.attempts == 20
    assert exhausted.duplicates > 0


def test_guard_exhaustion_is_zero_coverage_partial() -> None:
    x, c = Meta("X", "expr"), Meta("C", "const")
    target = Rule("A", PBinary("add", x, c), x, (Guard("eq", "C", Const(7)),))
    result = generate_target(target, Generation(cases=1, attempts=5, constants=(0,)))
    assert not result.completed
    assert not result.cases
    assert result.rejections == result.attempts == 5


def test_experiment_snapshots_record_tool_and_runtime_versions() -> None:
    from pathlib import Path

    from ruleaudit.corpus import load_corpus
    from ruleaudit.experiment import snapshots

    corpus = load_corpus(Path(__file__).parent / "fixtures/budget.json")
    result = snapshots(corpus, Config(Schedule("preorder", ("A", "B", "C"))), corpus.rules[0])
    assert result["tool_version"] == "0.1.0"
    assert isinstance(result["environment"], dict)
    assert set(result["environment"]) == {"python", "z3-solver"}
