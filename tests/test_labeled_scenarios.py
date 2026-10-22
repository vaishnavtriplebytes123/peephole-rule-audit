"""Fixed independent oracles, counted separately from study case denominators."""

import json
from collections import Counter
from pathlib import Path
from typing import Literal, cast

import pytest

from ruleaudit.corpus import load_corpus, parse_pattern
from ruleaudit.io import JSONValue, expression_node, parse_expression
from ruleaudit.ir import Const, Expr, evaluate, measure
from ruleaudit.rewrite import RunLimits, Schedule, run
from ruleaudit.rules import Guard, match

DATA = Path(__file__).parent / "fixtures/labeled-scenarios.json"
SCENARIOS: list[dict[str, JSONValue]] = json.loads(DATA.read_text(encoding="utf8"))["scenarios"]


def expr(value: JSONValue) -> Expr:
    return parse_expression({"schema_version": 1, "expression": value})


def test_labeled_dataset_coverage_and_unique_ids() -> None:
    assert len(SCENARIOS) == len({cast(str, row["id"]) for row in SCENARIOS}) == 112
    assert Counter(cast(str, row["category"]) for row in SCENARIOS) == {
        "semantics": 36,
        "guards": 16,
        "matching": 12,
        "schedule-budget": 48,
    }


@pytest.mark.parametrize("row", SCENARIOS, ids=[cast(str, row["id"]) for row in SCENARIOS])
def test_labeled_scenario(row: dict[str, JSONValue]) -> None:
    if row["category"] == "semantics":
        assert evaluate(expr(row["input"]), {}) == row["expected"]
    elif row["category"] == "guards":
        bindings = {
            name: Const(value) for name, value in cast(dict[str, int], row["bindings"]).items()
        }
        right = row["right"]
        assert (
            Guard(
                cast(Literal["eq", "ne"], row["op"]),
                "C",
                right if isinstance(right, str) else Const(cast(int, right)),
            ).holds(bindings)
            is row["expected"]
        )
    elif row["category"] == "matching":
        actual = match(parse_pattern(row["pattern"], "pattern"), expr(row["input"]))
        assert (
            {key: expression_node(value) for key, value in actual.items()}
            if actual is not None
            else None
        ) == row["expected"]
    else:
        assert row["category"] == "schedule-budget"
        corpus = load_corpus(DATA.parent / f"{row['fixture']}.json")
        priority = tuple(cast(list[str], row["priority"]))
        for label, rules in (
            ("with", corpus.rules),
            ("without", tuple(rule for rule in corpus.rules if rule.id != "A")),
        ):
            result = run(
                expr(row["input"]),
                rules,
                Schedule(
                    cast(Literal["preorder", "postorder"], row["traversal"]),
                    tuple(key for key in priority if label == "with" or key != "A"),
                ),
                RunLimits(h=cast(int, row["h"])),
            )
            expected = cast(dict[str, JSONValue], row[label])
            assert result.completed
            assert measure(result.output).operators == expected["cost"]
            assert expression_node(result.output) == expected["output"]
            assert result.stop_reason == expected["stop"]
            assert [
                {"rule": step.rule_id, "location": list(step.location)} for step in result.trace
            ] == expected["trace"]
