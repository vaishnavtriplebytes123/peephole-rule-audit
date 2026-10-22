"""Ordered local shrinking; every accepted input retains independently checked evidence."""

from collections.abc import Callable, Iterator
from dataclasses import asdict, dataclass
from time import perf_counter
from typing import cast

from ruleaudit.audit import CheckedCorpus, audit_case
from ruleaudit.config import Config, parse_config
from ruleaudit.corpus import parse_corpus
from ruleaudit.derive import Derivation
from ruleaudit.io import (
    InputError,
    JSONValue,
    content_hash,
    expression_node,
    object_fields,
    parse_expression,
)
from ruleaudit.ir import Const, Expr, Var, children, measure, within_limits
from ruleaudit.records import (
    EncodingBudget,
    at_location,
    ground_alternative,
    paired_document,
    verify_template,
)
from ruleaudit.report import IncompleteError
from ruleaudit.rewrite import RunLimits, locations, replace
from ruleaudit.rules import Rule
from ruleaudit.solver import ProofBackend, SolverLimits, Z3Backend

METHOD = "ordered greedy local shrinking; no global minimum claim"


@dataclass(frozen=True, slots=True)
class ReductionConfig:
    max_attempts: int = 1000
    max_accepted: int = 64
    seconds: float = 60.0
    solver: SolverLimits = SolverLimits(max_calls=100000)
    max_output_bytes: int = 100 * 1024**2

    def __post_init__(self) -> None:
        for name, low, high in (
            ("max_attempts", 0, 10000),
            ("max_accepted", 0, 256),
            ("max_output_bytes", 8192, 1024**3),
        ):
            value = getattr(self, name)
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f"{name} must be an integer in [{low}, {high}]")
        if type(self.seconds) not in (int, float) or not 0 <= self.seconds <= 3600:
            raise ValueError("seconds must be finite and in [0, 3600]")


def reduction_config_document(settings: ReductionConfig) -> dict[str, JSONValue]:
    return {"schema_version": 1, **cast(dict[str, JSONValue], asdict(settings))}


def parse_reduction_config(value: JSONValue) -> ReductionConfig:
    doc = object_fields(
        value, {"schema_version", *ReductionConfig.__dataclass_fields__}, "reduction_config"
    )
    if type(doc["schema_version"]) is not int or doc["schema_version"] != 1:
        raise InputError(
            "reduction_config.schema_version", "unsupported reduction configuration version"
        )
    solver = object_fields(
        doc["solver"], set(SolverLimits.__dataclass_fields__), "reduction_config.solver"
    )
    try:
        return ReductionConfig(
            cast(int, doc["max_attempts"]),
            cast(int, doc["max_accepted"]),
            cast(float, doc["seconds"]),
            SolverLimits(**cast(dict[str, int], solver)),
            cast(int, doc["max_output_bytes"]),
        )
    except (ValueError, TypeError) as error:
        raise InputError("reduction_config", str(error)) from error


def reduction_measure(expression: Expr) -> tuple[int, int, int]:
    constants = variables = 0
    for _, node in locations(expression, "preorder"):
        if isinstance(node, Const):
            constants += node.value
        elif isinstance(node, Var):
            variables += sum(map(ord, node.name))
    return measure(expression).nodes, constants, variables


