import copy
from typing import cast

import pytest

from ruleaudit.corpus import corpus_document, parse_corpus
from ruleaudit.io import InputError, JSONValue
from ruleaudit.rules import Meta


def fixture() -> dict[str, JSONValue]:
    x: dict[str, JSONValue] = {"op": "meta", "name": "X", "kind": "expr"}
    return {
        "schema_version": 1,
        "kind": "synthetic",
        "rules": [
            {
                "id": "identity",
                "lhs": x,
                "rhs": x,
                "guards": [],
                "provenance": {
                    key: "synthetic fixture"
                    for key in (
                        "source_url",
                        "revision",
                        "location",
                        "original",
                        "normalized",
                        "restrictions",
                        "license",
                        "redistribution",
                    )
                },
            }
        ],
    }


def test_roundtrip_and_identity_warning() -> None:
    corpus = parse_corpus(fixture())
    assert corpus.kind == "synthetic"
    assert corpus.rules[0].lhs == Meta("X", "expr")
    assert corpus.rules[0].identity
    assert corpus_document(corpus) == fixture()


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", True),
        ("schema_version", 2),
        ("kind", "unknown"),
        ("rules", []),
        ("extra", 1),
    ],
)
def test_bad_envelope(field: str, value: JSONValue) -> None:
    data = fixture()
    data[field] = value
    with pytest.raises(InputError):
        parse_corpus(data)


def test_rule_id_duplicates_unknown_fields_unbound_and_guard_kinds() -> None:
    data = fixture()
    rules = cast(list[JSONValue], data["rules"])
    rules.append(copy.deepcopy(rules[0]))
    with pytest.raises(InputError, match="duplicate"):
        parse_corpus(data)
    rules.pop()
    rule = cast(dict[str, JSONValue], rules[0])
    rule["rhs"] = {"op": "meta", "name": "Y", "kind": "expr"}
    with pytest.raises(InputError, match="unbound"):
        parse_corpus(data)
    rule["rhs"] = rule["lhs"]
    rule["guards"] = [{"op": "eq", "left": "X", "right": 0}]
    with pytest.raises(InputError, match="constant"):
        parse_corpus(data)
    rule["guards"] = []
    rule["lhs"] = {"op": "var", "name": "x"}
    with pytest.raises(InputError, match="operator"):
        parse_corpus(data)


def test_rule_count_and_pattern_depth_caps() -> None:
    data = fixture()
    data["rules"] = cast(list[JSONValue], data["rules"]) * 101
    with pytest.raises(InputError, match="100"):
        parse_corpus(data)
    data = fixture()
    rule = cast(dict[str, JSONValue], cast(list[JSONValue], data["rules"])[0])
    lhs = rule["lhs"]
    for _ in range(64):
        lhs = {"op": "not", "args": [lhs]}
    rule["lhs"] = lhs
    with pytest.raises(InputError, match="depth"):
        parse_corpus(data)


def test_guard_boolean_and_provenance_length() -> None:
    data = fixture()
    rule = cast(dict[str, JSONValue], cast(list[JSONValue], data["rules"])[0])
    rule["guards"] = [{"op": "eq", "left": True, "right": 0}]
    with pytest.raises(InputError, match="operand"):
        parse_corpus(data)
    rule["guards"] = []
    provenance = cast(dict[str, JSONValue], rule["provenance"])
    provenance["original"] = "x" * 16385
    with pytest.raises(InputError, match="16384"):
        parse_corpus(data)
