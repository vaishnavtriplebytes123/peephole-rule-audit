"""Self-contained evidence replay: hashes never replace recomputation."""

from collections.abc import Callable
from time import perf_counter
from typing import cast

from ruleaudit import __version__
from ruleaudit.audit import audit_case, check_corpus
from ruleaudit.config import parse_config
from ruleaudit.corpus import parse_corpus
from ruleaudit.generate import GuidanceBudget, guided_attempt, random_attempt, target_attempt
from ruleaudit.io import InputError, JSONValue, content_hash, object_fields, parse_expression
from ruleaudit.records import (
    EncodingBudget,
    case_document,
    ground_alternative,
    paired_document,
    verify_template,
)
from ruleaudit.report import IncompleteError
from ruleaudit.rewrite import RunLimits
from ruleaudit.solver import Z3Backend


def _semantic_pair(value: JSONValue) -> dict[str, JSONValue]:
    pair = object_fields(
        value,
        {
            "with_target",
            "without_target",
            "without_priority",
            "delta",
            "semantic_status",
            "comparable",
        },
        "paired",
    )
    result = dict(pair)
    for name in ("with_target", "without_target"):
        arm = object_fields(
            pair[name],
            {"output", "cost", "stop_reason", "completed", "trace", "elapsed"},
            f"paired.{name}",
        )
        elapsed = arm["elapsed"]
        if type(elapsed) not in (int, float) or not 0 <= cast(float, elapsed) <= 86400:
            raise InputError(f"paired.{name}.elapsed", "invalid elapsed metadata")
        result[name] = {key: item for key, item in arm.items() if key != "elapsed"}
    return result


