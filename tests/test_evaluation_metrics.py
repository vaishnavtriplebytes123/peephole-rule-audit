from dataclasses import replace
from pathlib import Path
from typing import cast

from ruleaudit.config import Config, Generation
from ruleaudit.corpus import load_corpus
from ruleaudit.experiment import audit_experiment
from ruleaudit.io import JSONValue, load_json
from ruleaudit.metrics import case_key, rate
from ruleaudit.report import ReportWriter
from ruleaudit.rewrite import RunLimits, Schedule

FIXTURES = Path(__file__).parent / "fixtures"


def test_zero_findings_still_have_checked_eligibility_denominator(tmp_path: Path) -> None:
    corpus = load_corpus(FIXTURES / "budget.json")
    config = Config(
        Schedule("preorder", ("A", "B", "C")),
        run=RunLimits(h=2),
        generation=Generation(cases=2, depth=0),
    )
    out = tmp_path / "audit"
    assert (
        audit_experiment(
            corpus, config, corpus.rules[0], ReportWriter(out, config.max_output_bytes)
        )
        == 0
    )
    report = cast(dict[str, JSONValue], load_json(out / "audit.json"))
    assert report["findings"] == 0 and report["eligible_cases"] == 2
    assert report["primary_interference_cases"] == 0
    assert report["time_to_first_qualified_finding"] is None
    for row in cast(list[dict[str, JSONValue]], report["records"]):
        assert row["eligible_alternative"] is True and row["alternative_steps"] == 2
        assert row["checked_alternative"] is None
        assert row["case_key"]


def test_primary_interference_denominator_and_censoring(tmp_path: Path) -> None:
    corpus = load_corpus(FIXTURES / "interference.json")
    config = Config(
        Schedule("preorder", ("A", "B", "D", "C")),
        run=RunLimits(h=4),
        generation=Generation(cases=1, depth=0),
    )
    out = tmp_path / "audit"
    assert (
        audit_experiment(
            corpus, config, corpus.rules[0], ReportWriter(out, config.max_output_bytes)
        )
        == 0
    )
    report = cast(dict[str, JSONValue], load_json(out / "audit.json"))
    assert report["primary_interference_cases"] == report["primary_interference_findings"] == 1
    assert report["trial_to_first_finding"] == report["attempt_to_first_finding"] == 1
    assert cast(float, report["time_to_first_qualified_finding"]) > 0
    assert rate(0, 0) is None and rate(0, 3) == 0.0 and rate(1, 2) == 0.5


def test_uniqueness_key_ignores_seed_and_mode_but_preserves_semantic_settings() -> None:
    config = Config(Schedule("preorder", ("A", "B", "C")))
    key = case_key("input", "A", "corpus", config)
    other = replace(config, generation=replace(config.generation, strategy="random", seed=99))
    assert key == case_key("input", "A", "corpus", other)
    for changed in (
        replace(config, run=replace(config.run, h=4)),
        replace(config, schedule=Schedule("postorder", config.schedule.priority)),
        replace(config, run=replace(config.run, max_nodes=500)),
    ):
        assert key != case_key("input", "A", "corpus", changed)
    assert key != case_key("input", "B", "corpus", config)
    assert key != case_key("input", "A", "different_corpus", config)
