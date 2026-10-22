from pathlib import Path

import pytest

from ruleaudit.report import IncompleteError, ReportWriter


def test_output_budget_retains_partial_and_reserves_status(tmp_path: Path) -> None:
    writer = ReportWriter(tmp_path / "out", 8192)
    with pytest.raises(IncompleteError, match="limit"):
        writer.write("large.json", {"value": "x" * 5000})
    assert (writer.directory / "large.json.partial").exists()
    assert not (writer.directory / "large.json").exists()
    writer.write("status.json", {"status": "partial"}, status=True)
    assert (writer.directory / "status.json").exists()
    with pytest.raises(FileExistsError):
        writer.write("status.json", {})
    with pytest.raises(ValueError):
        writer.write("../escape.json", {})
