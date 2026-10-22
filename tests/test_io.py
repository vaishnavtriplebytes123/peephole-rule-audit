import json
from pathlib import Path

import pytest

from ruleaudit.io import (
    InputError,
    InputLimits,
    canonical_bytes,
    content_hash,
    expression_document,
    load_expression,
    parse_expression,
    parse_json,
)
from ruleaudit.ir import Binary, Const, Unary, Var


def document(expression: object, version: object = 1) -> str:
    return json.dumps({"schema_version": version, "expression": expression})


def test_roundtrip_unicode_path_and_canonical_form(tmp_path: Path) -> None:
    expr = Binary("add", Unary("not", Var("x")), Const(0xFFFFFFFF))
    path = tmp_path / "문서 with spaces.json"
    path.write_bytes(canonical_bytes(expression_document(expr)))
    assert load_expression(path) == expr
    assert canonical_bytes({"b": 1, "a": 2}) == b'{"a":2,"b":1}'
    assert content_hash({"b": 1, "a": 2}) == content_hash({"a": 2, "b": 1})
    assert len(content_hash(expression_document(expr))) == 64


@pytest.mark.parametrize(
    "text,path,reason",
    [
        (
            '{"schema_version":1,"expression":{"op":"const","value":0,"value":1}}',
            "$.expression.value",
            "duplicate",
        ),
        (document({"op": "const", "value": True}), "$.expression.value", "integer"),
        (document({"op": "const", "value": -1}), "$.expression.value", "range"),
        (document({"op": "const", "value": 2**32}), "$.expression.value", "range"),
        (document({"op": "const", "value": 1.0}), "$.expression.value", "integer"),
        (document({"op": "var", "name": "é"}), "$.expression.name", "identifier"),
        (document({"op": "var", "name": "a" * 65}), "$.expression.name", "identifier"),
        (document({"op": "mul", "args": []}), "$.expression.op", "operator"),
        (document({"op": "add", "args": []}), "$.expression.args", "2"),
        (document({"op": "not", "args": []}), "$.expression.args", "1"),
        (document({"op": "const", "value": 0, "extra": 1}), "$.expression.extra", "unknown"),
        (document({"op": "const"}), "$.expression.value", "required"),
        (document(None), "$.expression", "object"),
        (document({"op": "const", "value": 0}, True), "$.schema_version", "version"),
        (document({"op": "const", "value": 0}, 2), "$.schema_version", "version"),
        ('{"schema_version":1,"expression":{"op":"const","value":0},"x":1}', "$.x", "unknown"),
        ('{"schema_version":1,"expression":{"op":"const","value":NaN}}', "$", "non-finite"),
        ('{"expression":', "$", "JSON"),
        ("[0]", "$", "object"),
    ],
)
def test_invalid_documents(text: str, path: str, reason: str) -> None:
    with pytest.raises(InputError) as caught:
        parse_expression(parse_json(text))
    assert caught.value.path == path
    assert reason in str(caught.value)


def test_depth_and_node_limits() -> None:
    tree: object = {"op": "var", "name": "x"}
    for _ in range(63):
        tree = {"op": "not", "args": [tree]}
    assert parse_expression(parse_json(document(tree))) == _not_chain(63)
    tree = {"op": "not", "args": [tree]}
    with pytest.raises(InputError, match="depth"):
        parse_expression(parse_json(document(tree)))
    two = {"op": "not", "args": [{"op": "const", "value": 1}]}
    with pytest.raises(InputError, match="node"):
        parse_expression(parse_json(document(two)), InputLimits(max_nodes=1))
    with pytest.raises(InputError, match="depth"):
        parse_expression(parse_json(document(two)), InputLimits(max_depth=1))


def _not_chain(count: int) -> Unary | Var:
    result: Unary | Var = Var("x")
    for _ in range(count):
        result = Unary("not", result)
    return result


def test_parser_recursion_size_encoding_and_io_errors(tmp_path: Path) -> None:
    with pytest.raises(InputError, match="JSON"):
        parse_json("[" * 5000 + "0" + "]" * 5000)
    with pytest.raises(InputError, match="size"):
        parse_json(" " * 11, InputLimits(max_bytes=10))
    path = tmp_path / "large.json"
    path.write_bytes(b" " * 11)
    with pytest.raises(InputError, match="size"):
        load_expression(path, InputLimits(max_bytes=10))
    path.write_bytes(b"\xff")
    with pytest.raises(InputError, match="UTF-8"):
        load_expression(path)
    with pytest.raises(OSError):
        load_expression(tmp_path / "missing.json")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_nodes": True},
        {"max_depth": 0},
        {"max_bytes": -1},
        {"max_nodes": 1001},
        {"max_depth": 65},
        {"max_bytes": 10 * 1024**2 + 1},
    ],
)
def test_invalid_limits(kwargs: dict[str, int]) -> None:
    with pytest.raises(ValueError):
        InputLimits(**kwargs)


def test_overflowed_json_number_is_not_finite() -> None:
    with pytest.raises(InputError, match="non-finite"):
        parse_json('{"number":1e999}')


def test_exact_default_node_ceiling() -> None:
    def balanced(leaves: int) -> dict[str, object]:
        if leaves == 1:
            return {"op": "const", "value": 0}
        return {"op": "add", "args": [balanced(leaves // 2), balanced(leaves - leaves // 2)]}

    valid = {"op": "not", "args": [balanced(500)]}
    from ruleaudit.ir import measure

    assert measure(parse_expression(parse_json(document(valid)))).nodes == 1000
    with pytest.raises(InputError, match="node count"):
        parse_expression(parse_json(document(balanced(501))))
