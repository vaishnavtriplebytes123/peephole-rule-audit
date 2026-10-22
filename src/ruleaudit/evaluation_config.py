"""Strict evaluation grid and independent deterministic schedule/trial ordering."""

import hashlib
import random
from collections.abc import Iterator
from dataclasses import dataclass, replace
from itertools import product
from typing import Literal, cast

from ruleaudit.config import Config, config_document, parse_config
from ruleaudit.corpus import Corpus
from ruleaudit.io import InputError, JSONValue, object_fields
from ruleaudit.ir import valid_identifier
from ruleaudit.reduce import ReductionConfig, parse_reduction_config, reduction_config_document
from ruleaudit.rewrite import Schedule
from ruleaudit.solver import SolverLimits


@dataclass(frozen=True, slots=True)
class EvaluationConfig:
    base: Config
    targets: tuple[str, ...]
    seeds: tuple[int, ...] = (0, 1, 2, 3, 4)
    h_values: tuple[int, ...] = (1, 2, 4, 8)
    traversals: tuple[Literal["preorder", "postorder"], ...] = ("preorder", "postorder")
    priorities: tuple[Literal["corpus", "permuted"], ...] = ("corpus",)
    permutation_seed: int = 1729
    order_seed: int = 2718
    max_trials: int = 10000
    seconds: float = 3600.0
    max_output_bytes: int = 512 * 1024**2
    reduce_per_trial: int = 1
    reduction: ReductionConfig = ReductionConfig(
        max_attempts=100, max_accepted=16, seconds=10.0, solver=SolverLimits(max_calls=1000)
    )

    def __post_init__(self) -> None:
        if (
            not 1 <= len(self.targets) <= 100
            or len(set(self.targets)) != len(self.targets)
            or any(not valid_identifier(v) for v in self.targets)
        ):
            raise ValueError("targets must contain 1–100 unique ASCII rule IDs")
        for name, values, maximum, ceiling in (
            ("seeds", self.seeds, 5, 2**64 - 1),
            ("h_values", self.h_values, 6, 10000),
        ):
            if (
                not 1 <= len(values) <= maximum
                or len(set(values)) != len(values)
                or any(type(v) is not int or not 0 <= v <= ceiling for v in values)
            ):
                raise ValueError(f"{name} must contain unique bounded integers")
        for name, choices, allowed in (
            ("traversals", self.traversals, {"preorder", "postorder"}),
            ("priorities", self.priorities, {"corpus", "permuted"}),
        ):
            if (
                not choices
                or len(set(choices)) != len(choices)
                or any(v not in allowed for v in choices)
            ):
                raise ValueError(f"invalid {name}")
        for name, low, high in (
            ("permutation_seed", 0, 2**64 - 1),
            ("order_seed", 0, 2**64 - 1),
            ("max_trials", 0, 10000),
            ("max_output_bytes", 8192, 1024**3),
            ("reduce_per_trial", 0, 100),
        ):
            value = getattr(self, name)
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f"{name} must be an integer in [{low}, {high}]")
        if type(self.seconds) not in (int, float) or not 0 <= self.seconds <= 86400:
            raise ValueError("seconds must be finite and in [0, 86400]")

    @property
    def expected_trials(self) -> int:
        return (
            len(self.targets)
            * len(self.seeds)
            * len(self.h_values)
            * len(self.traversals)
            * len(self.priorities)
            * 3
        )


@dataclass(frozen=True, slots=True)
class Trial:
    target: str
    config: Config


def evaluation_document(settings: EvaluationConfig) -> dict[str, JSONValue]:
    return {
        "schema_version": 1,
        "kind": "evaluation",
        "base": config_document(settings.base),
        "targets": list(settings.targets),
        "seeds": list(settings.seeds),
        "h_values": list(settings.h_values),
        "traversals": list(settings.traversals),
        "priorities": list(settings.priorities),
        "permutation_seed": settings.permutation_seed,
        "order_seed": settings.order_seed,
        "max_trials": settings.max_trials,
        "seconds": settings.seconds,
        "max_output_bytes": settings.max_output_bytes,
        "reduce_per_trial": settings.reduce_per_trial,
        "reduction": reduction_config_document(settings.reduction),
    }


def parse_evaluation_config(value: JSONValue) -> EvaluationConfig:
    doc = object_fields(
        value,
        {"schema_version", "kind", *EvaluationConfig.__dataclass_fields__},
        "evaluation_config",
    )
    if (
        type(doc["schema_version"]) is not int
        or doc["schema_version"] != 1
        or doc["kind"] != "evaluation"
    ):
        raise InputError("evaluation_config", "unsupported version or kind")
    for key in ("targets", "seeds", "h_values", "traversals", "priorities"):
        if not isinstance(doc[key], list):
            raise InputError(f"evaluation_config.{key}", "expected an array")
    try:
        return EvaluationConfig(
            base=parse_config(doc["base"]),
            targets=tuple(cast(list[str], doc["targets"])),
            seeds=tuple(cast(list[int], doc["seeds"])),
            h_values=tuple(cast(list[int], doc["h_values"])),
            traversals=tuple(cast(list[Literal["preorder", "postorder"]], doc["traversals"])),
            priorities=tuple(cast(list[Literal["corpus", "permuted"]], doc["priorities"])),
            permutation_seed=cast(int, doc["permutation_seed"]),
            order_seed=cast(int, doc["order_seed"]),
            max_trials=cast(int, doc["max_trials"]),
            seconds=cast(float, doc["seconds"]),
            max_output_bytes=cast(int, doc["max_output_bytes"]),
            reduce_per_trial=cast(int, doc["reduce_per_trial"]),
            reduction=parse_reduction_config(doc["reduction"]),
        )
    except (ValueError, TypeError) as error:
        raise InputError("evaluation_config", str(error)) from error


def _rng(domain: str, seed: int) -> random.Random:
    return random.Random(
        int.from_bytes(hashlib.sha256(f"{domain}:{seed}".encode("ascii")).digest(), "big")
    )


def validate_evaluation(corpus: Corpus, settings: EvaluationConfig) -> tuple[str, ...]:
    ids = tuple(rule.id for rule in corpus.rules)
    if settings.base.schedule.priority != ids:
        raise InputError("base.schedule.priority", "must equal corpus order")
    if any(target not in ids for target in settings.targets):
        raise InputError("targets", "unknown target ID")
    return ids


def trials(corpus: Corpus, settings: EvaluationConfig) -> Iterator[Trial]:
    ids = validate_evaluation(corpus, settings)
    permuted = list(ids)
    _rng("priority", settings.permutation_seed).shuffle(permuted)
    priorities = {"corpus": ids, "permuted": tuple(permuted)}
    strategies: tuple[Literal["random", "target", "guided"], ...] = ("random", "target", "guided")
    descriptors = list(
        product(
            settings.targets,
            settings.seeds,
            settings.h_values,
            settings.traversals,
            settings.priorities,
            strategies,
        )
    )
    _rng("order", settings.order_seed).shuffle(descriptors)
    for target, seed, h, traversal, priority, strategy in descriptors:
        yield Trial(
            target,
            replace(
                settings.base,
                schedule=Schedule(traversal, priorities[priority]),
                run=replace(settings.base.run, h=h),
                generation=replace(settings.base.generation, seed=seed, strategy=strategy),
            ),
        )
