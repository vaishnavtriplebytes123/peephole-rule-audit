"""Checked corpora and exactly paired bounded optimizer executions."""

from collections.abc import Callable
from dataclasses import dataclass
from time import perf_counter

from ruleaudit.corpus import Corpus
from ruleaudit.ir import Expr, measure, within_limits
from ruleaudit.rewrite import RunLimits, RunResult, Schedule, run
from ruleaudit.solver import (
    ProofBackend,
    ValidationResult,
    Z3Backend,
    check_equivalence,
    check_rule,
)


@dataclass(frozen=True, slots=True)
class CheckedCorpus:
    corpus: Corpus


@dataclass(frozen=True, slots=True)
class CorpusValidation:
    status: str
    results: tuple[tuple[str, ValidationResult], ...]
    checked: CheckedCorpus | None


def check_corpus(corpus: Corpus, *, backend: ProofBackend | None = None) -> CorpusValidation:
    adapter = backend if backend is not None else Z3Backend()
    results = tuple((rule.id, check_rule(rule, backend=adapter)) for rule in corpus.rules)
    if any(result.status not in {"verified", "unknown"} for _, result in results):
        return CorpusValidation("invalid", results, None)
    if any(result.status == "unknown" for _, result in results):
        return CorpusValidation("unknown", results, None)
    return CorpusValidation("verified", results, CheckedCorpus(corpus))


@dataclass(frozen=True, slots=True)
class PairedResult:
    input: Expr
    target_id: str
    with_target: RunResult
    without_target: RunResult
    without_priority: tuple[str, ...]
    cost_with: int
    cost_without: int
    delta: int
    semantic_status: str
    comparable: bool


def audit_case(
    expression: Expr,
    target_id: str,
    checked: CheckedCorpus,
    schedule: Schedule,
    limits: RunLimits,
    *,
    backend: ProofBackend | None = None,
    now: Callable[[], float] = perf_counter,
) -> PairedResult:
    rules = checked.corpus.rules
    if sum(rule.id == target_id for rule in rules) != 1:
        raise ValueError("target must identify exactly one corpus rule")
    if not within_limits(expression, 1000, 64):
        raise ValueError("input exceeds expression limits")
    without_priority = tuple(name for name in schedule.priority if name != target_id)
    with_target = run(expression, rules, schedule, limits, now=now)
    if with_target.stop_reason == "interrupted":
        raise KeyboardInterrupt
    without_target = run(
        expression,
        tuple(r for r in rules if r.id != target_id),
        Schedule(schedule.traversal, without_priority),
        limits,
        now=now,
    )
    if without_target.stop_reason == "interrupted":
        raise KeyboardInterrupt
    adapter = backend if backend is not None else Z3Backend()
    proofs = (
        check_equivalence(expression, with_target.output, backend=adapter),
        check_equivalence(expression, without_target.output, backend=adapter),
    )
    semantic = (
        "invalid"
        if any(p.status == "invalid" for p in proofs)
        else ("unknown" if any(p.status != "verified" for p in proofs) else "verified")
    )
    cost_with, cost_without = (
        measure(with_target.output).operators,
        measure(without_target.output).operators,
    )
    return PairedResult(
        expression,
        target_id,
        with_target,
        without_target,
        without_priority,
        cost_with,
        cost_without,
        cost_without - cost_with,
        semantic,
        semantic == "verified" and with_target.completed and without_target.completed,
    )
