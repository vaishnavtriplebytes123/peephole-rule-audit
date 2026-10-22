import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


def corpus_file(path: Path, *, invalid_rule: bool = False) -> Path:
    x = {"op": "meta", "name": "X", "kind": "expr"}
    rule = {
        "id": "add_zero",
        "lhs": {"op": "add", "args": [x, {"op": "const", "value": int(invalid_rule)}]},
        "rhs": x,
        "guards": [],
        "provenance": {
            key: "constructed fixture"
            for key in (
                "source_url",
                "revision",
                "location",
                "original",
                "normalized",
                "restrictions",
                "license",
                "redistribution",
            )
        },
    }
    path.write_text(
        json.dumps({"schema_version": 1, "kind": "synthetic", "rules": [rule]}), encoding="utf-8"
    )
    return path


def invoke(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "ruleaudit", *args],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONUTF8": "1"},
        timeout=30,
    )


@pytest.mark.parametrize("invalid_rule,status", [(False, "verified"), (True, "invalid")])
def test_validated_report_with_semantic_outcome(
    tmp_path: Path, invalid_rule: bool, status: str
) -> None:
    path = corpus_file(tmp_path / "rules 문서.json", invalid_rule=invalid_rule)
    out = tmp_path / "report dir"
    result = invoke("validate", "--rules", str(path), "--out", str(out))
    assert result.returncode == 0, result.stderr
    report = json.loads((out / "validation.json").read_text(encoding="utf-8"))
    assert report["status"] == "completed"
    assert report["results"][0]["status"] == status
    assert report["solver_calls"] == 2
    assert len(report["corpus_hash"]) == 64
    assert report["corpus"]["kind"] == "synthetic"
    assert "Traceback" not in result.stderr


def test_partial_call_limit_and_output_collision(tmp_path: Path) -> None:
    path = corpus_file(tmp_path / "rules.json")
    out = tmp_path / "report"
    result = invoke("validate", "--rules", str(path), "--out", str(out), "--solver-max-calls", "0")
    assert result.returncode == 3
    saved = (out / "validation.json").read_bytes()
    assert json.loads(saved)["status"] == "partial"
    result = invoke("validate", "--rules", str(path), "--out", str(out))
    assert result.returncode == 2
    assert (out / "validation.json").read_bytes() == saved
    assert "exists" in result.stderr


def test_invalid_json_and_missing_input(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{", encoding="utf-8")
    result = invoke("validate", "--rules", str(path), "--out", str(tmp_path / "out"))
    assert result.returncode == 2
    assert "JSON" in result.stderr
    assert not (tmp_path / "out").exists()
    result = invoke(
        "validate", "--rules", str(tmp_path / "missing.json"), "--out", str(tmp_path / "out")
    )
    assert result.returncode == 4
    assert "Traceback" not in result.stderr


def test_solver_settings_are_bounded(tmp_path: Path) -> None:
    path = corpus_file(tmp_path / "rules.json")
    result = invoke(
        "validate", "--rules", str(path), "--out", str(tmp_path / "out"), "--solver-timeout-ms", "0"
    )
    assert result.returncode == 2
    assert "timeout_ms" in result.stderr
