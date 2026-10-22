"""Self-contained evidence replay: hashes never replace recomputation."""

from time import perf_counter
from typing import cast

from ruleaudit import __version__
from ruleaudit.audit import audit_case, check_corpus
from ruleaudit.config import parse_config
from ruleaudit.corpus import parse_corpus
from ruleaudit.generate import target_attempt
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


def replay(value: JSONValue) -> dict[str, JSONValue]:
    started = perf_counter()
    envelope = object_fields(value, {"schema_version", "kind", "payload", "sha256"}, "$")
    if type(envelope["schema_version"]) is not int or envelope["schema_version"] != 1:
        raise InputError("$.schema_version", "unsupported witness version")
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
    case = target_attempt(target, config.generation, attempt)
    if case is None or content_hash(case_document(case, EncodingBudget())) != content_hash(
        provenance
    ):
        raise InputError("provenance", "generation provenance mismatch")
    expression = parse_expression({"schema_version": 1, "expression": payload["input"]})
    if expression != case.expression:
        raise InputError("input", "input differs from regenerated candidate")
    backend = Z3Backend(config.solver, deadline=started + config.seconds)
    validation = check_corpus(corpus, backend=backend)
    if validation.status == "unknown":
        raise IncompleteError("corpus validation inconclusive during replay")
    if validation.checked is None:
        raise InputError("corpus", "corpus contains unusable rules")
    try:
        pair = audit_case(
            expression, target.id, validation.checked, config.schedule, config.run, backend=backend
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
