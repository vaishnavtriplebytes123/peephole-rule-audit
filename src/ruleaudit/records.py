"""Plain-data evidence encoding and independently checked concrete alternatives."""

import platform
from importlib.metadata import version
from time import perf_counter
from typing import cast

from ruleaudit import __version__
from ruleaudit.audit import PairedResult
from ruleaudit.config import Config, config_document
from ruleaudit.corpus import Corpus, corpus_document
from ruleaudit.derive import Derivation
from ruleaudit.generate import Case
from ruleaudit.io import InputError, JSONValue, content_hash, expression_node, object_fields
from ruleaudit.ir import (
    Const,
    Expr,
    Var,
    children,
    measure,
    valid_word,
    within_limits,
)
from ruleaudit.report import IncompleteError
from ruleaudit.rewrite import Location, RunLimits, RunResult, Step, locations, replace
from ruleaudit.rules import Rule, match, metavariables, substitute
from ruleaudit.solver import ProofBackend, Z3Backend, check_equivalence


class EncodingBudget:
    def __init__(self) -> None:
        self.remaining = 100000

    def expression(self, expression: Expr) -> dict[str, JSONValue]:
        nodes = measure(expression).nodes
        if nodes > self.remaining:
            raise IncompleteError("serialized-expression-node-limit")
        self.remaining -= nodes
        return expression_node(expression)


def step_document(step: Step, budget: EncodingBudget) -> dict[str, JSONValue]:
    return {
        "rule_id": step.rule_id,
        "location": list(step.location),
        "before": budget.expression(step.before),
        "after": budget.expression(step.after),
        "bindings": {name: budget.expression(expr) for name, expr in step.bindings},
        "guards": list(step.guards),
    }


def run_document(result: RunResult, budget: EncodingBudget) -> dict[str, JSONValue]:
    return {
        "output": budget.expression(result.output),
        "cost": measure(result.output).operators,
        "stop_reason": result.stop_reason,
        "completed": result.completed,
        "trace": [step_document(step, budget) for step in result.trace],
        "elapsed": result.elapsed,
    }


def paired_document(pair: PairedResult, budget: EncodingBudget) -> dict[str, JSONValue]:
    return {
        "with_target": run_document(pair.with_target, budget),
        "without_target": run_document(pair.without_target, budget),
        "without_priority": list(pair.without_priority),
        "delta": pair.delta,
        "semantic_status": pair.semantic_status,
        "comparable": pair.comparable,
    }


def case_document(case: Case, budget: EncodingBudget) -> dict[str, JSONValue]:
    return {
        "strategy": case.strategy,
        "seed": case.seed,
        "attempt": case.attempt,
        "bindings": {name: budget.expression(expr) for name, expr in case.bindings},
        "context": {"kind": "hole"},
        "guidance": None,
    }


def derivation_document(
    template: Derivation, budget: EncodingBudget | None = None
) -> dict[str, JSONValue]:
    budget = budget if budget is not None else EncodingBudget()
    return {
        "target_id": template.target_id,
        "constant_bindings": dict(template.constant_bindings),
        "placeholders": dict(template.placeholders),
        "start": budget.expression(template.start),
        "endpoint": budget.expression(template.endpoint),
        "steps": [step_document(step, budget) for step in template.steps],
        "semantic_status": template.semantic_status,
        "scope": template.scope,
    }


def at_location(expression: Expr, location: Location) -> Expr:
    current = expression
    for index in location:
        operands = children(current)
        if index < 0 or index >= len(operands):
            raise InputError("alternative.location", "invalid tree location")
        current = operands[index]
    return current


def _path_specs(value: JSONValue) -> tuple[tuple[str, Location], ...]:
    if not isinstance(value, list) or not 1 <= len(value) <= 2:
        raise InputError("alternative.steps", "expected 1 or 2 steps")
    specs: list[tuple[str, Location]] = []
    for item in value:
        step = object_fields(
            item,
            {"rule_id", "location", "before", "after", "bindings", "guards"},
            "alternative.steps",
        )
        path = step["location"]
        if (
            not isinstance(step["rule_id"], str)
            or not isinstance(path, list)
            or len(path) > 128
            or any(type(i) is not int or i not in (0, 1) for i in path)
        ):
            raise InputError("alternative.steps", "invalid rule ID or location")
        specs.append((step["rule_id"], tuple(cast(list[int], path))))
    return tuple(specs)


def check_path(
    start: Expr,
    specs: tuple[tuple[str, Location], ...],
    target_id: str,
    corpus: Corpus,
    limits: RunLimits,
    backend: ProofBackend,
) -> tuple[Expr, tuple[Step, ...]]:
    by_id = {rule.id: rule for rule in corpus.rules}
    current = start
    steps: list[Step] = []
    if not 1 <= len(specs) <= 2:
        raise InputError("alternative.steps", "expected 1 or 2 steps")
    for rule_id, path in specs:
        if rule_id == target_id or rule_id not in by_id:
            raise InputError("alternative.steps", "target reuse or unknown rule")
        rule = by_id[rule_id]
        before = at_location(current, path)
        bindings = match(rule.lhs, before)
        if bindings is None:
            raise InputError("alternative.steps", "rule does not match")
        guards = tuple(guard.holds(bindings) for guard in rule.guards)
        if not all(guards):
            raise InputError("alternative.steps", "guard does not hold")
        after = substitute(rule.rhs, bindings)
        proof = check_equivalence(before, after, backend=backend)
        if proof.status == "unknown":
            raise IncompleteError(proof.reason)
        if proof.status != "verified":
            raise InputError("alternative.steps", "invalid step semantics")
        current = replace(current, path, after)
        if not within_limits(current, limits.max_nodes, limits.max_depth):
            raise InputError("alternative.steps", "growth limit exceeded")
        steps.append(Step(rule_id, path, before, after, tuple(sorted(bindings.items())), guards))
    proof = check_equivalence(start, current, backend=backend)
    if proof.status == "unknown":
        raise IncompleteError(proof.reason)
    if proof.status != "verified":
        raise InputError("alternative", "invalid endpoint semantics")
    return current, tuple(steps)


