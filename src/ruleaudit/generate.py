"""Seeded baselines and explicit, syntactically checked overlap guidance."""

import hashlib
import random
from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import replace as updated
from typing import cast

from ruleaudit.config import Generation
from ruleaudit.derive import Derivation
from ruleaudit.ir import Binary, BinaryOp, Const, Expr, Unary, Var, children, within_limits
from ruleaudit.report import IncompleteError
from ruleaudit.rewrite import Location, RunLimits, Schedule, Step, locations, replace
from ruleaudit.rules import Rule, match, metavariables, substitute


@dataclass(frozen=True, slots=True)
class Context:
    kind: str = "hole"
    sibling: Expr | None = None

    @property
    def location(self) -> Location:
        if self.kind == "hole":
            return ()
        return (1,) if self.kind.endswith("-right") else (0,)

    def wrap(self, expression: Expr) -> Expr:
        if self.kind == "hole":
            return expression
        if self.kind == "not":
            return Unary("not", expression)
        assert self.sibling is not None
        op, side = self.kind.split("-")
        return (
            Binary(cast(BinaryOp, op), expression, self.sibling)
            if side == "left"
            else Binary(cast(BinaryOp, op), self.sibling, expression)
        )


@dataclass(frozen=True, slots=True)
class Guidance:
    template: Derivation
    target_location: Location
    prefix: tuple[Step, ...]
    intermediate: Expr
    expected_rule: str
    expected_location: Location
    competing: Step


@dataclass(frozen=True, slots=True)
class Case:
    expression: Expr
    strategy: str
    seed: int
    attempt: int
    bindings: tuple[tuple[str, Expr], ...]
    context: Context = Context()
    guidance: Guidance | None = None


@dataclass(frozen=True, slots=True)
class Generated:
    cases: tuple[Case, ...]
    attempts: int
    duplicates: int
    rejections: int
    completed: bool


class GuidanceBudget:
    def __init__(self, max_matches: int, *, allow_work: Callable[[], bool] = lambda: True) -> None:
        self.max_matches = max_matches
        self.allow_work = allow_work
        self.matches = 0

    def checkpoint(self) -> None:
        if not self.allow_work():
            raise IncompleteError("overall-time-limit")

    def match(self) -> None:
        self.checkpoint()
        if self.matches >= self.max_matches:
            raise IncompleteError("generation-match-limit")
        self.matches += 1


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
    return Binary(cast(BinaryOp, op), left, random_expression(rng, constants, depth - 1))


def _check_attempt(settings: Generation, attempt: int) -> None:
    if type(attempt) is not int or not 1 <= attempt <= settings.attempts:
        raise ValueError("attempt must be within the configured attempt budget")


def _context(settings: Generation, attempt: int) -> Context:
    kind = attempt_rng(settings.seed, settings.strategy, attempt, "context").choice(
        settings.contexts
    )
    sibling = None
    if kind not in {"hole", "not"}:
        sibling = random_expression(
            attempt_rng(settings.seed, settings.strategy, attempt, "sibling"),
            settings.constants,
            settings.depth,
        )
    return Context(kind, sibling)


def random_attempt(settings: Generation, attempt: int) -> Case | None:
    _check_attempt(settings, attempt)
    core = random_expression(
        attempt_rng(settings.seed, settings.strategy, attempt, "expression"),
        settings.constants,
        settings.depth,
    )
    context = _context(settings, attempt)
    expression = context.wrap(core)
    if not within_limits(expression, settings.max_nodes, settings.max_depth):
        return None
    return Case(expression, settings.strategy, settings.seed, attempt, (), context)


def target_attempt(target: Rule, settings: Generation, attempt: int) -> Case | None:
    _check_attempt(settings, attempt)
    rng = attempt_rng(settings.seed, settings.strategy, attempt, "bindings")
    bindings = {
        name: Const(rng.choice(settings.constants))
        if kind == "const"
        else random_expression(rng, settings.constants, settings.depth)
        for name, kind in sorted(metavariables(target.lhs).items())
    }
    if not all(guard.holds(bindings) for guard in target.guards):
        return None
    context = _context(settings, attempt)
    expression = context.wrap(substitute(target.lhs, bindings))
    if not within_limits(expression, settings.max_nodes, settings.max_depth):
        return None
    return Case(
        expression,
        settings.strategy,
        settings.seed,
        attempt,
        tuple(sorted(bindings.items())),
        context,
    )


def _at(expression: Expr, path: Location) -> Expr:
    for index in path:
        expression = children(expression)[index]
    return expression


def _apply(expression: Expr, rule: Rule, path: Location) -> tuple[Expr, Step] | None:
    try:
        before = _at(expression, path)
    except IndexError:
        return None
    bindings = match(rule.lhs, before)
    if bindings is None:
        return None
    guards = tuple(guard.holds(bindings) for guard in rule.guards)
    if not all(guards):
        return None
    after = substitute(rule.rhs, bindings)
    return replace(expression, path, after), Step(
        rule.id, path, before, after, tuple(sorted(bindings.items())), guards
    )


def guided_attempt(
    target: Rule,
    settings: Generation,
    attempt: int,
    templates: tuple[Derivation, ...],
    rules: tuple[Rule, ...],
    schedule: Schedule,
    limits: RunLimits,
    *,
    budget: GuidanceBudget | None = None,
) -> Case | None:
    work = budget if budget is not None else GuidanceBudget(settings.max_match_attempts)
    work.checkpoint()
    case = target_attempt(target, settings, attempt)
    if case is None:
        return None
    bindings = dict(case.bindings)
    by_id = {rule.id: rule for rule in rules if rule.id != target.id}
    ordered = tuple(by_id[name] for name in schedule.priority if name != target.id)
    for template in templates:
        work.checkpoint()
        if template.target_id != target.id or len(template.steps) != 2:
            continue
        if any(bindings.get(name) != Const(value) for name, value in template.constant_bindings):
            continue
        current, prefix = case.expression, []
        evidence: Guidance | None = None
        for index, declared in enumerate(template.steps):
            rule = by_id.get(declared.rule_id)
            if rule is None:
                break
            path = case.context.location + declared.location
            work.match()
            applied = _apply(current, rule, path)
            if applied is None or not within_limits(applied[0], limits.max_nodes, limits.max_depth):
                break
            current, step = applied
            prefix.append(step)
            if index == 0:
                expected = template.steps[1]
                expected_path = case.context.location + expected.location
                selected: Step | None = None
                matched = False
                for location, _ in locations(current, schedule.traversal):
                    for competitor in ordered:
                        work.match()
                        alternative = _apply(current, competitor, location)
                        if alternative is not None:
                            matched = True
                            # A growth-stopped first match cannot be a chosen rewrite hint.
                            if within_limits(alternative[0], limits.max_nodes, limits.max_depth):
                                selected = alternative[1]
                            break
                    if matched:
                        break
                if selected is not None and (selected.rule_id, selected.location) != (
                    expected.rule_id,
                    expected_path,
                ):
                    overlap = (
                        selected.location[: len(expected_path)] == expected_path
                        or expected_path[: len(selected.location)] == selected.location
                    )
                    if overlap:
                        evidence = Guidance(
                            template,
                            case.context.location,
                            tuple(prefix),
                            current,
                            expected.rule_id,
                            expected_path,
                            selected,
                        )
        else:
            endpoint = case.context.wrap(substitute(target.rhs, bindings))
            if current == endpoint and evidence is not None:
                return updated(case, guidance=evidence)
    return None


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
