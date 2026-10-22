import os
import subprocess
import sys

import pytest


@pytest.mark.parametrize(
    "argument,code,text",
    [("--help", 0, "usage:"), ("--version", 0, "0.1.0"), ("audit", 2, "error:")],
)
def test_cli(argument: str, code: int, text: str) -> None:
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    result = subprocess.run(
        [sys.executable, "-m", "ruleaudit", argument],
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )
    assert result.returncode == code
    assert text in result.stdout + result.stderr
    assert "Traceback" not in result.stderr
