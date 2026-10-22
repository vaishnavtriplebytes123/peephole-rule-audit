import json
import os
import subprocess
import sys
from pathlib import Path

from ruleaudit.io import canonical_bytes
from ruleaudit.reduce import ReductionConfig, reduction_config_document

FIXTURES = Path(__file__).parent / "fixtures"


def invoke(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "ruleaudit", *args],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONUTF8": "1"},
        timeout=30,
    )


def test_reduce_replay_csv_and_collision_subprocess(tmp_path: Path) -> None:
    config = tmp_path / "config.json"
    config.write_bytes(canonical_bytes(reduction_config_document(ReductionConfig())))
    out = tmp_path / "reduced 문서"
    args = (
        "reduce",
        "--witness",
        str(FIXTURES / "m4-guided-witness-v1.json"),
        "--config",
        str(config),
        "--out",
        str(out),
    )
    result = invoke(*args)
    assert result.returncode == 0, result.stderr
    saved = (out / "witness.json").read_bytes()
    assert json.loads(saved)["schema_version"] == 2
    assert (out / "summary.csv").exists()
    assert json.loads((out / "reduction.json").read_text())["nodes_after"] == 5
    replayed = invoke(
        "replay", "--witness", str(out / "witness.json"), "--out", str(tmp_path / "replayed")
    )
    assert replayed.returncode == 0, replayed.stderr
    collision = invoke(*args)
    assert collision.returncode == 2
    assert (out / "witness.json").read_bytes() == saved


def test_partial_reduction_still_emits_replayable_original(tmp_path: Path) -> None:
    config = tmp_path / "config.json"
    config.write_bytes(canonical_bytes(reduction_config_document(ReductionConfig(max_attempts=0))))
    out = tmp_path / "partial"
    result = invoke(
        "reduce",
        "--witness",
        str(FIXTURES / "m3-witness-v1.json"),
        "--config",
        str(config),
        "--out",
        str(out),
    )
    assert result.returncode == 3, result.stderr
    assert json.loads((out / "status.json").read_text())["status"] == "partial"
    assert (
        invoke(
            "replay", "--witness", str(out / "witness.json"), "--out", str(tmp_path / "replayed")
        ).returncode
        == 0
    )


def test_malformed_reduction_config_and_unknown_witness_version(tmp_path: Path) -> None:
    config = tmp_path / "config.json"
    config.write_text('{"schema_version": 99}')
    result = invoke(
        "reduce",
        "--witness",
        str(FIXTURES / "m3-witness-v1.json"),
        "--config",
        str(config),
        "--out",
        str(tmp_path / "bad"),
    )
    assert result.returncode == 2 and "Traceback" not in result.stderr
    malformed = tmp_path / "witness.json"
    malformed.write_text('{"schema_version":99,"kind":"removal-witness","payload":{},"sha256":"x"}')
    result = invoke("replay", "--witness", str(malformed), "--out", str(tmp_path / "replay-bad"))
    assert result.returncode == 2 and "version" in result.stderr
