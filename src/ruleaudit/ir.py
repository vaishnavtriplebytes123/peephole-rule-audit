"""Immutable trees and total unsigned 32-bit expression semantics.

This evaluator deliberately has no solver, rewrite engine, I/O, or clock effects.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, NamedTuple

MASK = 2**32 - 1
BinaryOp = Literal["add", "sub", "and", "or", "xor"]
BINARY_OPS = frozenset({"add", "sub", "and", "or", "xor"})
_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,63}", re.ASCII)


def valid_identifier(name: object) -> bool:
    return isinstance(name, str) and _IDENTIFIER.fullmatch(name) is not None


def valid_word(value: object) -> bool:
    return type(value) is int and 0 <= value <= MASK


@dataclass(frozen=True, slots=True)
class Var:
    name: str

    def __post_init__(self) -> None:
        if not valid_identifier(self.name):
            raise ValueError("variable name must be an ASCII identifier of 1–64 characters")


@dataclass(frozen=True, slots=True)
class Const:
    value: int

    def __post_init__(self) -> None:
        if not valid_word(self.value):
            raise ValueError("constant must be an integer in range [0, 4294967295]")


@dataclass(frozen=True, slots=True)
class Unary:
    op: Literal["not"]
    operand: "Expr"

    def __post_init__(self) -> None:
        if self.op != "not":
            raise ValueError("unsupported unary operator")
        _require_expr(self.operand)


@dataclass(frozen=True, slots=True)
class Binary:
    op: BinaryOp
    left: "Expr"
    right: "Expr"

    def __post_init__(self) -> None:
        if self.op not in BINARY_OPS:
            raise ValueError("unsupported binary operator")
        _require_expr(self.left)
        _require_expr(self.right)


type Expr = Var | Const | Unary | Binary


def _require_expr(value: object) -> None:
    if not isinstance(value, Var | Const | Unary | Binary):
        raise ValueError("operand must be an expression")


def children(expr: Expr) -> tuple[Expr, ...]:
    if isinstance(expr, Unary):
        return (expr.operand,)
    if isinstance(expr, Binary):
        return (expr.left, expr.right)
    return ()


class Size(NamedTuple):
    nodes: int
    depth: int
    operators: int


def measure(expr: Expr) -> Size:
    """Count occurrences, root-inclusive depth, and operator cost without recursion."""
    nodes = depth = operators = 0
    pending = [(expr, 1)]
    while pending:
        current, level = pending.pop()
        nodes += 1
        depth = max(depth, level)
        if isinstance(current, Unary | Binary):
            operators += 1
        pending.extend((child, level + 1) for child in children(current))
    return Size(nodes, depth, operators)


def evaluate(expr: Expr, bindings: Mapping[str, int]) -> int:
    """Evaluate with explicit bindings, using a stack independent of tree depth."""
    values: list[int] = []
    pending = [(expr, False)]
    while pending:
        current, visited = pending.pop()
        if isinstance(current, Const):
            values.append(current.value)
        elif isinstance(current, Var):
            if current.name not in bindings:
                raise ValueError(f"missing binding for variable {current.name!r}")
            value = bindings[current.name]
            if not valid_word(value):
                raise ValueError(f"binding for {current.name!r} must be a 32-bit integer")
            values.append(value)
        elif not visited:
            pending.append((current, True))
            pending.extend((child, False) for child in reversed(children(current)))
        elif isinstance(current, Unary):
            values.append((~values.pop()) & MASK)
        else:
            right, left = values.pop(), values.pop()
            match current.op:
                case "add":
                    result = left + right
                case "sub":
                    result = left - right
                case "and":
                    result = left & right
                case "or":
                    result = left | right
                case "xor":
                    result = left ^ right
            values.append(result & MASK)
    return values[0]
