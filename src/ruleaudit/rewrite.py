"""Deterministic first-match rewriting with explicit locations and budgets."""

import math
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from time import perf_counter
from typing import Literal

from ruleaudit.ir import Binary, Expr, Unary, children
from ruleaudit.rules import Rule, match, substitute

type Location = tuple[int, ...]
type StopReason = Literal["no-match", "rewrite-budget", "growth-limit", "time-limit", "interrupted"]


@dataclass(frozen=True, slots=True)
class Schedule:
    traversal: Literal["preorder", "postorder"]
    priority: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.traversal not in {"preorder", "postorder"}:
            raise ValueError("traversal must be preorder or postorder")


@dataclass(frozen=True, slots=True)
class RunLimits:
    h: int = 8
    max_nodes: int = 10000
    max_depth: int = 128
    seconds: float = 60.0

    def __post_init__(self) -> None:
        for name, low, high in (("h", 0, 10000), ("max_nodes", 1, 10000), ("max_depth", 1, 128)):
            value = getattr(self, name)
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f"{name} must be an integer in [{low}, {high}]")
        if (
            type(self.seconds) not in {int, float}
            or not 0 <= self.seconds <= 3600
            or not math.isfinite(self.seconds)
        ):
            raise ValueError("seconds must be finite and in [0, 3600]")


DEFAULT_RUN_LIMITS = RunLimits()


@dataclass(frozen=True, slots=True)
class Step:
    rule_id: str
    location: Location
    before: Expr
    after: Expr
    bindings: tuple[tuple[str, Expr], ...]
    guards: tuple[bool, ...]


@dataclass(frozen=True, slots=True)
class RunResult:
    output: Expr
    trace: tuple[Step, ...]
    stop_reason: StopReason
    elapsed: float

    @property
    def completed(self) -> bool:
        return self.stop_reason in {"no-match", "rewrite-budget", "growth-limit"}


def _within_growth_limits(expr: Expr, limits: RunLimits) -> bool:
    count = 0
    pending = [(expr, 1)]
    while pending:
        current, depth = pending.pop()
        count += 1
        if count > limits.max_nodes or depth > limits.max_depth:
            return False
        pending.extend((child, depth + 1) for child in children(current))
    return True


def locations(
    expr: Expr, traversal: Literal["preorder", "postorder"]
) -> Iterator[tuple[Location, Expr]]:
    pending: list[tuple[Location, Expr, bool]] = [((), expr, False)]
    while pending:
        path, current, visited = pending.pop()
        if visited or traversal == "preorder":
            yield path, current
        if not visited:
            if traversal == "postorder":
                pending.append((path, current, True))
            pending.extend(
                ((*path, i), child, False)
                for i, child in reversed(tuple(enumerate(children(current))))
            )


def replace(expr: Expr, location: Location, replacement: Expr) -> Expr:
    if not location:
        return replacement
    index, *tail = location
    rest = tuple(tail)
    if isinstance(expr, Unary) and index == 0:
        return Unary("not", replace(expr.operand, rest, replacement))
    if isinstance(expr, Binary):
        if index == 0:
            return Binary(expr.op, replace(expr.left, rest, replacement), expr.right)
        if index == 1:
            return Binary(expr.op, expr.left, replace(expr.right, rest, replacement))
    raise ValueError("invalid rewrite location")


def run(
    expr: Expr,
    rules: tuple[Rule, ...],
    schedule: Schedule,
    limits: RunLimits = DEFAULT_RUN_LIMITS,
    *,
    now: Callable[[], float] = perf_counter,
) -> RunResult:
    by_id = {rule.id: rule for rule in rules}
    if (
        len(by_id) != len(rules)
        or len(schedule.priority) != len(rules)
        or set(schedule.priority) != set(by_id)
    ):
        raise ValueError("priority must contain every unique rule id exactly once")
    ordered = tuple(by_id[name] for name in schedule.priority)
    started = now()
    state: tuple[Expr, tuple[Step, ...]] = (expr, ())

    def finish(reason: StopReason) -> RunResult:
        return RunResult(*state, reason, max(0.0, now() - started))

    try:
        while True:
            current, trace = state
            if len(trace) >= limits.h:
                return finish("rewrite-budget")
            if now() - started >= limits.seconds:
                return finish("time-limit")
            rewritten = False
            for path, subtree in locations(current, schedule.traversal):
                for rule in ordered:
                    if now() - started >= limits.seconds:
                        return finish("time-limit")
                    bindings = match(rule.lhs, subtree)
                    if bindings is None:
                        continue
                    guards = tuple(guard.holds(bindings) for guard in rule.guards)
                    if not all(guards):
                        continue
                    replacement = substitute(rule.rhs, bindings)
                    candidate = replace(current, path, replacement)
                    if not _within_growth_limits(candidate, limits):
                        return finish("growth-limit")
                    step = Step(
                        rule.id, path, subtree, replacement, tuple(sorted(bindings.items())), guards
                    )
                    # One assignment preserves a consistent prefix on interruption.
                    state = (candidate, (*trace, step))
                    rewritten = True
                    break
                if rewritten:
                    break
            if not rewritten:
                return finish("no-match")
    except KeyboardInterrupt:
        return finish("interrupted")