def verify_template(
    value: JSONValue, target: Rule, corpus: Corpus, limits: RunLimits, backend: ProofBackend
) -> Derivation:
    doc = object_fields(
        value,
        {
            "target_id",
            "constant_bindings",
            "placeholders",
            "start",
            "endpoint",
            "steps",
            "semantic_status",
            "scope",
        },
        "alternative.template",
    )
    variables = metavariables(target.lhs)
    names = sorted(name for name, kind in variables.items() if kind == "const")
    constants = object_fields(doc["constant_bindings"], set(names), "alternative.constant_bindings")
    if any(not valid_word(value) for value in constants.values()):
        raise InputError("alternative.constant_bindings", "invalid constant")
    placeholders = tuple(
        (name, f"_s{i}")
        for i, name in enumerate(sorted(name for name, kind in variables.items() if kind == "expr"))
    )
    bindings: dict[str, Expr] = {name: Var(symbol) for name, symbol in placeholders}
    bindings.update((name, Const(cast(int, value))) for name, value in constants.items())
    if not all(guard.holds(bindings) for guard in target.guards):
        raise InputError("alternative.template", "target guard does not hold")
    start = substitute(target.lhs, bindings)
    if not within_limits(start, limits.max_nodes, limits.max_depth):
        raise InputError("alternative.template", "start exceeds declared search growth limits")
    endpoint, steps = check_path(
        start, _path_specs(doc["steps"]), target.id, corpus, limits, backend
    )
    if endpoint != substitute(target.rhs, bindings):
        raise InputError("alternative.template", "structural endpoint mismatch")
    result = Derivation(
        target.id,
        tuple((name, cast(int, constants[name])) for name in names),
        placeholders,
        start,
        endpoint,
        steps,
    )
    if content_hash(derivation_document(result)) != content_hash(value):
        raise InputError("alternative.template", "template trace or scope mismatch")
    return result


def ground_alternative(
    template: Derivation,
    expression: Expr,
    target: Rule,
    corpus: Corpus,
    limits: RunLimits,
    backend: ProofBackend,
    budget: EncodingBudget,
) -> dict[str, JSONValue] | None:
    for target_path, subtree in locations(expression, "preorder"):
        bound = match(target.lhs, subtree)
        if bound is None or not all(guard.holds(bound) for guard in target.guards):
            continue
        if any(bound.get(name) != Const(value) for name, value in template.constant_bindings):
            continue
        specs = tuple((step.rule_id, (*target_path, *step.location)) for step in template.steps)
        try:
            endpoint, steps = check_path(expression, specs, target.id, corpus, limits, backend)
        except InputError:
            continue
        expected = replace(expression, target_path, substitute(target.rhs, bound))
        if endpoint != expected:
            continue
        return {
            "template": derivation_document(template, budget),
            "target_location": list(target_path),
            "steps": [step_document(step, budget) for step in steps],
            "endpoint": budget.expression(endpoint),
            "target_guards": [g.holds(bound) for g in target.guards],
            "scope": "ground input instance",
            "semantic_status": "verified",
        }
    return None


def make_witness(
    corpus: Corpus,
    config: Config,
    case: Case,
    pair: PairedResult,
    templates: tuple[Derivation, ...] = (),
    *,
    backend: ProofBackend | None = None,
) -> dict[str, JSONValue]:
    if not pair.comparable or pair.delta <= 0 or pair.input != case.expression:
        raise ValueError("witness requires a comparable positive regression on the same input")
    budget = EncodingBudget()
    adapter = (
        backend
        if backend is not None
        else Z3Backend(config.solver, deadline=perf_counter() + config.seconds)
    )
    target = next(rule for rule in corpus.rules if rule.id == pair.target_id)
    alternative: JSONValue = None
    for template in templates:
        if template.target_id == target.id:
            alternative = ground_alternative(
                template, case.expression, target, corpus, config.run, adapter, budget
            )
            if alternative is not None:
                break
    corpus_data, config_data = corpus_document(corpus), config_document(config)
    payload: dict[str, JSONValue] = {
        "tool_version": __version__,
        "environment": {"python": platform.python_version(), "z3-solver": version("z3-solver")},
        "corpus": corpus_data,
        "corpus_hash": content_hash(corpus_data),
        "config": config_data,
        "config_hash": content_hash(config_data),
        "target": target.id,
        "input": budget.expression(case.expression),
        "provenance": case_document(case, budget),
        "paired": paired_document(pair, budget),
        "alternative": alternative,
    }
    return {
        "schema_version": 1,
        "kind": "removal-witness",
        "payload": payload,
        "sha256": content_hash(payload),
    }
