import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

from ruleaudit.config import Config, Generation
from ruleaudit.evaluation_config import EvaluationConfig, evaluation_document
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


def test_evaluate_cli_replays_reduces_and_refuses_overwrite(tmp_path: Path) -> None:
    settings = EvaluationConfig(
        base=Config(
            Schedule("preorder", ("A", "B", "D", "C")),
            run=RunLimits(h=4),
            generation=Generation(cases=1, depth=0),
        ),
        targets=("A",),
        seeds=(0,),
        h_values=(4,),
        traversals=("preorder",),
        priorities=("corpus",),
    )
    cfg = tmp_path / "evaluation.json"
    cfg.write_bytes(canonical_bytes(evaluation_document(settings)))
    out = tmp_path / "evaluation 문서"
    args = (
        "evaluate",
        "--rules",
        str(FIXTURES / "interference.json"),
        "--config",
        str(cfg),
        "--out",
        str(out),
    )
    result = invoke(*args)
    assert result.returncode == 0, result.stderr
    saved = (out / "evaluation.json").read_bytes()
    assert json.loads(saved)["finished_trials"] == 3
    assert json.loads((out / "status.json").read_text())["status"] == "completed"
    assert invoke(*args).returncode == 2
    assert (out / "evaluation.json").read_bytes() == saved
    cfg.write_bytes(canonical_bytes(evaluation_document(replace(settings, max_trials=0))))
    result = invoke(
        "evaluate",
        "--rules",
        str(FIXTURES / "interference.json"),
        "--config",
        str(cfg),
        "--out",
        str(tmp_path / "partial"),
    )
    assert result.returncode == 3, result.stderr
    report = json.loads((tmp_path / "partial/evaluation.json").read_text())
    assert report["not_run"] == 3 and report["trials"] == []
