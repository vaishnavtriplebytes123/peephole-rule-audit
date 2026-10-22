"""Syntactic patterns, constant guards, matching, and explicit substitution."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from ruleaudit.ir import BINARY_OPS, Binary, BinaryOp, Const, Expr, Unary, valid_identifier


@dataclass(frozen=True, slots=True)
class Meta:
    name: str
    kind: Literal["expr", "const"]

    def __post_init__(self) -> None:
        if not valid_identifier(self.name) or self.kind not in {"expr", "const"}:
            raise ValueError("metavariable requires an identifier and expr/const kind")


@dataclass(frozen=True, slots=True)
class PUnary:
    op: Literal["not"]
    operand: "Pattern"

    def __post_init__(self) -> None:
        if self.op != "not":
            raise ValueError("unsupported unary pattern operator")


@dataclass(frozen=True, slots=True)
class PBinary:
    op: BinaryOp
    left: "Pattern"
    right: "Pattern"

    def __post_init__(self) -> None:
        if self.op not in BINARY_OPS:
            raise ValueError("unsupported binary pattern operator")


type Pattern = Meta | Const | PUnary | PBinary
type Bindings = dict[str, Expr]
type GuardOperand = str | Const


@dataclass(frozen=True, slots=True)
class Guard:
    op: Literal["eq", "ne"]
    left: GuardOperand
    right: GuardOperand

    def __post_init__(self) -> None:
        if self.op not in {"eq", "ne"}:
            raise ValueError("guard operator must be eq or ne")
        for operand in (self.left, self.right):
            if not isinstance(operand, Const) and not valid_identifier(operand):
                raise ValueError("guard operand must be a constant or metavariable identifier")

    def holds(self, bindings: Mapping[str, Expr]) -> bool:
        def value(operand: GuardOperand) -> int:
            bound = bindings.get(operand) if isinstance(operand, str) else operand
            if not isinstance(bound, Const):
                raise ValueError("guard operand must be bound to a constant")
            return bound.value

        equal = value(self.left) == value(self.right)
        return equal if self.op == "eq" else not equal


def metavariables(pattern: Pattern) -> dict[str, Literal["expr", "const"]]:
    result: dict[str, Literal["expr", "const"]] = {}
    pending = [pattern]
    while pending:
        current = pending.pop()
        if isinstance(current, Meta):
            if current.name in result and result[current.name] != current.kind:
                raise ValueError(f"metavariable {current.name!r} has inconsistent kind")
            result[current.name] = current.kind
        elif isinstance(current, PUnary):
            pending.append(current.operand)
        elif isinstance(current, PBinary):
            pending.extend((current.right, current.left))
        elif not isinstance(current, Const):
            raise ValueError("unsupported pattern node")
    return result


@dataclass(frozen=True, slots=True)
class Provenance:
    source_url: str
    revision: str
    location: str
    original: str
    normalized: str
    restrictions: str
    license: str
    redistribution: str


@dataclass(frozen=True, slots=True)
class Rule:
    id: str
    lhs: Pattern
    rhs: Pattern
    guards: tuple[Guard, ...] = ()
    provenance: Provenance | None = None

    def __post_init__(self) -> None:
        if not valid_identifier(self.id):
            raise ValueError("rule id must be an ASCII identifier of 1–64 characters")
        lhs = metavariables(self.lhs)
        for name, kind in metavariables(self.rhs).items():
            if name not in lhs:
                raise ValueError(f"unbound RHS metavariable {name!r}")
            if lhs[name] != kind:
                raise ValueError(f"metavariable {name!r} has inconsistent kind")
        for guard in self.guards:
            for operand in (guard.left, guard.right):
                if isinstance(operand, str):
                    if operand not in lhs:
                        raise ValueError(f"unbound guard metavariable {operand!r}")
                    if lhs[operand] != "const":
                        raise ValueError("guard metavariables must be constant-valued")

    @property
    def identity(self) -> bool:
        return self.lhs == self.rhs


def match(pattern: Pattern, expression: Expr) -> Bindings | None:
    """First-order ordered matching; no folding, specialization, or commutativity."""
    bindings: Bindings = {}
    pending = [(pattern, expression)]
    while pending:
        current, expr = pending.pop()
        if isinstance(current, Meta):
            if current.kind == "const" and not isinstance(expr, Const):
                return None
            if current.name in bindings and bindings[current.name] != expr:
                return None
            bindings[current.name] = expr
        elif isinstance(current, Const):
            if current != expr:
                return None
        elif isinstance(current, PUnary):
            if not isinstance(expr, Unary) or current.op != expr.op:
                return None
            pending.append((current.operand, expr.operand))
        else:
            if not isinstance(expr, Binary) or current.op != expr.op:
                return None
            pending.extend(((current.right, expr.right), (current.left, expr.left)))
    return bindings


def substitute(pattern: Pattern, bindings: Mapping[str, Expr]) -> Expr:
    if isinstance(pattern, Meta):
        if pattern.name not in bindings:
            raise ValueError(f"unbound metavariable {pattern.name!r}")
        bound = bindings[pattern.name]
        if pattern.kind == "const" and not isinstance(bound, Const):
            raise ValueError(f"{pattern.name!r} requires a constant binding")
        return bound
    if isinstance(pattern, Const):
        return pattern
    if isinstance(pattern, PUnary):
        return Unary("not", substitute(pattern.operand, bindings))
    return Binary(
        pattern.op, substitute(pattern.left, bindings), substitute(pattern.right, bindings)
    )
