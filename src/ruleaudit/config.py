"""Strict, immutable single-run experiment settings."""

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal, cast

from ruleaudit.derive import DeriveLimits
from ruleaudit.io import InputError, JSONValue, load_json, object_fields
from ruleaudit.ir import MASK, valid_identifier, valid_word
from ruleaudit.rewrite import RunLimits, Schedule
from ruleaudit.solver import SolverLimits


@dataclass(frozen=True, slots=True)
class Generation:
    strategy: Literal["target"] = "target"
    seed: int = 0
    cases: int = 100
    attempts: int = 1000
    depth: int = 2
    constants: tuple[int, ...] = (0, 1, MASK)
    contexts: tuple[str, ...] = ("hole",)

    def __post_init__(self) -> None:
        for name, low, high in (
            ("seed", 0, 2**64 - 1),
            ("cases", 1, 10000),
            ("attempts", 0, 1000000),
            ("depth", 0, 4),
        ):
            value = getattr(self, name)
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f"{name} must be an integer in [{low}, {high}]")
        if self.strategy != "target" or self.contexts != ("hole",):
            raise ValueError("M3 supports target generation in the hole context")
        if not 1 <= len(self.constants) <= 16 or any(not valid_word(v) for v in self.constants):
            raise ValueError("constants must contain 1–16 unsigned 32-bit integers")
        if len(set(self.constants)) != len(self.constants):
            raise ValueError("constants must be unique")


@dataclass(frozen=True, slots=True)
class Config:
    schedule: Schedule
    run: RunLimits = RunLimits()
    search: DeriveLimits = DeriveLimits()
    generation: Generation = Generation()
    solver: SolverLimits = SolverLimits(max_calls=100000)
    seconds: float = 60.0
    max_output_bytes: int = 100 * 1024**2

    def __post_init__(self) -> None:
        if any(not valid_identifier(name) for name in self.schedule.priority):
            raise ValueError("priority entries must be ASCII identifiers of at most 64 characters")
        if type(self.seconds) not in {int, float} or not 0 <= self.seconds <= 3600:
            raise ValueError("seconds must be finite and in [0, 3600]")
        if type(self.max_output_bytes) is not int or not 8192 <= self.max_output_bytes <= 1024**3:
            raise ValueError("max_output_bytes must be an integer in [8192, 1073741824]")
        if len(self.schedule.priority) > 100 or len(set(self.schedule.priority)) != len(
            self.schedule.priority
        ):
            raise ValueError("priority must contain at most 100 unique IDs")


def config_document(config: Config) -> dict[str, JSONValue]:
    # JSON roundtrip deliberately converts immutable tuples into JSON arrays.
    from ruleaudit.io import canonical_bytes, parse_json

    data = {"schema_version": 1, **asdict(config)}
    return cast(
        dict[str, JSONValue], parse_json(canonical_bytes(cast(JSONValue, data)).decode("ascii"))
    )


def parse_config(value: JSONValue) -> Config:
    doc = object_fields(
        value,
        {
            "schema_version",
            "schedule",
            "run",
            "search",
            "generation",
            "solver",
            "seconds",
            "max_output_bytes",
        },
        "$",
    )
    if type(doc["schema_version"]) is not int or doc["schema_version"] != 1:
        raise InputError("$.schema_version", "unsupported configuration version")
    schedule = object_fields(doc["schedule"], {"traversal", "priority"}, "$.schedule")
    priorities = schedule["priority"]
    if not isinstance(priorities, list) or any(not isinstance(v, str) for v in priorities):
        raise InputError("$.schedule.priority", "expected an array of rule IDs")
    run = object_fields(doc["run"], set(RunLimits.__dataclass_fields__), "$.run")
    search = object_fields(doc["search"], set(DeriveLimits.__dataclass_fields__), "$.search")
    solver = object_fields(doc["solver"], set(SolverLimits.__dataclass_fields__), "$.solver")
    generation = object_fields(
        doc["generation"], set(Generation.__dataclass_fields__), "$.generation"
    )
    for name in ("constants", "contexts"):
        if not isinstance(generation[name], list):
            raise InputError(f"$.generation.{name}", "expected an array")
    try:
        return Config(
            Schedule(
                cast(Literal["preorder", "postorder"], schedule["traversal"]),
                tuple(cast(list[str], priorities)),
            ),
            RunLimits(**cast(dict[str, int], run)),
            DeriveLimits(**cast(dict[str, int], search)),
            Generation(
                cast(Literal["target"], generation["strategy"]),
                cast(int, generation["seed"]),
                cast(int, generation["cases"]),
                cast(int, generation["attempts"]),
                cast(int, generation["depth"]),
                tuple(cast(list[int], generation["constants"])),
                tuple(cast(list[str], generation["contexts"])),
            ),
            SolverLimits(**cast(dict[str, int], solver)),
            cast(float, doc["seconds"]),
            cast(int, doc["max_output_bytes"]),
        )
    except (ValueError, TypeError) as error:
        raise InputError("$", str(error)) from error


def load_config(path: Path) -> Config:
    return parse_config(load_json(path))
