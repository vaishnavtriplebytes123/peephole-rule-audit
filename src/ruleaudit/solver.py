"""Local SMT boundary; unknown, resource exhaustion, and unsatisfiable guards differ."""

from collections.abc import Callable
from dataclasses import dataclass
from time import perf_counter
from typing import Literal, Protocol, cast

import z3  # type: ignore[import-untyped]

from ruleaudit.ir import Binary, Const, Expr, Unary, Var
from ruleaudit.rules import Guard, GuardOperand, Meta, Pattern, PBinary, PUnary, Rule, metavariables


@dataclass(frozen=True, slots=True)
class SolverLimits:
    timeout_ms: int = 1000
    max_calls: int = 1000

    def __post_init__(self) -> None:
        for name, low, high in (("timeout_ms", 1, 60000), ("max_calls", 0, 1000000)):
            value = getattr(self, name)
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f"{name} must be an integer in [{low}, {high}]")


DEFAULT_SOLVER_LIMITS = SolverLimits()


@dataclass(frozen=True, slots=True)
class QueryResult:
    status: Literal["sat", "unsat", "unknown"]
    valuation: tuple[tuple[str, int], ...] = ()
    reason: str = ""


@dataclass(frozen=True, slots=True)
class ValidationResult:
    status: Literal["verified", "invalid", "unknown", "unsatisfiable_guard", "unsupported"]
    valuation: tuple[tuple[str, int], ...] = ()
    reason: str = ""
    warning: str = ""


class SemanticBackend(Protocol):
    def query(self, rule: Rule, *, inequality: bool) -> QueryResult: ...


class EquivalenceBackend(Protocol):
    def equivalence(self, left: Expr, right: Expr) -> QueryResult: ...


class ProofBackend(SemanticBackend, EquivalenceBackend, Protocol):
    pass


def _runtime_pattern(expr: Expr) -> Pattern:
    if isinstance(expr, Var):
        return Meta(expr.name, "expr")
    if isinstance(expr, Const):
        return expr
    if isinstance(expr, Unary):
        return PUnary("not", _runtime_pattern(expr.operand))
    assert isinstance(expr, Binary)
    return PBinary(expr.op, _runtime_pattern(expr.left), _runtime_pattern(expr.right))


class Z3Backend:
    def __init__(
        self,
        limits: SolverLimits = DEFAULT_SOLVER_LIMITS,
        *,
        deadline: float | None = None,
        now: Callable[[], float] = perf_counter,
    ) -> None:
        self.limits = limits
        self.calls = 0
        self.deadline = deadline
        self.now = now

    def query(self, rule: Rule, *, inequality: bool) -> QueryResult:
        return self._solve(rule.lhs, rule.rhs, rule.guards, inequality=inequality)

    def equivalence(self, left: Expr, right: Expr) -> QueryResult:
        return self._solve(_runtime_pattern(left), _runtime_pattern(right), (), inequality=True)

    def _solve(
        self, lhs: Pattern, rhs: Pattern, guards: tuple[Guard, ...], *, inequality: bool
    ) -> QueryResult:
        if self.deadline is not None and self.now() >= self.deadline:
            return QueryResult("unknown", reason="solver-deadline")
        if self.calls >= self.limits.max_calls:
            return QueryResult("unknown", reason="solver-call-limit")
        self.calls += 1
        names = set(metavariables(lhs)) | set(metavariables(rhs))
        symbols = {name: z3.BitVec(name, 32) for name in sorted(names)}

        def term(pattern: Pattern) -> z3.BitVecRef:
            if isinstance(pattern, Meta):
                return symbols[pattern.name]
            if isinstance(pattern, Const):
                return z3.BitVecVal(pattern.value, 32)
            if isinstance(pattern, PUnary):
                return ~term(pattern.operand)
            assert isinstance(pattern, PBinary)
            left, right = term(pattern.left), term(pattern.right)
            match pattern.op:
                case "add":
                    return left + right
                case "sub":
                    return left - right
                case "and":
                    return left & right
                case "or":
                    return left | right
                case "xor":
                    return left ^ right

        def guard_operand(operand: GuardOperand) -> z3.BitVecRef:
            return symbols[operand] if isinstance(operand, str) else z3.BitVecVal(operand.value, 32)

        solver = z3.Solver()
        solver.set(timeout=self.limits.timeout_ms)
        for guard in guards:
            equal = guard_operand(guard.left) == guard_operand(guard.right)
            solver.add(equal if guard.op == "eq" else z3.Not(equal))
        if inequality:
            solver.add(term(lhs) != term(rhs))
        result = solver.check()
        if result == z3.unsat:
            return QueryResult("unsat")
        if result != z3.sat:
            return QueryResult("unknown", reason=solver.reason_unknown())
        model = solver.model()
        valuation = tuple(
            (name, cast(int, model.eval(symbols[name], model_completion=True).as_long()))
            for name in sorted(symbols)
        )
        return QueryResult("sat", valuation)


def check_rule(
    rule: Rule,
    limits: SolverLimits = DEFAULT_SOLVER_LIMITS,
    *,
    backend: SemanticBackend | None = None,
) -> ValidationResult:
    adapter = backend if backend is not None else Z3Backend(limits)
    guard = adapter.query(rule, inequality=False)
    if guard.status == "unknown":
        return ValidationResult("unknown", reason=guard.reason)
    if guard.status == "unsat":
        return ValidationResult("unsatisfiable_guard", reason="guard has no satisfying valuation")
    unequal = adapter.query(rule, inequality=True)
    if unequal.status == "unknown":
        return ValidationResult("unknown", reason=unequal.reason)
    if unequal.status == "sat":
        return ValidationResult("invalid", unequal.valuation)
    warning = "identity rule consumes rewrite budget" if rule.identity else ""
    return ValidationResult("verified", warning=warning)


def check_equivalence(
    left: Expr,
    right: Expr,
    limits: SolverLimits = DEFAULT_SOLVER_LIMITS,
    *,
    backend: EquivalenceBackend | None = None,
) -> ValidationResult:
    adapter = backend if backend is not None else Z3Backend(limits)
    result = adapter.equivalence(left, right)
    if result.status == "unknown":
        return ValidationResult("unknown", reason=result.reason)
    if result.status == "sat":
        return ValidationResult("invalid", result.valuation)
    return ValidationResult("verified")
