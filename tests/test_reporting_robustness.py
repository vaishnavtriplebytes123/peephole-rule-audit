import csv
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import ruleaudit.cli as cli
from ruleaudit.config import Config, config_document
from ruleaudit.io import canonical_bytes
from ruleaudit.report import IncompleteError, ReportWriter
from ruleaudit.rewrite import Schedule

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize(
    "text", ["=1+1", "+SUM(A1)", "-1+1", "@SUM(A1)", " \t=cmd()", "\x00=cmd()", "\u200b=cmd()"]
)
def test_csv_text_cannot_be_a_formula(tmp_path: Path, text: str) -> None:
    writer = ReportWriter(tmp_path / "out", 8192)
    writer.write_csv("cases.csv", [("text", "number", "empty"), (text, -2, None)])
    rows = list(csv.reader(io.StringIO((writer.directory / "cases.csv").read_text())))
    assert rows[1] == ["'" + text, "-2", ""]


def test_csv_quotes_and_output_caps_are_shared_with_json(tmp_path: Path) -> None:
    writer = ReportWriter(tmp_path / "out", 8192)
    writer.write_csv("safe.csv", [("a,b", 'a"b', "a\nb", "plain")])
    assert list(csv.reader(io.StringIO((writer.directory / "safe.csv").read_text()))) == [
        ["a,b", 'a"b', "a\nb", "plain"]
    ]
    with pytest.raises(IncompleteError):
        writer.write_csv("large.csv", [("x" * 5000,)])
    assert (writer.directory / "large.csv.partial").exists()
    assert not (writer.directory / "large.csv").exists()
    writer.write("status.json", {"status": "partial"}, status=True)
    assert (writer.directory / "status.json").exists()


@pytest.mark.parametrize(
    "failure,expected",
    [(IncompleteError("cap"), 3), (KeyboardInterrupt(), 130), (OSError("disk full"), 4)],
)
def test_status_write_failure_never_escapes_error_handler(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    failure: BaseException,
    expected: int,
) -> None:
    config = tmp_path / "config.json"
    config.write_bytes(
        canonical_bytes(config_document(Config(Schedule("preorder", ("A", "B", "C")))))
    )

    def fail(*args: object, **kwargs: object) -> None:
        raise failure

    def disk_error(*args: object, **kwargs: object) -> None:
        raise OSError("status disk full")

    monkeypatch.setattr(cli, "audit_experiment", fail)
    monkeypatch.setattr(ReportWriter, "write", disk_error)
    assert (
        cli.main(
            [
                "audit",
                "--rules",
                str(FIXTURES / "budget.json"),
                "--target",
                "A",
                "--config",
                str(config),
                "--out",
                str(tmp_path / "out"),
            ]
        )
        == expected
    )
    captured = capsys.readouterr()
    assert "Traceback" not in captured.err
    assert "status" in captured.err and "disk full" in captured.err


def test_validation_writes_common_status_and_csv(tmp_path: Path) -> None:
    out = tmp_path / "validation"
    assert cli.main(["validate", "--rules", str(FIXTURES / "budget.json"), "--out", str(out)]) == 0
    assert json.loads((out / "status.json").read_text())["status"] == "completed"
    with (out / "rules.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert [r["id"] for r in rows] == ["A", "B", "C"]
    assert all(r["status"] == "verified" for r in rows)


def test_ascii_console_does_not_turn_success_into_failure(tmp_path: Path) -> None:
    out = tmp_path / "report 문서"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ruleaudit",
            "validate",
            "--rules",
            str(FIXTURES / "budget.json"),
            "--out",
            str(out),
        ],
        capture_output=True,
        env={**os.environ, "PYTHONIOENCODING": "ascii:strict"},
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert (out / "validation.json").exists()


def test_real_flush_failure_retains_only_partial_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def full_disk(descriptor: int) -> None:
        raise OSError("injected fsync disk failure")

    monkeypatch.setattr(os, "fsync", full_disk)
    out = tmp_path / "failed"
    assert cli.main(["validate", "--rules", str(FIXTURES / "budget.json"), "--out", str(out)]) == 4
    assert not (out / "validation.json").exists()
    assert (out / "validation.json.partial").exists()
    assert (out / "status.json.partial").exists()
    assert "Traceback" not in capsys.readouterr().err


def test_subprocess_interpreter_interrupt_during_real_audit(tmp_path: Path) -> None:
    from dataclasses import replace

    config = Config(Schedule("preorder", ("A", "B", "C")))
    config = replace(
        config, generation=replace(config.generation, strategy="guided", attempts=1000000)
    )
    config_path = tmp_path / "interrupt.json"
    config_path.write_bytes(canonical_bytes(config_document(config)))
    script = """import _thread, sys, threading
import ruleaudit.cli as cli
original = cli.ReportWriter.__init__
def initialized(self, *args, **kwargs):
    original(self, *args, **kwargs)
    threading.Timer(0.2, _thread.interrupt_main).start()
cli.ReportWriter.__init__ = initialized
raise SystemExit(cli.main(sys.argv[1:]))
"""
    out = tmp_path / "interrupted"
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            "audit",
            "--rules",
            str(FIXTURES / "budget.json"),
            "--target",
            "A",
            "--config",
            str(config_path),
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONUTF8": "1"},
        timeout=30,
    )
    assert result.returncode == 130, result.stderr
    assert json.loads((out / "status.json").read_text())["status"] == "interrupted"
    assert "Traceback" not in result.stderr


def test_interrupt_is_latched_until_clock_checkpoint_and_handlers_restore() -> None:
    import signal

    from ruleaudit.interrupt import interruptible_clock

    previous = signal.getsignal(signal.SIGINT)
    with interruptible_clock() as now:
        signal.raise_signal(signal.SIGINT)
        # The signal handler returns safely, including during native object cleanup.
        with pytest.raises(KeyboardInterrupt):
            now()
        assert now() > 0
    assert signal.getsignal(signal.SIGINT) == previous


def test_audit_stops_before_pair_if_raw_record_storage_would_overflow(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import ruleaudit.experiment as experiment
    from ruleaudit.config import Generation
    from ruleaudit.corpus import load_corpus

    corpus = load_corpus(FIXTURES / "budget.json")
    config = Config(
        Schedule("preorder", ("A", "B", "C")), generation=Generation(cases=10000, attempts=10000)
    )
    monkeypatch.setattr(experiment, "MAX_AUDIT_BYTES", 512, raising=False)

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("pair executed without room for its raw record")

    monkeypatch.setattr(experiment, "audit_case", forbidden)
    out = tmp_path / "bounded"
    assert (
        experiment.audit_experiment(
            corpus, config, corpus.rules[0], ReportWriter(out, config.max_output_bytes)
        )
        == 3
    )
    report = json.loads((out / "audit.json").read_text())
    assert report["cases_tested"] == 0
    assert "report-record-limit" in report["reasons"]
