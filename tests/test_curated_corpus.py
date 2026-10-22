import json
from pathlib import Path

from ruleaudit.corpus import load_corpus, pattern_node
from ruleaudit.io import canonical_bytes
from ruleaudit.solver import check_rule

ROOT = Path(__file__).resolve().parents[1]


def test_source_rules_are_attributed_and_semantically_verified() -> None:
    corpus = load_corpus(ROOT / "corpus/jog.json")
    assert corpus.kind == "source"
    assert len(corpus.rules) == 26
    for rule in corpus.rules:
        assert rule.provenance is not None
        assert rule.provenance.revision == "3011b9de21eae081448517fc77a85f4e8d5113d0"
        assert rule.provenance.source_url.startswith(
            "https://github.com/EngineeringSoftware/jog/blob/"
        )
        assert "before(" in rule.provenance.original and "after(" in rule.provenance.original
        assert rule.provenance.normalized == canonical_bytes(
            {"lhs": pattern_node(rule.lhs), "rhs": pattern_node(rule.rhs)}
        ).decode("ascii")
        assert check_rule(rule).status == "verified", rule.id
    exclusions = json.loads((ROOT / "corpus/exclusions.json").read_text(encoding="utf-8"))
    assert len(exclusions["excluded"]) == 94
    assert all(item["reason"] for item in exclusions["excluded"])


def test_constructed_rules_remain_separate_and_valid() -> None:
    for name in ("budget", "interference"):
        corpus = load_corpus(ROOT / f"tests/fixtures/{name}.json")
        assert corpus.kind == "synthetic"
        assert all(check_rule(rule).status == "verified" for rule in corpus.rules)
