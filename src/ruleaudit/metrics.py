"""Explicit denominators and cross-seed uniqueness; no inference from missing data."""

from dataclasses import asdict
from typing import cast

from ruleaudit.config import Config
from ruleaudit.io import JSONValue, content_hash


def rate(numerator: int, denominator: int) -> float | None:
    if (
        type(numerator) is not int
        or type(denominator) is not int
        or not 0 <= numerator <= denominator
    ):
        raise ValueError("rate requires nonnegative integer counts with numerator <= denominator")
    return numerator / denominator if denominator else None


def case_key(input_hash: str, target: str, corpus_hash: str, config: Config) -> str:
    return content_hash(
        {
            "input_hash": input_hash,
            "target": target,
            "corpus_hash": corpus_hash,
            "schedule": cast(dict[str, JSONValue], asdict(config.schedule)),
            "run": cast(dict[str, JSONValue], asdict(config.run)),
            "semantics": "bv32-total-tree-v1",
        }
    )
