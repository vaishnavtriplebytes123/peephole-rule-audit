from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

from ruleaudit.config import Config, Generation
from ruleaudit.corpus import load_corpus
from ruleaudit.evaluate import evaluate
from ruleaudit.evaluation_config import (
    EvaluationConfig,
    evaluation_document,
    parse_evaluation_config,
    trials,
)
from ruleaudit.io import InputError, JSONValue, load_json
from ruleaudit.report import ReportWriter
from ruleaudit.rewrite import RunLimits, Schedule

FIXTURES = Path(__file__).parent / "fixtures"


def settings() -> EvaluationConfig:
    return EvaluationConfig(
        base=Config(
            Schedule("preorder", ("A", "B", "D", "C")),
            run=RunLimits(h=4),
            generation=Generation(cases=1, depth=0),
        ),
        targets=("A",),
        seeds=(0,),
        h_values=(4,),
        traversals=("preorder",),
        priorities=("corpus",),
        reduce_per_trial=1,
    )


def test_strict_matrix_roundtrip_and_grid_shares_caps_and_schedule() -> None:
    config = replace(
        settings(),
        seeds=(0, 1),
        h_values=(1, 4),
        traversals=("preorder", "postorder"),
        priorities=("corpus", "permuted"),
    )
    assert parse_evaluation_config(evaluation_document(config)) == config
    corpus = load_corpus(FIXTURES / "interference.json")
    grid = tuple(trials(corpus, config))
    assert grid == tuple(trials(corpus, config))
    assert len(grid) == 2 * 2 * 2 * 2 * 3
    assert {trial.config.generation.strategy for trial in grid} == {"random", "target", "guided"}
    for trial in grid:
        assert trial.config.generation.constants == config.base.generation.constants
        assert trial.config.generation.attempts == config.base.generation.attempts
        assert trial.config.generation.max_depth == config.base.generation.max_depth
        assert set(trial.config.schedule.priority) == {"A", "B", "D", "C"}
    bad = evaluation_document(config)
    bad["extra"] = 1
    with pytest.raises(InputError, match="unknown"):
        parse_evaluation_config(bad)
    with pytest.raises(ValueError):
        replace(config, seeds=(True,))
    with pytest.raises(ValueError):
        replace(config, h_values=(4, 4))


def test_evaluation_retains_zeroes_qualified_rates_and_replays_every_witness(
    tmp_path: Path,
) -> None:
    corpus = load_corpus(FIXTURES / "interference.json")
    config = settings()
    out = tmp_path / "matrix"
    code = evaluate(corpus, config, ReportWriter(out, config.max_output_bytes))
    assert code == 0
    result = cast(dict[str, JSONValue], load_json(out / "evaluation.json"))
    rows = cast(list[dict[str, JSONValue]], result["trials"])
    assert len(rows) == 3 and result["not_run"] == 0
    by_mode = {cast(str, row["strategy"]): row for row in rows}
    assert all(
        cast(float, row["wall_seconds"]) >= cast(float, row["total_seconds"]) for row in rows
    )
    assert by_mode["random"]["findings"] == 0
    assert by_mode["random"]["primary_rate"] is None
    assert by_mode["random"]["time_to_first_finding"] is None
    for mode in ("target", "guided"):
        row = by_mode[mode]
        assert row["findings"] == row["eligible_cases"] == 1
        assert row["primary_rate"] == 1.0
        assert row["original_witnesses"] == row["original_replayed"] == 1
        assert row["reduced_witnesses"] == row["reduced_replayed"] == 1
    assert (out / "trials.csv").exists()
    assert all((out / cast(str, row["directory"]) / "audit.json").exists() for row in rows)


def test_max_trials_and_inconclusive_reports_are_not_zero_findings(tmp_path: Path) -> None:
    from ruleaudit.solver import SolverLimits

    corpus = load_corpus(FIXTURES / "interference.json")
    limited = replace(settings(), max_trials=0)
    out = tmp_path / "not-run"
    assert evaluate(corpus, limited, ReportWriter(out, limited.max_output_bytes)) == 3
    doc = cast(dict[str, JSONValue], load_json(out / "evaluation.json"))
    assert doc["trials"] == [] and doc["not_run"] == 3
    unknown = replace(
        settings(),
        base=replace(settings().base, solver=SolverLimits(max_calls=0)),
        reduce_per_trial=0,
    )
    out = tmp_path / "unknown"
    assert evaluate(corpus, unknown, ReportWriter(out, unknown.max_output_bytes)) == 3
    doc = cast(dict[str, JSONValue], load_json(out / "evaluation.json"))
    for row in cast(list[dict[str, JSONValue]], doc["trials"]):
        assert row["status"] == "partial"
        assert row["cases_tested"] is None and row["findings"] is None
        assert row["primary_rate"] is None


def test_unknown_target_and_wrong_base_priority_fail_before_trials(tmp_path: Path) -> None:
    corpus = load_corpus(FIXTURES / "interference.json")
    with pytest.raises(InputError, match="target"):
        tuple(trials(corpus, replace(settings(), targets=("missing",))))
    with pytest.raises(InputError, match="priority"):
        tuple(
            trials(
                corpus,
                replace(
                    settings(),
                    base=replace(
                        settings().base, schedule=Schedule("preorder", ("C", "D", "B", "A"))
                    ),
                ),
            )
        )
