"""Target-independent concrete input snapshots; only random generation is accessible."""

from collections.abc import Callable
from dataclasses import asdict
from typing import cast

from ruleaudit.config import Generation
from ruleaudit.generate import random_attempt
from ruleaudit.io import JSONValue, canonical_bytes, content_hash, expression_node, parse_json
from ruleaudit.ir import measure


def input_snapshot(
    generation: Generation, deadline: float, *, now: Callable[[], float]
) -> dict[str, JSONValue]:
    if generation.strategy != "random" or generation.contexts != ("hole",):
        raise ValueError("held-out input selection requires random generation and hole context")
    cases: list[JSONValue] = []
    seen: set[str] = set()
    attempts = duplicates = rejected = nodes = size = 0
    status, reason = "partial", "attempt-limit"
    try:
        for attempt in range(1, generation.attempts + 1):
            if now() >= deadline:
                reason = "overall-time-limit preparing held-out inputs"
                break
            attempts = attempt
            case = random_attempt(generation, attempt)
            if case is None:
                rejected += 1
                continue
            node = expression_node(case.expression)
            key = content_hash(node)
            if key in seen:
                duplicates += 1
                continue
            count = measure(case.expression).nodes
            row: dict[str, JSONValue] = {"attempt": attempt, "input": node, "input_hash": key}
            row_size = len(canonical_bytes(row)) + 1
            if nodes + count > 100000 or size + row_size > 8 * 1024**2:
                reason = "held-out input record limit"
                break
            cases.append(row)
            nodes += count
            size += row_size
            seen.add(key)
            if len(cases) == generation.cases:
                status, reason = "completed", "requested input count"
                break
    except KeyboardInterrupt:
        status, reason = "interrupted", "held-out input preparation interrupted"
    return {
        "schema_version": 1,
        "kind": "heldout-inputs",
        "seed": generation.seed,
        "generation": parse_json(
            canonical_bytes(cast(JSONValue, asdict(generation))).decode("ascii")
        ),
        "requested_cases": generation.cases,
        "status": status,
        "reason": reason,
        "attempts": attempts,
        "duplicates": duplicates,
        "rejections": rejected,
        "cases": cases,
    }
