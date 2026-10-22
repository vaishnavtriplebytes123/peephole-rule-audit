from pathlib import Path

import pytest

from ruleaudit.io import load_json
from ruleaudit.replay import replay


@pytest.mark.parametrize(
    "filename,qualified",
    [
        ("pilot-budget-witness.json", True),
        ("pilot-interference-witness.json", True),
        ("pilot-jog-unqualified-witness.json", False),
    ],
)
def test_preserved_pilot_witnesses_replay(filename: str, qualified: bool) -> None:
    result = replay(load_json(Path(__file__).parent / "fixtures" / filename))
    assert result["status"] == "verified"
    assert result["alternative_checked"] is qualified