def replay(value: JSONValue, *, now: Callable[[], float] = perf_counter) -> dict[str, JSONValue]:
    started = now()
    envelope = object_fields(value, {"schema_version", "kind", "payload", "sha256"}, "$")
    if type(envelope["schema_version"]) is not int or envelope["schema_version"] not in (1, 2):
        raise InputError("$.schema_version", "unsupported witness version")
    if envelope["schema_version"] == 2:
        return _replay_reduced(envelope, now=now)
    if envelope["kind"] != "removal-witness":
        raise InputError("$.kind", "expected removal-witness")
    if content_hash(envelope["payload"]) != envelope["sha256"]:
        raise InputError("$.sha256", "witness payload hash mismatch")
    payload = object_fields(
        envelope["payload"],
        {
            "tool_version",
            "environment",
            "corpus",
            "corpus_hash",
            "config",
            "config_hash",
            "target",
            "input",
            "provenance",
            "paired",
            "alternative",
        },
        "$.payload",
    )
    if payload["tool_version"] != __version__:
        raise InputError("tool_version", "unsupported producer tool version")
    environment = object_fields(payload["environment"], {"python", "z3-solver"}, "environment")
    if any(not isinstance(item, str) or not 1 <= len(item) <= 128 for item in environment.values()):
        raise InputError("environment", "invalid producer version metadata")
    for key in ("corpus", "config"):
        if content_hash(payload[key]) != payload[f"{key}_hash"]:
            raise InputError(f"{key}_hash", "snapshot hash mismatch")
    corpus, config = parse_corpus(payload["corpus"]), parse_config(payload["config"])
    target = next((rule for rule in corpus.rules if rule.id == payload["target"]), None)
    if target is None:
        raise InputError("target", "unknown target")
    provenance = object_fields(
        payload["provenance"],
        {"strategy", "seed", "attempt", "bindings", "context", "guidance"},
        "provenance",
    )
    attempt = provenance["attempt"]
    if type(attempt) is not int or not 1 <= attempt <= config.generation.attempts:
        raise InputError("provenance.attempt", "attempt is outside generation limits")
    backend = Z3Backend(config.solver, deadline=started + config.seconds, now=now)
    validation = check_corpus(corpus, backend=backend)
    if validation.status == "unknown":
        raise IncompleteError("corpus validation inconclusive during replay")
    if validation.checked is None:
        raise InputError("corpus", "corpus contains unusable rules")
    if config.generation.strategy == "random":
        case = random_attempt(config.generation, attempt)
    elif config.generation.strategy == "target":
        case = target_attempt(target, config.generation, attempt)
    else:
        guidance = object_fields(
            provenance["guidance"],
            {
                "template",
                "target_location",
                "prefix",
                "intermediate",
                "expected_rule",
                "expected_location",
                "competing",
            },
            "provenance.guidance",
        )
        template = verify_template(
            guidance["template"],
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
        if len(template.steps) > config.search.max_steps or any(
            value not in config.generation.constants for _, value in template.constant_bindings
        ):
            raise InputError("provenance.guidance", "template exceeds declared search scope")
        case = guided_attempt(
            target,
            config.generation,
            attempt,
            (template,),
            corpus.rules,
            config.schedule,
            config.run,
            budget=GuidanceBudget(
                config.generation.max_match_attempts,
                allow_work=lambda: now() < started + config.seconds,
            ),
        )
    if case is None or content_hash(case_document(case, EncodingBudget())) != content_hash(
        provenance
    ):
        raise InputError("provenance", "generation provenance mismatch")
    expression = parse_expression({"schema_version": 1, "expression": payload["input"]})
    if expression != case.expression:
        raise InputError("input", "input differs from regenerated candidate")
    try:
        pair = audit_case(
            expression,
            target.id,
            validation.checked,
            config.schedule,
            config.run,
            backend=backend,
            now=now,
        )
    except ValueError as error:
        raise InputError("paired", str(error)) from error
    if (
        pair.semantic_status == "unknown"
        or not pair.with_target.completed
        or not pair.without_target.completed
    ):
        raise IncompleteError("recomputed pair is inconclusive")
    if not pair.comparable or pair.delta <= 0:
        raise InputError("paired", "recomputed input is not an eligible regression")
    actual = paired_document(pair, EncodingBudget())
    if content_hash(_semantic_pair(actual)) != content_hash(_semantic_pair(payload["paired"])):
        raise InputError("paired", "recomputed trace, cost or stop reason mismatch")
    alternative = payload["alternative"]
    if alternative is not None:
        alt = object_fields(
            alternative,
            {
                "template",
                "target_location",
                "steps",
                "endpoint",
                "target_guards",
                "scope",
                "semantic_status",
            },
            "alternative",
        )
        search_limits = RunLimits(
            h=2,
            max_nodes=config.search.max_nodes,
            max_depth=config.search.max_depth,
            seconds=config.search.seconds,
        )
        template = verify_template(alt["template"], target, corpus, search_limits, backend)
        if len(template.steps) > config.search.max_steps or any(
            value not in config.generation.constants for _, value in template.constant_bindings
        ):
            raise InputError("alternative.template", "template exceeds declared search scope")
        recomputed = ground_alternative(
            template, expression, target, corpus, config.run, backend, EncodingBudget()
        )
        if recomputed is None or content_hash(recomputed) != content_hash(alternative):
            raise InputError("alternative", "recomputed ground alternative mismatch")
    return {
        "schema_version": 1,
        "status": "verified",
        "witness_hash": envelope["sha256"],
        "delta": pair.delta,
        "alternative_checked": alternative is not None,
    }


def _record_semantics(value: JSONValue) -> dict[str, JSONValue]:
    record = object_fields(value, {"input", "paired", "alternative"}, "reduction.record")
    return {**record, "paired": _semantic_pair(record["paired"])}


def _replay_reduced(
    envelope: dict[str, JSONValue], *, now: Callable[[], float]
) -> dict[str, JSONValue]:
    from ruleaudit.audit import CheckedCorpus
    from ruleaudit.ir import measure
    from ruleaudit.reduce import (
        METHOD,
        apply_shrink,
        check_candidate,
        original_record,
        parse_reduction_config,
        reduction_measure,
    )

    if envelope["kind"] != "reduced-removal-witness":
        raise InputError("kind", "schema version 2 requires reduced-removal-witness")
    if content_hash(envelope["payload"]) != envelope["sha256"]:
        raise InputError("sha256", "reduction payload hash mismatch")
    doc = object_fields(
        envelope["payload"],
        {
            "original",
            "reduction_config",
            "steps",
            "final",
            "status",
            "reason",
            "attempts",
            "solver_calls",
            "preparation_seconds",
            "elapsed",
            "method",
        },
        "reduction",
    )
    original = object_fields(
        doc["original"], {"schema_version", "kind", "payload", "sha256"}, "original"
    )
    if type(original["schema_version"]) is not int or original["schema_version"] != 1:
        raise InputError(
            "original", "expected an original version-1 witness; nesting is not supported"
        )
    replay(original, now=now)
    origin = cast(dict[str, JSONValue], original["payload"])
    if origin["alternative"] is None:
        raise InputError("original.alternative", "checked alternative required")
    settings = parse_reduction_config(doc["reduction_config"])
    steps = doc["steps"]
    if not isinstance(steps, list) or len(steps) > settings.max_accepted:
        raise InputError("reduction.steps", "invalid accepted-step count")
    for key, low, high in (
        ("attempts", len(steps), settings.max_attempts),
        ("solver_calls", 0, settings.solver.max_calls),
    ):
        if type(doc[key]) is not int or not low <= cast(int, doc[key]) <= high:
            raise InputError(f"reduction.{key}", "counter exceeds declared bounds")
    for key in ("elapsed", "preparation_seconds"):
        if type(doc[key]) not in (int, float) or not 0 <= cast(float, doc[key]) <= 86400:
            raise InputError(f"reduction.{key}", "invalid timing metadata")
    if (
        doc["status"] not in ("completed", "partial", "interrupted")
        or not isinstance(doc["reason"], str)
        or not 1 <= len(doc["reason"]) <= 1024
        or doc["method"] != METHOD
    ):
        raise InputError("reduction", "invalid status, reason or method")
    corpus, config = parse_corpus(origin["corpus"]), parse_config(origin["config"])
    target = next(rule for rule in corpus.rules if rule.id == origin["target"])
    current = parse_expression({"schema_version": 1, "expression": origin["input"]})
    best = original_record(origin)
    backend = Z3Backend(settings.solver, deadline=now() + settings.seconds, now=now)
    if steps:
        alternative = cast(dict[str, JSONValue], origin["alternative"])
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
        for index, value in enumerate(steps):
            step = object_fields(
                value,
                {
                    "shrink",
                    "before_hash",
                    "after_hash",
                    "measure_before",
                    "measure_after",
                    "record",
                },
                f"reduction.steps[{index}]",
            )
            candidate = apply_shrink(current, step["shrink"])
            from ruleaudit.io import expression_node

            expected: dict[str, JSONValue] = {
                "before_hash": content_hash(expression_node(current)),
                "after_hash": content_hash(expression_node(candidate)),
                "measure_before": list(reduction_measure(current)),
                "measure_after": list(reduction_measure(candidate)),
            }
            if any(content_hash(step[key]) != content_hash(item) for key, item in expected.items()):
                raise InputError("reduction.step", "input hash or decreasing measure mismatch")
            record = check_candidate(
                candidate, target, CheckedCorpus(corpus), config, template, backend, now=now
            )
            if record is None:
                raise InputError(
                    "reduction.step", "candidate loses regression or checked target path"
                )
            if content_hash(_record_semantics(record)) != content_hash(
                _record_semantics(step["record"])
            ):
                raise InputError(
                    "reduction.record", "recomputed input, pair or alternative mismatch"
                )
            current, best = candidate, cast(dict[str, JSONValue], step["record"])
    if content_hash(doc["final"]) != content_hash(best):
        raise InputError("reduction.final", "final record differs from last verified input")
    pair = cast(dict[str, JSONValue], best["paired"])
    return {
        "schema_version": 1,
        "status": "verified",
        "witness_hash": envelope["sha256"],
        "delta": pair["delta"],
        "alternative_checked": True,
        "reduction_status": doc["status"],
        "reduced_nodes": measure(current).nodes,
    }
