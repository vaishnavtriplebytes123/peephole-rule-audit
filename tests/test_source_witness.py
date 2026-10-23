"""Frozen source-derived case and its hand-explained traversal contrast."""

from pathlib import Path
from typing import cast

from ruleaudit.audit import audit_case, check_corpus
from ruleaudit.config import parse_config
from ruleaudit.corpus import parse_corpus
from ruleaudit.io import JSONValue, load_json, parse_expression
from ruleaudit.replay import replay
from ruleaudit.rewrite import Schedule


def test_source_witness_replays_and_preorder_preserves_the_checked_cancellation() -> None:
    value = load_json(Path(__file__).parent / "fixtures/source-qualified-witness.json")
    payload = cast(dict[str, JSONValue], cast(dict[str, JSONValue], value)["payload"])
    assert replay(value)["alternative_checked"] is True
    pair = cast(dict[str, JSONValue], payload["paired"])
    with_target = cast(dict[str, JSONValue], pair["with_target"])
    without = cast(dict[str, JSONValue], pair["without_target"])
    assert with_target["cost"] == 3 and without["cost"] == 11 and pair["delta"] == 8
    assert with_target["stop_reason"] == without["stop_reason"] == "no-match"
    assert [step["rule_id"] for step in cast(list[dict[str, JSONValue]], without["trace"])] == [
        "jog_pAdd2",
        "jog_pAddMoveConstantRight",
    ]
    corpus = parse_corpus(payload["corpus"])
    config = parse_config(payload["config"])
    assert config.run.h == 8 and config.schedule.traversal == "postorder"
    checked = check_corpus(corpus).checked
    assert checked is not None
    expression = parse_expression({"schema_version": 1, "expression": payload["input"]})
    preorder = audit_case(
        expression,
        "jog_pAdd5",
        checked,
        Schedule("preorder", config.schedule.priority),
        config.run,
    )
    assert preorder.comparable
    assert preorder.cost_with == preorder.cost_without == 3 and preorder.delta == 0
    assert [step.rule_id for step in preorder.without_target.trace] == ["jog_pAdd2", "jog_pSub11"]
    assert preorder.with_target.stop_reason == preorder.without_target.stop_reason == "no-match"
