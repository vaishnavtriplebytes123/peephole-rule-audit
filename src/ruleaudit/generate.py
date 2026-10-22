"""Seeded target-pattern generation with no access to derivation data."""

import hashlib
import random
from dataclasses import dataclass

from ruleaudit.config import Generation
from ruleaudit.ir import Binary, BinaryOp, Const, Expr, Unary, Var, within_limits
from ruleaudit.rules import Rule, metavariables, substitute


@dataclass(frozen=True, slots=True)
class Case:
    expression: Expr
    strategy: str
    seed: int
    attempt: int
    bindings: tuple[tuple[str, Expr], ...]


@dataclass(frozen=True, slots=True)
class Generated:
    cases: tuple[Case, ...]
    attempts: int
    duplicates: int
    rejections: int
    completed: bool


def attempt_rng(seed: int, strategy: str, attempt: int, stream: str) -> random.Random:
    key = f"{seed}:{strategy}:{attempt}:{stream}".encode("ascii")
    return random.Random(int.from_bytes(hashlib.sha256(key).digest(), "big"))


def random_expression(rng: random.Random, constants: tuple[int, ...], depth: int) -> Expr:
    if depth == 0 or rng.randrange(3) == 0:
        return (
            Var(rng.choice(("x", "y", "z")))
            if rng.randrange(2) == 0
            else Const(rng.choice(constants))
        )
    op: BinaryOp | str = rng.choice(("add", "sub", "and", "or", "xor", "not"))
    left = random_expression(rng, constants, depth - 1)
    if op == "not":
        return Unary("not", left)
    from typing import cast

    return Binary(cast(BinaryOp, op), left, random_expression(rng, constants, depth - 1))


def target_attempt(target: Rule, settings: Generation, attempt: int) -> Case | None:
    if type(attempt) is not int or not 1 <= attempt <= settings.attempts:
        raise ValueError("attempt must be within the configured attempt budget")
    rng = attempt_rng(settings.seed, settings.strategy, attempt, "bindings")
    bindings = {
        name: Const(rng.choice(settings.constants))
        if kind == "const"
        else random_expression(rng, settings.constants, settings.depth)
        for name, kind in sorted(metavariables(target.lhs).items())
    }
    if not all(guard.holds(bindings) for guard in target.guards):
        return None
    expression = substitute(target.lhs, bindings)
    if not within_limits(expression, 1000, 64):
        return None
    return Case(
        expression, settings.strategy, settings.seed, attempt, tuple(sorted(bindings.items()))
    )


def generate_target(target: Rule, settings: Generation) -> Generated:
    cases: list[Case] = []
    seen: set[Expr] = set()
    duplicates = rejections = attempts = 0
    for attempt in range(1, settings.attempts + 1):
        attempts = attempt
        case = target_attempt(target, settings, attempt)
        if case is None:
            rejections += 1
        elif case.expression in seen:
            duplicates += 1
        else:
            cases.append(case)
            seen.add(case.expression)
        if len(cases) == settings.cases:
            break
    return Generated(tuple(cases), attempts, duplicates, rejections, len(cases) == settings.cases)
