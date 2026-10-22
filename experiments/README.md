# M3 smoke configurations

These are small, reproducible single-run configurations, not the M6 evaluation
matrix. Run from the repository root in the documented virtual environment.
Every output directory must be new.

```powershell
.venv/Scripts/python.exe -m ruleaudit validate --rules tests/fixtures/interference.json --out artifacts/demo-validation
.venv/Scripts/python.exe -m ruleaudit derive --rules tests/fixtures/interference.json --config experiments/interference-h4.json --target A --out artifacts/demo-derivation
.venv/Scripts/python.exe -m ruleaudit audit --rules tests/fixtures/interference.json --config experiments/interference-h4.json --target A --out artifacts/demo-audit
.venv/Scripts/python.exe -m ruleaudit replay --witness artifacts/demo-audit/witness-000001.json --out artifacts/demo-replay
```

`budget-h1.json` and `budget-h2.json` use `tests/fixtures/budget.json` and target
`A`. The H=1 fixture has a two-step alternative but only one rewrite available;
H=2 catches up for these leaf substitutions. `interference-h4.json` uses
`tests/fixtures/interference.json`: the target-free optimizer cycles under the
declared B/D/C order. All three are explicitly constructed synthetic examples.

`jog-smoke.json` uses `corpus/jog.json`; a small initial command is:

```powershell
.venv/Scripts/python.exe -m ruleaudit audit --rules corpus/jog.json --config experiments/jog-smoke.json --target jog_pAdd3 --out artifacts/demo-jog
```

The four-case source smoke run is not a generator comparison or effectiveness
benchmark. A positive delta without a checked alternative is recorded separately
from a derivation-backed regression. Neither bounded misses nor zero findings
justify deleting a production rule. See the audit's raw records and statuses.
