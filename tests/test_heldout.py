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
from ruleaudit.generate import random_attempt
from ruleaudit.io import JSONValue, content_hash, expression_node, load_json
from ruleaudit.report import ReportWriter
from ruleaudit.rewrite import RunLimits, Schedule

FIXTURES = Path(__file__).parent / "fixtures"


def settings() -> EvaluationConfig:
    return EvaluationConfig(
        kind="heldout-evaluation",
        base=Config(
            Schedule("preorder", ("A", "B", "D", "C")),
            run=RunLimits(h=4),
            generation=Generation(strategy="random", cases=8, depth=2, contexts=("hole",)),
        ),
        targets=("A", "B"),
        seeds=(100003, 100019),
        h_values=(4,),
        traversals=("preorder",),
        priorities=("corpus",),
        reduce_per_trial=0,
    )


def test_heldout_is_explicit_random_only_and_roundtrips() -> None:
    config = settings()
    assert parse_evaluation_config(evaluation_document(config)) == config
    grid = tuple(trials(load_corpus(FIXTURES / "interference.json"), config))
    assert len(grid) == config.expected_trials == 4
    assert {t.config.generation.strategy for t in grid} == {"random"}
    with pytest.raises(ValueError, match="hole"):
        replace(
            config,
            base=replace(
                config.base, generation=replace(config.base.generation, contexts=("not",))
            ),
        )
    with pytest.raises(ValueError, match="random"):
        replace(
            config,
            base=replace(
                config.base, generation=replace(config.base.generation, strategy="target")
            ),
        )


def test_saved_heldout_inputs_are_independent_and_shared_for_every_target(tmp_path: Path) -> None:
    config = settings()
    out = tmp_path / "heldout"
    assert (
        evaluate(
            load_corpus(FIXTURES / "interference.json"),
            config,
            ReportWriter(out, config.max_output_bytes),
        )
        == 0
    )
    result = cast(dict[str, JSONValue], load_json(out / "evaluation.json"))
    inputs = cast(list[dict[str, JSONValue]], result["heldout_inputs"])
    assert len(inputs) == 2
    by_seed: dict[int, list[str]] = {}
    for item in inputs:
        doc = cast(dict[str, JSONValue], load_json(out / cast(str, item["file"])))
        saved = cast(list[dict[str, JSONValue]], doc["cases"])
        assert len(saved) == doc["requested_cases"] == 8
        assert doc["status"] == "completed"
        seed = cast(int, doc["seed"])
        gen = replace(config.base.generation, seed=seed)
        hashes = []
        for case in saved:
            generated = random_attempt(gen, cast(int, case["attempt"]))
            assert generated is not None
            assert expression_node(generated.expression) == case["input"]
            assert content_hash(case["input"]) == case["input_hash"]
            hashes.append(case["input_hash"])
        assert len(set(hashes)) == 8
        by_seed[seed] = hashes
    for row in cast(list[dict[str, JSONValue]], result["trials"]):
        assert row["heldout_sequence"] == "complete"
        audit = cast(
            dict[str, JSONValue], load_json(out / cast(str, row["directory"]) / "audit.json")
        )
        assert [
            r["input_hash"] for r in cast(list[dict[str, JSONValue]], audit["records"])
        ] == by_seed[cast(int, row["seed"])]


def test_incomplete_heldout_generation_is_saved_without_running_trials(tmp_path: Path) -> None:
    config = settings()
    config = replace(
        config, base=replace(config.base, generation=replace(config.base.generation, attempts=1))
    )
    out = tmp_path / "short-inputs"
    assert (
        evaluate(
            load_corpus(FIXTURES / "interference.json"),
            config,
            ReportWriter(out, config.max_output_bytes),
        )
        == 3
    )
    doc = cast(dict[str, JSONValue], load_json(out / "evaluation.json"))
    assert doc["not_run"] == 4 and doc["trials"] == []
    saved = cast(dict[str, JSONValue], load_json(out / "heldout-inputs-000001.json"))
    assert saved["status"] == "partial" and len(cast(list[JSONValue], saved["cases"])) == 1
