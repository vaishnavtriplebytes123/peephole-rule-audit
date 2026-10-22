"""Scoped one/two-step forward search with opaque expression placeholders."""

import math
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from itertools import product
from time import perf_counter
from typing import Literal

from ruleaudit.ir import MASK, Const, Expr, Var, valid_word, within_limits
from ruleaudit.rewrite import Step, locations, replace
from ruleaudit.rules import Rule, match, metavariables, substitute
from ruleaudit.solver import ProofBackend, Z3Backend, check_equivalence, check_rule


@dataclass(frozen=True, slots=True)
class DeriveLimits:
    max_steps: int = 2
    max_states: int = 1000
    max_match_attempts: int = 100000
    max_bindings: int = 64
    max_nodes: int = 10000
    max_depth: int = 128
    seconds: float = 60.0

    def __post_init__(self) -> None:
        for name, low, high in (
            ("max_steps", 1, 2),
            ("max_states", 1, 10000),
            ("max_match_attempts", 0, 1000000),
            ("max_bindings", 1, 1024),
            ("max_nodes", 1, 10000),
            ("max_depth", 1, 128),
        ):
            value = getattr(self, name)
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f"{name} must be an integer in [{low}, {high}]")
        if (
            type(self.seconds) not in {int, float}
            or not 0 <= self.seconds <= 3600
            or not math.isfinite(self.seconds)
        ):
            raise ValueError("seconds must be finite and in [0, 3600]")


DEFAULT_DERIVE_LIMITS = DeriveLimits()


@dataclass(frozen=True, slots=True)
class Derivation:
    target_id: str
    constant_bindings: tuple[tuple[str, int], ...]
    placeholders: tuple[tuple[str, str], ...]
    start: Expr
    endpoint: Expr
    steps: tuple[Step, ...]
    semantic_status: Literal["verified"] = "verified"
    scope: str = (
        "template for listed constants and opaque placeholders; no automatic whole-rule claim"
    )


@dataclass(frozen=True, slots=True)
class DeriveResult:
    status: Literal["found", "not-found-within-bounds", "partial"]
    witnesses: tuple[Derivation, ...]
    match_attempts: int
    states: int
    bindings_examined: int
    guard_rejections: int
    growth_exclusions: int
    solver_unknowns: int
    reason: str
    elapsed: float


def derive(
    target: Rule,
    rules: tuple[Rule, ...],
    limits: DeriveLimits = DEFAULT_DERIVE_LIMITS,
    constants: tuple[int, ...] = (0, 1, MASK),
    *,
    backend: ProofBackend | None = None,
    now: Callable[[], float] = perf_counter,
) -> DeriveResult:
    by_id = {rule.id: rule for rule in rules}
    if len(by_id) != len(rules) or by_id.get(target.id) != target:
        raise ValueError("rules must have unique IDs and contain the exact target rule")
    if not 1 <= len(constants) <= 16 or any(not valid_word(value) for value in constants):
        raise ValueError("constant domain must contain 1–16 unsigned 32-bit integers")
    if len(set(constants)) != len(constants):
        raise ValueError("constant domain must not contain duplicates")
    adapter = backend if backend is not None else Z3Backend()
    started = now()
    witnesses: list[Derivation] = []
    attempts = states = bindings_examined = guard_rejections = growth_exclusions = unknowns = 0

    def finish(
        status: Literal["found", "not-found-within-bounds", "partial"], reason: str = ""
    ) -> DeriveResult:
        return DeriveResult(
            status,
            tuple(witnesses),
            attempts,
            states,
            bindings_examined,
            guard_rejections,
            growth_exclusions,
            unknowns,
            reason,
            max(0.0, now() - started),
        )

    def expired() -> bool:
        return now() - started >= limits.seconds

    try:
        for rule in rules:
            if expired():
                return finish("partial", "time-limit during rule validation")
            validation = check_rule(rule, backend=adapter)
            if validation.status == "unknown":
                unknowns += 1
                return finish("partial", validation.reason)
            if validation.status != "verified":
                raise ValueError(f"rule {rule.id!r} is not usable: {validation.status}")
        variables = metavariables(target.lhs)
        constant_names = sorted(name for name, kind in variables.items() if kind == "const")
        expr_names = sorted(name for name, kind in variables.items() if kind == "expr")
        placeholders = tuple((name, f"_s{i}") for i, name in enumerate(expr_names))
        remaining = tuple(rule for rule in rules if rule.id != target.id)
        for index, values in enumerate(product(constants, repeat=len(constant_names))):
            if index >= limits.max_bindings:
                return finish("partial", "constant-binding-limit")
            if expired():
                return finish("partial", "time-limit")
            bindings_examined += 1
            bindings: dict[str, Expr] = {name: Var(symbol) for name, symbol in placeholders}
            binding_values = tuple(zip(constant_names, values, strict=True))
            bindings.update((name, Const(value)) for name, value in binding_values)
            if not all(guard.holds(bindings) for guard in target.guards):
                guard_rejections += 1
                continue
            start = substitute(target.lhs, bindings)
            endpoint = substitute(target.rhs, bindings)
            if not within_limits(start, limits.max_nodes, limits.max_depth):
                growth_exclusions += 1
                continue
            if states >= limits.max_states:
                return finish("partial", "search-state-limit")
            states += 1
            queue: deque[tuple[Expr, tuple[Step, ...]]] = deque([(start, ())])
            seen = {start}
            found = False
            while queue and not found:
                current, prefix = queue.popleft()
                for path, subtree in locations(current, "preorder"):
                    for rule in remaining:
                        if expired():
                            return finish("partial", "time-limit")
                        if attempts >= limits.max_match_attempts:
                            return finish("partial", "matching-attempt-limit")
                        attempts += 1
                        matched = match(rule.lhs, subtree)
                        if matched is None:
                            continue
                        guards = tuple(guard.holds(matched) for guard in rule.guards)
                        if not all(guards):
                            guard_rejections += 1
                            continue
                        replacement = substitute(rule.rhs, matched)
                        candidate = replace(current, path, replacement)
                        if not within_limits(candidate, limits.max_nodes, limits.max_depth):
                            growth_exclusions += 1
                            continue
                        step = Step(
                            rule.id,
                            path,
                            subtree,
                            replacement,
                            tuple(sorted(matched.items())),
                            guards,
                        )
                        steps = (*prefix, step)
                        is_new = candidate not in seen
                        if is_new:
                            if states >= limits.max_states:
                                return finish("partial", "search-state-limit")
                            states += 1
                            seen.add(candidate)
                        if candidate == endpoint:
                            obligations = [(item.before, item.after) for item in steps]
                            obligations.append((start, candidate))
                            for left, right in obligations:
                                if expired():
                                    return finish("partial", "time-limit during path validation")
                                proof = check_equivalence(left, right, backend=adapter)
                                if proof.status == "unknown":
                                    unknowns += 1
                                    return finish("partial", proof.reason)
                                if proof.status != "verified":
                                    raise ValueError(
                                        "instantiated derivation failed semantic validation"
                                    )
                            witnesses.append(
                                Derivation(
                                    target.id, binding_values, placeholders, start, candidate, steps
                                )
                            )
                            found = True
                            break
                        if is_new and len(steps) < limits.max_steps:
                            queue.append((candidate, steps))
                    if found:
                        break
        if witnesses:
            return finish("found")
        return finish("not-found-within-bounds", "bounded miss is inconclusive")
    except KeyboardInterrupt:
        return finish("partial", "interrupted")
