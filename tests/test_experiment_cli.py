import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

from ruleaudit.config import Config, Generation, config_document
from ruleaudit.io import canonical_bytes
from ruleaudit.rewrite import RunLimits, Schedule

FIXTURES = Path(__file__).parent / "fixtures"


def invoke(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "ruleaudit", *args],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONUTF8": "1"},
        timeout=30,
    )


def test_validate_derive_audit_replay_subprocess_journey(tmp_path: Path) -> None:
    corpus = str(FIXTURES / "interference.json")
    config = Config(
        Schedule("preorder", ("A", "B", "D", "C")),
        run=RunLimits(h=4),
        generation=Generation(cases=2, depth=0),
    )
    cfg = tmp_path / "config 문서.json"
    cfg.write_bytes(canonical_bytes(config_document(config)))
    validated = invoke("validate", "--rules", corpus, "--out", str(tmp_path / "validation"))
    assert validated.returncode == 0, validated.stderr
    derived = invoke(
        "derive",
        "--rules",
        corpus,
        "--config",
        str(cfg),
        "--target",
        "A",
        "--out",
        str(tmp_path / "derive"),
    )
    assert derived.returncode == 0, derived.stderr
    derivations = json.loads((tmp_path / "derive/derivations.json").read_text())
    assert derivations["status"] == "found"
    assert [step["rule_id"] for step in derivations["witnesses"][0]["steps"]] == ["B", "C"]
    out = tmp_path / "audit"
    audited = invoke(
        "audit", "--rules", corpus, "--config", str(cfg), "--target", "A", "--out", str(out)
    )
    assert audited.returncode == 0, audited.stderr
    report = json.loads((out / "audit.json").read_text())
    assert report["status"] == "completed"
    assert report["cases_tested"] == report["findings"] == 2
    assert report["checked_alternative_findings"] == 2
    assert report["corpus_kind"] == "synthetic"
    witnesses = sorted(out.glob("witness-*.json"))
    assert len(witnesses) == 2
    for index, witness in enumerate(witnesses):
        replayed = invoke(
            "replay", "--witness", str(witness), "--out", str(tmp_path / f"replay-{index}")
        )
        assert replayed.returncode == 0, replayed.stderr
    collision = invoke(
        "audit", "--rules", corpus, "--config", str(cfg), "--target", "A", "--out", str(out)
    )
    assert collision.returncode == 2


def test_zero_findings_partial_generation_and_solver_inconclusiveness(tmp_path: Path) -> None:
    corpus = str(FIXTURES / "budget.json")
    config = Config(
        Schedule("preorder", ("A", "B", "C")),
        run=RunLimits(h=2),
        generation=Generation(cases=2, depth=0),
    )
    cfg = tmp_path / "config.json"
    cfg.write_bytes(canonical_bytes(config_document(config)))
    result = invoke(
        "audit",
        "--rules",
        corpus,
        "--config",
        str(cfg),
        "--target",
        "A",
        "--out",
        str(tmp_path / "zero"),
    )
    assert result.returncode == 0, result.stderr
    assert json.loads((tmp_path / "zero/audit.json").read_text())["findings"] == 0
    partial = replace(config, generation=replace(config.generation, attempts=0))
    cfg.write_bytes(canonical_bytes(config_document(partial)))
    result = invoke(
        "audit",
        "--rules",
        corpus,
        "--config",
        str(cfg),
        "--target",
        "A",
        "--out",
        str(tmp_path / "partial"),
    )
    assert result.returncode == 3, result.stderr
    report = json.loads((tmp_path / "partial/audit.json").read_text())
    assert report["status"] == "partial" and report["cases_tested"] == 0
    unknown = replace(config, solver=replace(config.solver, max_calls=0))
    cfg.write_bytes(canonical_bytes(config_document(unknown)))
    result = invoke(
        "audit",
        "--rules",
        corpus,
        "--config",
        str(cfg),
        "--target",
        "A",
        "--out",
        str(tmp_path / "unknown"),
    )
    assert result.returncode == 3, result.stderr
    assert json.loads((tmp_path / "unknown/status.json").read_text())["status"] == "partial"


def test_audit_never_opens_python_network_connections(tmp_path: Path, monkeypatch: object) -> None:
    import socket

    import pytest

    from ruleaudit.cli import main

    assert isinstance(monkeypatch, pytest.MonkeyPatch)

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("network use during audit")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    config = Config(
        Schedule("preorder", ("A", "B", "C")),
        run=RunLimits(h=1),
        generation=Generation(cases=1, depth=0),
    )
    cfg = tmp_path / "offline.json"
    cfg.write_bytes(canonical_bytes(config_document(config)))
    assert (
        main(
            [
                "audit",
                "--rules",
                str(FIXTURES / "budget.json"),
                "--config",
                str(cfg),
                "--target",
                "A",
                "--out",
                str(tmp_path / "offline"),
            ]
        )
        == 0
    )


def test_cli_interrupt_records_explicit_status(tmp_path: Path, monkeypatch: object) -> None:
    import pytest

    import ruleaudit.cli as cli

    assert isinstance(monkeypatch, pytest.MonkeyPatch)

    def interrupted(*args: object, **kwargs: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(cli, "audit_experiment", interrupted)
    config = Config(Schedule("preorder", ("A", "B", "C")))
    cfg = tmp_path / "interrupt.json"
    cfg.write_bytes(canonical_bytes(config_document(config)))
    out = tmp_path / "interrupted"
    assert (
        cli.main(
            [
                "audit",
                "--rules",
                str(FIXTURES / "budget.json"),
                "--config",
                str(cfg),
                "--target",
                "A",
                "--out",
                str(out),
            ]
        )
        == 130
    )
    assert json.loads((out / "status.json").read_text())["status"] == "interrupted"
