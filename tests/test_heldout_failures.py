from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

import ruleaudit.evaluate as runner
from ruleaudit.config import Config, Generation
from ruleaudit.corpus import load_corpus
from ruleaudit.evaluation_config import EvaluationConfig
from ruleaudit.heldout import input_snapshot
from ruleaudit.io import JSONValue, load_json
from ruleaudit.report import ReportWriter
from ruleaudit.rewrite import Schedule

FIXTURES = Path(__file__).parent / "fixtures"


def settings() -> EvaluationConfig:
    return EvaluationConfig(
        kind="heldout-evaluation",
        base=Config(
            Schedule("preorder", ("A", "B", "D", "C")),
            generation=Generation(strategy="random", cases=8),
        ),
        targets=("A",),
        seeds=(100003,),
        h_values=(4,),
        traversals=("preorder",),
        priorities=("corpus",),
        reduce_per_trial=0,
    )


def test_input_mismatch_fails_parent_and_child_metrics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def wrong(
        generation: Generation, deadline: float, *, now: Callable[[], float]
    ) -> dict[str, JSONValue]:
        result = input_snapshot(generation, deadline, now=now)
        cast(list[dict[str, JSONValue]], result["cases"])[0]["input_hash"] = "wrong"
        return result

    monkeypatch.setattr(runner, "input_snapshot", wrong)
    config = settings()
    out = tmp_path / "wrong-inputs"
    assert (
        runner.evaluate(
            load_corpus(FIXTURES / "interference.json"),
            config,
            ReportWriter(out, config.max_output_bytes),
        )
        == 4
    )
    root = cast(dict[str, JSONValue], load_json(out / "evaluation.json"))
    row = cast(list[dict[str, JSONValue]], root["trials"])[0]
    child = cast(
        dict[str, JSONValue], load_json(out / cast(str, row["directory"]) / "metrics.json")
    )
    assert row["heldout_sequence"] == child["heldout_sequence"] == "mismatch"
    assert row["status"] == child["status"] == "failed"


def test_input_clock_interruption_retains_concrete_prefix() -> None:
    calls = 0

    def now() -> float:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise KeyboardInterrupt
        return 0.0

    result = input_snapshot(settings().base.generation, 100.0, now=now)
    assert result["status"] == "interrupted"
    assert len(cast(list[JSONValue], result["cases"])) == 1


def test_zero_time_and_input_output_cap_are_explicit(tmp_path: Path) -> None:
    corpus = load_corpus(FIXTURES / "interference.json")
    zero = replace(settings(), seconds=0)
    out = tmp_path / "zero-time"
    assert runner.evaluate(corpus, zero, ReportWriter(out, zero.max_output_bytes)) == 3
    saved = cast(dict[str, JSONValue], load_json(out / "heldout-inputs-000001.json"))
    assert saved["cases"] == [] and saved["status"] == "partial"
    small = replace(
        settings(),
        max_output_bytes=32768,
        base=replace(settings().base, generation=Generation(strategy="random", cases=200, depth=4)),
    )
    out = tmp_path / "input-cap"
    assert runner.evaluate(corpus, small, ReportWriter(out, small.max_output_bytes)) == 3
    result = cast(dict[str, JSONValue], load_json(out / "evaluation.json"))
    assert result["not_run"] == 1 and result["trials"] == []
    assert result["reason"] == "overall-output-limit preparing held-out inputs"


def test_interruption_wins_when_input_snapshot_exceeds_output_cap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def interrupted(
        generation: Generation, deadline: float, *, now: Callable[[], float]
    ) -> dict[str, JSONValue]:
        result = input_snapshot(generation, deadline, now=now)
        result["status"], result["reason"] = "interrupted", "injected late interruption"
        return result

    monkeypatch.setattr(runner, "input_snapshot", interrupted)
    config = replace(
        settings(),
        max_output_bytes=32768,
        base=replace(settings().base, generation=Generation(strategy="random", cases=200, depth=4)),
    )
    out = tmp_path / "interrupted-cap"
    assert (
        runner.evaluate(
            load_corpus(FIXTURES / "interference.json"),
            config,
            ReportWriter(out, config.max_output_bytes),
        )
        == 130
    )
    doc = cast(dict[str, JSONValue], load_json(out / "evaluation.json"))
    assert doc["status"] == "interrupted" and doc["not_run"] == 1
