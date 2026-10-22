from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from time import perf_counter
from typing import cast

import pytest

import ruleaudit.evaluate as runner
from ruleaudit.config import Config, Generation
from ruleaudit.corpus import load_corpus
from ruleaudit.evaluation_config import EvaluationConfig
from ruleaudit.io import InputError, JSONValue, content_hash, load_json
from ruleaudit.reduce import ReductionConfig, reduce_witness
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
    )


def test_invalid_replay_is_a_failed_trial_not_a_zero_finding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def invalid(*args: object, **kwargs: object) -> None:
        raise InputError("paired", "injected invalid replay")

    monkeypatch.setattr(runner, "replay", invalid)
    corpus = load_corpus(FIXTURES / "interference.json")
    config = settings()
    out = tmp_path / "invalid-replay"
    assert runner.evaluate(corpus, config, ReportWriter(out, config.max_output_bytes)) == 4
    doc = cast(dict[str, JSONValue], load_json(out / "evaluation.json"))
    rows = cast(list[dict[str, JSONValue]], doc["trials"])
    assert any(row["status"] == "failed" and row["replay_invalid"] == 1 for row in rows)


def test_interrupted_reducer_stops_matrix_and_retains_witness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def interrupted(
        value: JSONValue, config: ReductionConfig, *, now: Callable[[], float] = perf_counter
    ) -> dict[str, JSONValue]:
        result = reduce_witness(value, config, now=now)
        payload = cast(dict[str, JSONValue], result["payload"])
        payload["status"], payload["reason"] = "interrupted", "injected interruption"
        result["sha256"] = content_hash(payload)
        return result

    monkeypatch.setattr(runner, "reduce_witness", interrupted)
    corpus = load_corpus(FIXTURES / "interference.json")
    config = settings()
    out = tmp_path / "interrupted"
    assert runner.evaluate(corpus, config, ReportWriter(out, config.max_output_bytes)) == 130
    doc = cast(dict[str, JSONValue], load_json(out / "evaluation.json"))
    assert cast(int, doc["not_run"]) >= 1
    rows = cast(list[dict[str, JSONValue]], doc["trials"])
    row = next(row for row in rows if row["status"] == "interrupted")
    assert row["reduced_witnesses"] == 1 and row["reduced_replayed"] == 0
    assert (out / cast(str, row["directory"]) / "reduced-000001.json").exists()


def test_zero_time_and_shared_disk_cap_keep_explicit_partial_results(tmp_path: Path) -> None:
    corpus = load_corpus(FIXTURES / "interference.json")
    zero = replace(settings(), seconds=0)
    out = tmp_path / "zero-time"
    assert runner.evaluate(corpus, zero, ReportWriter(out, zero.max_output_bytes)) == 3
    doc = cast(dict[str, JSONValue], load_json(out / "evaluation.json"))
    assert doc["trials"] == [] and doc["not_run"] == 3
    small = replace(
        settings(),
        max_output_bytes=32768,
        reduce_per_trial=0,
        base=replace(settings().base, generation=Generation(cases=4, depth=0)),
    )
    out = tmp_path / "disk-cap"
    assert runner.evaluate(corpus, small, ReportWriter(out, small.max_output_bytes)) == 3
    assert (
        sum(path.stat().st_size for path in out.rglob("*") if path.is_file())
        <= small.max_output_bytes
    )
    doc = cast(dict[str, JSONValue], load_json(out / "evaluation.json"))
    assert doc["status"] == "partial"


def test_evaluate_makes_no_network_connections(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import socket

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("network connection during evaluation")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    corpus = load_corpus(FIXTURES / "interference.json")
    config = settings()
    assert (
        runner.evaluate(corpus, config, ReportWriter(tmp_path / "offline", config.max_output_bytes))
        == 0
    )