def _local_options(expression: Expr) -> Iterator[tuple[str, int, Expr]]:
    for index, child in enumerate(children(expression)):
        yield "subtree", index, child
    if not isinstance(expression, Const):
        yield "zero", 0, Const(0)
    else:
        for value in dict.fromkeys((0, 1, expression.value // 2)):
            if value < expression.value:
                yield "constant", value, Const(value)


def shrinks(expression: Expr) -> Iterator[tuple[dict[str, JSONValue], Expr]]:
    seen: set[Expr] = set()
    previous = reduction_measure(expression)
    for path, node in locations(expression, "preorder"):
        for kind, argument, replacement in _local_options(node):
            candidate = replace(expression, path, replacement)
            if candidate in seen or reduction_measure(candidate) >= previous:
                continue
            seen.add(candidate)
            yield {"kind": kind, "argument": argument, "location": list(path)}, candidate


def apply_shrink(expression: Expr, value: JSONValue) -> Expr:
    spec = object_fields(value, {"kind", "argument", "location"}, "shrink")
    path = spec["location"]
    if (
        not isinstance(path, list)
        or len(path) > 64
        or any(type(i) is not int or i not in (0, 1) for i in path)
        or type(spec["argument"]) is not int
    ):
        raise InputError("shrink", "invalid location or argument")
    location = tuple(cast(list[int], path))
    node = at_location(expression, location)
    for kind, argument, replacement in _local_options(node):
        if (spec["kind"], spec["argument"]) == (kind, argument):
            candidate = replace(expression, location, replacement)
            if reduction_measure(candidate) < reduction_measure(expression):
                return candidate
    raise InputError("shrink", "not an allowed strictly decreasing shrink")


def check_candidate(
    expression: Expr,
    target: Rule,
    checked: CheckedCorpus,
    config: Config,
    template: Derivation,
    backend: ProofBackend,
    *,
    now: Callable[[], float] = perf_counter,
) -> dict[str, JSONValue] | None:
    if not within_limits(expression, config.generation.max_nodes, config.generation.max_depth):
        return None
    budget = EncodingBudget()
    alternative = ground_alternative(
        template, expression, target, checked.corpus, config.run, backend, budget
    )
    if alternative is None:
        return None
    pair = audit_case(
        expression, target.id, checked, config.schedule, config.run, backend=backend, now=now
    )
    if (
        pair.semantic_status == "unknown"
        or not pair.with_target.completed
        or not pair.without_target.completed
    ):
        raise IncompleteError("reduction pair inconclusive")
    if not pair.comparable or pair.delta <= 0:
        return None
    return {
        "input": budget.expression(expression),
        "paired": paired_document(pair, budget),
        "alternative": alternative,
    }


def original_record(payload: dict[str, JSONValue]) -> dict[str, JSONValue]:
    return {key: payload[key] for key in ("input", "paired", "alternative")}


def reduce_witness(
    value: JSONValue, settings: ReductionConfig, *, now: Callable[[], float] = perf_counter
) -> dict[str, JSONValue]:
    from ruleaudit.replay import replay

    preparation_started = now()
    envelope = object_fields(value, {"schema_version", "kind", "payload", "sha256"}, "original")
    if (
        type(envelope["schema_version"]) is not int
        or envelope["schema_version"] != 1
        or envelope["kind"] != "removal-witness"
    ):
        raise InputError("original", "reduction requires an original version-1 removal witness")
    replay(value, now=now)
    payload = cast(dict[str, JSONValue], envelope["payload"])
    if payload["alternative"] is None:
        raise InputError("original.alternative", "reduction requires a checked alternative")
    corpus, config = parse_corpus(payload["corpus"]), parse_config(payload["config"])
    target = next(rule for rule in corpus.rules if rule.id == payload["target"])
    current = parse_expression({"schema_version": 1, "expression": payload["input"]})
    started = now()
    preparation_seconds = max(0.0, started - preparation_started)
    backend = Z3Backend(settings.solver, deadline=started + settings.seconds, now=now)
    attempts = 0
    state: tuple[Expr, dict[str, JSONValue], tuple[JSONValue, ...]] = (
        current,
        original_record(payload),
        (),
    )
    status, reason = "completed", "no-accepted-local-shrink"
    try:
        if settings.seconds == 0:
            raise IncompleteError("reduction-time-limit")
        if settings.max_attempts == 0:
            raise IncompleteError("reduction-attempt-limit")
        if settings.max_accepted == 0:
            raise IncompleteError("reduction-accepted-limit")
        alternative = cast(dict[str, JSONValue], payload["alternative"])
        template = verify_template(
            alternative["template"],
            target,
            corpus,
            RunLimits(
                h=2,
                max_nodes=config.search.max_nodes,
                max_depth=config.search.max_depth,
                seconds=config.search.seconds,
            ),
            backend,
        )
        while True:
            current, _, accepted = state
            if len(accepted) >= settings.max_accepted:
                raise IncompleteError("reduction-accepted-limit")
            improved = False
            for instruction, candidate in shrinks(current):
                if now() - started >= settings.seconds:
                    raise IncompleteError("reduction-time-limit")
                if attempts >= settings.max_attempts:
                    raise IncompleteError("reduction-attempt-limit")
                attempts += 1
                record = check_candidate(
                    candidate, target, CheckedCorpus(corpus), config, template, backend, now=now
                )
                if record is None:
                    continue
                step: dict[str, JSONValue] = {
                    "shrink": instruction,
                    "before_hash": content_hash(expression_node(current)),
                    "after_hash": content_hash(expression_node(candidate)),
                    "measure_before": list(reduction_measure(current)),
                    "measure_after": list(reduction_measure(candidate)),
                    "record": record,
                }
                # One assignment commits input, evidence and history together.
                state = (candidate, record, (*accepted, step))
                improved = True
                break
            if not improved:
                break
    except IncompleteError as error:
        status, reason = "partial", str(error)
    except KeyboardInterrupt:
        status, reason = "interrupted", "reduction interrupted; last verified input retained"
    current, best, accepted = state
    try:
        elapsed = max(0.0, now() - started)
    except KeyboardInterrupt:
        status, reason = "interrupted", "interrupted while finalizing; last verified input retained"
        elapsed = max(0.0, now() - started)
    result: dict[str, JSONValue] = {
        "original": value,
        "reduction_config": reduction_config_document(settings),
        "steps": list(accepted),
        "final": best,
        "status": status,
        "reason": reason,
        "attempts": attempts,
        "solver_calls": backend.calls,
        "preparation_seconds": preparation_seconds,
        "elapsed": elapsed,
        "method": METHOD,
    }
    return {
        "schema_version": 2,
        "kind": "reduced-removal-witness",
        "payload": result,
        "sha256": content_hash(result),
    }
