"""Bounded JSON input and canonical expression encoding; never executable formats."""

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from ruleaudit.ir import BINARY_OPS, Binary, BinaryOp, Const, Expr, Unary, Var

type JSONValue = None | bool | int | float | str | list[JSONValue] | dict[str, JSONValue]


class InputError(ValueError):
    def __init__(self, path: str, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"{path}: {reason}")


@dataclass(frozen=True, slots=True)
class InputLimits:
    max_bytes: int = 10 * 1024**2
    max_nodes: int = 1000
    max_depth: int = 64

    def __post_init__(self) -> None:
        for name, ceiling in (("max_bytes", 10 * 1024**2), ("max_nodes", 1000), ("max_depth", 64)):
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= ceiling:
                raise ValueError(f"{name} must be an integer in range [1, {ceiling}]")


DEFAULT_LIMITS = InputLimits()


@dataclass
class _ObjectPairs:
    pairs: list[tuple[str, object]]


def _nonfinite(token: str) -> None:
    raise InputError("$", f"non-finite JSON number {token!r} is not permitted")


def _normalize(value: object, path: str, depth: int = 0) -> JSONValue:
    # Operators have both an object and an args array at each expression level.
    if depth > 300:
        raise InputError(path, "JSON nesting depth exceeds supported limit")
    if isinstance(value, float) and not math.isfinite(value):
        raise InputError(path, "non-finite JSON number is not permitted")
    if isinstance(value, _ObjectPairs):
        result: dict[str, JSONValue] = {}
        for key, item in value.pairs:
            if len(key) > 64:
                raise InputError(path, "JSON object field name exceeds 64 characters")
            child_path = f"{path}.{key}"
            if key in result:
                raise InputError(child_path, f"duplicate JSON field {key!r}")
            result[key] = _normalize(item, child_path, depth + 1)
        return result
    if isinstance(value, list):
        return [_normalize(item, f"{path}[{index}]", depth + 1) for index, item in enumerate(value)]
    return cast(JSONValue, value)


def parse_json(text: str, limits: InputLimits = DEFAULT_LIMITS) -> JSONValue:
    try:
        size = len(text.encode("utf-8"))
    except UnicodeError as error:
        raise InputError("$", "input must be valid UTF-8 text") from error
    if size > limits.max_bytes:
        raise InputError("$", f"input size exceeds {limits.max_bytes} bytes")
    try:
        raw = json.loads(text, object_pairs_hook=_ObjectPairs, parse_constant=_nonfinite)
        return _normalize(raw, "$")
    except InputError:
        raise
    except (ValueError, RecursionError) as error:
        raise InputError("$", "invalid JSON or excessive JSON nesting/integer size") from error


def load_json(path: Path, limits: InputLimits = DEFAULT_LIMITS) -> JSONValue:
    with path.open("rb") as stream:
        raw = stream.read(limits.max_bytes + 1)
    if len(raw) > limits.max_bytes:
        raise InputError("$", f"input size exceeds {limits.max_bytes} bytes")
    try:
        text = raw.decode("utf-8")
    except UnicodeError as error:
        raise InputError("$", "input file must be UTF-8") from error
    return parse_json(text, limits)


def object_fields(value: JSONValue, required: set[str], path: str) -> dict[str, JSONValue]:
    if not isinstance(value, dict):
        raise InputError(path, "expected an object")
    unknown = value.keys() - required
    if unknown:
        raise InputError(f"{path}.{sorted(unknown)[0]}", "unknown field")
    missing = required - value.keys()
    if missing:
        raise InputError(f"{path}.{sorted(missing)[0]}", "required field is missing")
    return value


def parse_expression(value: JSONValue, limits: InputLimits = DEFAULT_LIMITS) -> Expr:
    doc = object_fields(value, {"schema_version", "expression"}, "$")
    version = doc["schema_version"]
    if type(version) is not int or version != 1:
        raise InputError("$.schema_version", "unsupported schema version; expected integer 1")
    count = 0

    def node(raw: JSONValue, path: str, depth: int) -> Expr:
        nonlocal count
        count += 1
        if count > limits.max_nodes:
            raise InputError(path, f"expression node count exceeds {limits.max_nodes}")
        if depth > limits.max_depth:
            raise InputError(path, f"expression depth exceeds {limits.max_depth}")
        if not isinstance(raw, dict):
            raise InputError(path, "expected an expression object")
        op = raw.get("op")
        if not isinstance(op, str) or op not in {"var", "const", "not", *BINARY_OPS}:
            raise InputError(f"{path}.op", "unknown or missing operator")
        if op == "var":
            fields = object_fields(raw, {"op", "name"}, path)
            name = fields["name"]
            try:
                return Var(cast(str, name))
            except ValueError as error:
                raise InputError(f"{path}.name", f"invalid identifier: {error}") from error
        if op == "const":
            fields = object_fields(raw, {"op", "value"}, path)
            try:
                return Const(cast(int, fields["value"]))
            except ValueError as error:
                raise InputError(f"{path}.value", str(error)) from error
        fields = object_fields(raw, {"op", "args"}, path)
        args = fields["args"]
        arity = 1 if op == "not" else 2
        if not isinstance(args, list) or len(args) != arity:
            raise InputError(f"{path}.args", f"expected an array of {arity} operands")
        left = node(args[0], f"{path}.args[0]", depth + 1)
        if op == "not":
            return Unary("not", left)
        right = node(args[1], f"{path}.args[1]", depth + 1)
        return Binary(cast(BinaryOp, op), left, right)

    return node(doc["expression"], "$.expression", 1)


def load_expression(path: Path, limits: InputLimits = DEFAULT_LIMITS) -> Expr:
    return parse_expression(load_json(path, limits), limits)


def expression_node(expr: Expr) -> dict[str, JSONValue]:
    if isinstance(expr, Var):
        return {"op": "var", "name": expr.name}
    if isinstance(expr, Const):
        return {"op": "const", "value": expr.value}
    if isinstance(expr, Unary):
        return {"op": expr.op, "args": [expression_node(expr.operand)]}
    return {"op": expr.op, "args": [expression_node(expr.left), expression_node(expr.right)]}


def expression_document(expr: Expr) -> dict[str, JSONValue]:
    return {"schema_version": 1, "expression": expression_node(expr)}


def canonical_bytes(value: JSONValue) -> bytes:
    return json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("ascii")


def content_hash(value: JSONValue) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()
