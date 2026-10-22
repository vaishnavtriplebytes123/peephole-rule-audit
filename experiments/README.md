# Smoke configurations and generator checks

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

## M4 equal-cap generator smoke

`m4-smoke-matrix.json` records twelve complete configurations: synthetic
interference and JOG target `jog_pAdd3`, seeds 0/1, all three modes. Each trial
caps accepted cases at 8, attempts at 200, guidance matches at 10,000, elapsed
computation at 60 s and solver calls at 100,000 (1,000 ms per query). The shared
constant domain is 0/1/4294967295, expansion depth 2, complete-input nodes <=63
and depth <=5, contexts hole/not/add-left/add-right, preorder/corpus priority,
H=4. Configs were fixed before running this comparison.

`m4-smoke-results.json` retains every raw case row, including costs, provenance,
hashes, stop/semantic status, timings, attempts and zero-coverage trials. The
original full reports/witnesses are under ignored `artifacts/m4-smoke/`; configs
and corpus hashes permit regeneration. The initial replay driver stopped on an
inconclusive corpus validation during JOG seed-1 target replay, while tests ran
concurrently. The record preserves that event. A sequential pass after tests
finished verified **49/49 witnesses**. That observation does not establish the
cause of the earlier inconclusiveness.

| Corpus / seed | Random findings / tested | Target findings / tested | Guided findings / tested |
|---|---:|---:|---:|
| Synthetic / 0 | 1 / 8 | 8 / 8 | 8 / 8 |
| Synthetic / 1 | 2 / 8 | 8 / 8 | 8 / 8 |
| JOG / 0 | 0 / 8 | 7 / 8 | 0 / 0 (partial) |
| JOG / 1 | 0 / 8 | 7 / 8 | 0 / 0 (partial) |

Only the 32 synthetic target/guided findings have a checked initial alternative.
The source target has no discovered bounded template, so guided generation
exhausts 200 attempts without fallback. The 14 source target findings and three
random synthetic findings are unqualified removal regressions. These small
trials do not demonstrate a guidance advantage, source-rule derivability or
production runtime impact. M6 adds controlled evaluation and eligibility rates.

To regenerate all trials, use a new root and the installed local interpreter:

```powershell
@'
import json, subprocess, sys
from pathlib import Path
matrix = json.loads(Path('experiments/m4-smoke-matrix.json').read_text())
root = Path('artifacts/m4-demo-NEW')
root.mkdir()
for trial in matrix['runs']:
    config = root / (trial['name'] + '.json')
    config.write_text(json.dumps(trial['config']), encoding='utf-8')
    result = subprocess.run([sys.executable, '-m', 'ruleaudit', 'audit',
        '--rules', trial['rules'], '--target', trial['target'],
        '--config', str(config), '--out', str(root / trial['name'])])
    if result.returncode not in (0, 3):
        raise SystemExit(result.returncode)
'@ | .venv/Scripts/python.exe -
```

Semantic traces/provenance are repeatable; wall time and solver resource outcomes
can vary. Output directories are never reused or overwritten.

## M5 reduction

`reduction.json` contains bounded reduction settings, rather than an audit
configuration. Reduction requires an original witness with a checked alternative;
the changed input retains separate provenance and every accepted shrink replays.

```powershell
.venv/Scripts/python.exe -m ruleaudit reduce --witness tests/fixtures/m4-guided-witness-v1.json --config experiments/reduction.json --out artifacts/demo-reduced-NEW
.venv/Scripts/python.exe -m ruleaudit replay --witness artifacts/demo-reduced-NEW/witness.json --out artifacts/demo-reduced-replay-NEW
```

The M5 manual run reduced 9 nodes to 5 in three accepted shrinks/14 attempts,
preserving a checked two-step alternative and delta 2 at H=4. The resulting
synthetic envelope is preserved in `tests/fixtures/m5-reduced-witness-v2.json`.
This is a local greedy result, not a global minimum or source-corpus evaluation.
Zero attempts/time and solver exhaustion return a partial reduction with its
last verified input. See [schema and caps](../docs/REDUCTION_FORMAT.md).

Audits now include `cases.csv`, validation includes `rules.csv`, and reduction
includes `summary.csv`. JSON retains full unescaped evidence; CSV protects text
cells from spreadsheet formula interpretation. Output failures retain `.partial`
files and explicit status when the filesystem permits it.
