"""Versioned corpus schema; provenance is data and never an instruction or URL fetch."""

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal, cast

from ruleaudit.io import (
    DEFAULT_LIMITS,
    InputError,
    InputLimits,
    JSONValue,
    load_json,
    object_fields,
)
from ruleaudit.ir import BINARY_OPS, BinaryOp, Const, valid_word
from ruleaudit.rules import Guard, GuardOperand, Meta, Pattern, PBinary, Provenance, PUnary, Rule

_PROVENANCE_FIELDS = {
    "source_url",
    "revision",
    "location",
    "original",
    "normalized",
    "restrictions",
    "license",
    "redistribution",
}


@dataclass(frozen=True, slots=True)
class Corpus:
    kind: Literal["synthetic", "source"]
    rules: tuple[Rule, ...]


def parse_pattern(value: JSONValue, path: str, limits: InputLimits = DEFAULT_LIMITS) -> Pattern:
    count = 0

    def node(raw: JSONValue, at: str, depth: int) -> Pattern:
        nonlocal count
        count += 1
        if count > limits.max_nodes:
            raise InputError(at, f"pattern node count exceeds {limits.max_nodes}")
        if depth > limits.max_depth:
            raise InputError(at, f"pattern depth exceeds {limits.max_depth}")
        if not isinstance(raw, dict):
            raise InputError(at, "expected a pattern object")
        op = raw.get("op")
        if not isinstance(op, str) or op not in {"meta", "const", "not", *BINARY_OPS}:
            raise InputError(f"{at}.op", "unknown or missing pattern operator")
        try:
            if op == "meta":
                fields = object_fields(raw, {"op", "name", "kind"}, at)
                return Meta(
                    cast(str, fields["name"]), cast(Literal["expr", "const"], fields["kind"])
                )
            if op == "const":
                fields = object_fields(raw, {"op", "value"}, at)
                return Const(cast(int, fields["value"]))
        except InputError:
            raise
        except (ValueError, TypeError) as error:
            raise InputError(at, str(error)) from error
        fields = object_fields(raw, {"op", "args"}, at)
        args = fields["args"]
        arity = 1 if op == "not" else 2
        if not isinstance(args, list) or len(args) != arity:
            raise InputError(f"{at}.args", f"expected an array of {arity} operands")
        left = node(args[0], f"{at}.args[0]", depth + 1)
        if op == "not":
            return PUnary("not", left)
        return PBinary(cast(BinaryOp, op), left, node(args[1], f"{at}.args[1]", depth + 1))

    return node(value, path, 1)


def pattern_node(pattern: Pattern) -> dict[str, JSONValue]:
    if isinstance(pattern, Meta):
        return {"op": "meta", "name": pattern.name, "kind": pattern.kind}
    if isinstance(pattern, Const):
        return {"op": "const", "value": pattern.value}
    if isinstance(pattern, PUnary):
        return {"op": "not", "args": [pattern_node(pattern.operand)]}
    return {"op": pattern.op, "args": [pattern_node(pattern.left), pattern_node(pattern.right)]}


def _parse_guard(value: JSONValue, path: str) -> Guard:
    fields = object_fields(value, {"op", "left", "right"}, path)
    op = fields["op"]
    if op not in ("eq", "ne"):
        raise InputError(f"{path}.op", "guard operator must be eq or ne")

    def operand(raw: JSONValue, at: str) -> GuardOperand:
        if isinstance(raw, str):
            return raw
        if valid_word(raw):
            return Const(cast(int, raw))
        raise InputError(at, "guard operand must be a constant metavariable name or 32-bit integer")

    try:
        return Guard(
            cast(Literal["eq", "ne"], op),
            operand(fields["left"], f"{path}.left"),
            operand(fields["right"], f"{path}.right"),
        )
    except InputError:
        raise
    except ValueError as error:
        raise InputError(path, str(error)) from error


def parse_corpus(value: JSONValue, limits: InputLimits = DEFAULT_LIMITS) -> Corpus:
    doc = object_fields(value, {"schema_version", "kind", "rules"}, "$")
    if type(doc["schema_version"]) is not int or doc["schema_version"] != 1:
        raise InputError("$.schema_version", "unsupported schema version; expected integer 1")
    if doc["kind"] not in ("synthetic", "source"):
        raise InputError("$.kind", "expected synthetic or source")
    records = doc["rules"]
    if not isinstance(records, list) or not 1 <= len(records) <= 100:
        raise InputError("$.rules", "expected between 1 and 100 rules")
    rules: list[Rule] = []
    seen: set[str] = set()
    for index, raw in enumerate(records):
        path = f"$.rules[{index}]"
        fields = object_fields(raw, {"id", "lhs", "rhs", "guards", "provenance"}, path)
        rule_id = fields["id"]
        if not isinstance(rule_id, str):
            raise InputError(f"{path}.id", "expected a rule identifier")
        if rule_id in seen:
            raise InputError(f"{path}.id", f"duplicate rule id {rule_id!r}")
        seen.add(rule_id)
        guards = fields["guards"]
        if not isinstance(guards, list) or len(guards) > 64:
            raise InputError(f"{path}.guards", "expected an array of at most 64 guards")
        source = object_fields(fields["provenance"], _PROVENANCE_FIELDS, f"{path}.provenance")
        for key, text in source.items():
            if not isinstance(text, str) or not text.strip() or len(text) > 16384:
                raise InputError(
                    f"{path}.provenance.{key}", "expected 1–16384 nonempty text characters"
                )
        provenance = Provenance(**cast(dict[str, str], source))
        lhs = parse_pattern(fields["lhs"], f"{path}.lhs", limits)
        rhs = parse_pattern(fields["rhs"], f"{path}.rhs", limits)
        parsed_guards = tuple(
            _parse_guard(guard, f"{path}.guards[{i}]") for i, guard in enumerate(guards)
        )
        try:
            rules.append(Rule(rule_id, lhs, rhs, parsed_guards, provenance))
        except ValueError as error:
            raise InputError(path, str(error)) from error
    return Corpus(cast(Literal["synthetic", "source"], doc["kind"]), tuple(rules))


def load_corpus(path: Path, limits: InputLimits = DEFAULT_LIMITS) -> Corpus:
    return parse_corpus(load_json(path, limits), limits)


def rule_document(rule: Rule) -> dict[str, JSONValue]:
    if rule.provenance is None:
        raise ValueError("serialized corpus rules require provenance")

    def operand(value: GuardOperand) -> JSONValue:
        return value if isinstance(value, str) else value.value

    return {
        "id": rule.id,
        "lhs": pattern_node(rule.lhs),
        "rhs": pattern_node(rule.rhs),
        "guards": [
            {"op": g.op, "left": operand(g.left), "right": operand(g.right)} for g in rule.guards
        ],
        "provenance": cast(dict[str, JSONValue], asdict(rule.provenance)),
    }


def corpus_document(corpus: Corpus) -> dict[str, JSONValue]:
    return {
        "schema_version": 1,
        "kind": corpus.kind,
        "rules": [rule_document(r) for r in corpus.rules],
    }
