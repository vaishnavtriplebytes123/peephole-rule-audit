# Development environment and verification

## Observed baseline — 2026-10-22

- Existing repository, no commits, no tracked files, branch `master`, no remotes.
- Git 2.46.1.windows.1 is available. Effective user.name and user.email are unset.
- `python --version` fails: the WindowsApps alias is inaccessible.
- `py --list-paths` reports no installed Python runtimes.
- Codex bundled interpreter works: Python 3.12.14 at
  `C:/Users/vaish/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`.
- Bundled interpreter has pip and venv. Imports were probed, not installed:
  pytest, z3, ruff, mypy and build are unavailable there.
- No application package, pyproject.toml, tests, lockfiles, test/lint/build commands,
  database, or service exists. Existing presentation scripts are unrelated to the
  planned application. They are not an application correctness baseline.
- No dependencies installed and no application tests executed during foundation work.

The bundled path is machine-specific. It is a bootstrap option, not a path to hardcode
in application code. A standalone Python 3.12 installation can be used instead.

## Setup — Python 3.12 on Windows

Create a local virtual environment. Example for this machine in PowerShell.
In the Codex sandbox, use workspace-local temporary storage and UTF-8 output:

```powershell
New-Item -ItemType Directory -Force tmp | Out-Null
$env:TEMP = Join-Path (Get-Location) 'tmp'
$env:TMP = $env:TEMP
$env:PYTHONUTF8 = '1'
& 'C:/Users/vaish/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -m venv .venv
```

Use `.venv/Scripts/python.exe` explicitly to avoid PowerShell activation-policy
changes. The initial attempt without workspace-local temporary storage failed
in ensurepip with a temporary-directory permission error. UTF-8 prevents pip's
legacy console renderer from failing to print this repository's Korean path.

M1 creates `pyproject.toml`, `requirements.in`, `requirements-dev.in`,
`requirements.lock`, and `requirements-dev.lock`. Runtime input includes z3-solver;
development input includes the runtime input and adds pytest, Hypothesis, Ruff,
mypy, build and pip-tools.
Resolve and pin compatible direct/transitive versions, generate hashes where
supported, and document the resolver version/bootstrap procedure. Align package
metadata and lock inputs; do not maintain contradictory dependency specifications.
Test installation on Windows/Python 3.12 before claiming reproducibility elsewhere.

Installation commands (lock verification status is recorded below):

```powershell
.venv/Scripts/python.exe -m pip install --require-hashes -r requirements-dev.lock
.venv/Scripts/python.exe -m pip install --no-deps --no-build-isolation -e .
```

The development lock includes the explicitly pinned setuptools 84.2.1 and wheel
0.48.0 backend requirements. Both commands were verified at the M1/M2 checkpoint.

To regenerate locks on Python 3.12/Windows, bootstrap pip-tools 7.6.2 in the
project venv, then run these commands (network access is for installation only):

```powershell
.venv/Scripts/python.exe -m pip install pip-tools==7.6.2
.venv/Scripts/python.exe -m piptools compile --cache-dir tmp/piptools-cache --generate-hashes --allow-unsafe --strip-extras --output-file requirements.lock requirements.in
.venv/Scripts/python.exe -m piptools compile --cache-dir tmp/piptools-cache --newline lf --generate-hashes --allow-unsafe --strip-extras --constraint requirements.lock --output-file requirements-dev.lock requirements-dev.in
```

The runtime lock has one package and ten distribution hashes. The development
lock has 23 direct/transitive packages and 386 distribution hashes. Resolve on
the target platform; these are verified on Windows/Python 3.12 only.

## Validation commands

Run with the environment settings above:

```powershell
.venv/Scripts/python.exe -m pytest --basetemp=tmp/pytest-validation
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m ruff format --check .
.venv/Scripts/python.exe -m mypy src tests
.venv/Scripts/python.exe -m build --no-isolation
.venv/Scripts/python.exe -m ruleaudit --help
git diff --check
git diff
```

Restrict Ruff/mypy/pytest discovery to application code and tests, excluding the
existing coursework, presentation build directory, and reference checkout. For
untracked initial files, `git diff` is insufficient: inspect their full contents
and use no-index whitespace checks before any authorized staging.

At M5, verify wheel installation in a separate temporary virtual environment,
with locked dependencies; invoke every implemented CLI command on a curated
fixture. Record actual commands and outputs in milestone evidence. There is no
development server or production service start command.

When rebuilding in a sandbox, Python's secure tar extraction may require a
permission escalation even for a workspace-local directory. The initial
`build --no-isolation` failed at `os.path.realpath(..., ALLOW_MISSING)` with
WinError 5; this is not a semantic-test failure. Do not disable archive filters.

## Configuration and operations

- No required environment variables, credentials, database migrations, cloud, or GPU.
- Use CLI paths and versioned JSON configuration. `.env.example` documents the
  intentional absence of secrets; no automatic dotenv loader is planned.
- Keep generated results under `artifacts/`; curated fixtures/configs remain tracked.
- Every experiment records hardware, Python/dependency/tool versions, input hashes,
  settings, limits, seed, run status, wall time and CPU time where supported.
- Reports never overwrite existing output directories. No automatic deletion or uploads.

## Foundation validation record

Foundation-only checks are recorded after file creation. They do not establish
that any application feature, test suite, or proposed command works.

Checks executed during foundation preparation:

- `git status --short --branch`: only the intended foundation files and docs/
  remain visible as untracked; existing excluded materials remain on disk.
- `git diff --check`, `git diff --stat`, `git diff --cached --stat`: no tracked
  or staged changes. These do not validate untracked file content by themselves.
- A Python standard-library check inspected all nine foundation files for existence,
  nonempty UTF-8 content, local Markdown link resolution, all 18 numbered PRD
  sections and 14 research reference entries.
- `git check-ignore --quiet -- <path>` was exercised on eight ignored paths and
  eight paths that must remain trackable, including .env.example and lockfiles.
- Per-file `git -c core.autocrlf=false diff --no-index --check -- NUL <file>`
  checks cover untracked content. This per-command option does not change Git
  configuration. The first check without it treated existing Git LF-to-CRLF
  warning messages as errors; those were conversion warnings, not whitespace defects.
  A subsequent check exposed CRLF endings in the generated research document;
  that new file was normalized to LF and the complete check was rerun successfully.

Final foundation outcome: all nine files, local links, 18 PRD sections, 14 reference
entries, whitespace checks and 16 ignore/trackability examples passed.

No application test, lint, type-check, build, dependency installation, experiment,
or research-result replication was performed. Those remain milestone work.

## M1/M2 implementation verification — 2026-10-22

Environment: Windows, bundled Python 3.12.14, project `.venv`; UTF-8 and
workspace-local TEMP/TMP as above. No global Python packages or Git identity
were changed. Dependency installation required approved network access because
the sandbox's initial PyPI DNS lookup failed. Installation succeeded; pip's
first run printed console encoding errors until PYTHONUTF8 was set.

Tests preceded application modules: the initial M1 run failed collection because
`ruleaudit` did not exist. The initial M2 runs failed for missing rules/rewrite/
solver/corpus modules and missing `validate` CLI. New semantic edge tests also
failed before their fixes (overflowed JSON exponent, growth completion status,
and huge integer time-limit validation).

Checks executed for the M1/M2 checkpoint:

- `.venv/Scripts/python.exe -m pytest --basetemp=tmp/pytest-m1-final`:
  **52 passed in 48.14 s** (M1 library and CLI at that checkpoint).
- `.venv/Scripts/python.exe -m ruff check .`: **passed** after fixes.
- `.venv/Scripts/python.exe -m ruff format --check .`: **passed**, 18 files.
- `.venv/Scripts/python.exe -m mypy src tests`: **passed**, most recently 18
  source files at the M2 checkpoint.
- `.venv/Scripts/python.exe -m build --no-isolation`: initial sandbox attempt
  failed during tar extraction with WinError 5. The same command with approved
  escalation **built sdist and wheel**. Repeated successfully after adding M2,
  locks, curated fixtures/corpus, license, and the source manifest.
- `.venv/Scripts/python.exe -m ruleaudit --help`, `--version`, and
  `.venv/Scripts/ruleaudit.exe --version`: **passed** (`ruleaudit 0.1.0`).
- `.venv/Scripts/python.exe -m pip check`: **No broken requirements found**.
- `.venv/Scripts/python.exe -c "import z3; print(z3.get_version_string())"`:
  **5.3.1**, distribution version **5.3.1.0**.
- `.venv/Scripts/python.exe -m pytest --basetemp=tmp/pytest-m2-all`:
  **94 passed in 49.28 s**. A subsequent numeric-limit test exposed an
  OverflowError; the check was reordered. The follow-up checkpoint passed
  **95 tests in 32.03 s**. After the hash-required reinstall,
  `.venv/Scripts/python.exe -m pytest --basetemp=tmp/pytest-m2-locked` passed
  **95 tests in 73.56 s**, followed by passing Ruff/format/mypy checks.
- `.venv/Scripts/python.exe -m ruleaudit validate --rules corpus/jog.json --out artifacts/m2-corpus-initial`:
  **exit 0**, 26/26 rules verified, 52 solver calls; complete validation report
  saved under ignored artifacts. This is semantic validation, not a removal
  experiment or evidence of practical redundancy.

The Windows sandbox rejected hard-link publication of reports. Publication now
uses Windows' non-replacing atomic rename; POSIX uses a non-replacing hard link.
The CLI tests subsequently passed, including report-directory collisions and
solver-call-limit partial status. Linux remains unverified.

Locks: both locks were generated with pip-tools 7.6.2, including exact
z3-solver 5.3.1.0 and SHA-256 hashes. The verification command
`.venv/Scripts/python.exe -m pip install --disable-pip-version-check --require-hashes --force-reinstall -r requirements-dev.lock`
successfully reinstalled all 23 packages. The editable install was then repeated
and `pip check` again reported no broken requirements.
The resolver downloads/hashes distributions for multiple platforms. Those
downloads remain in ignored tmp/; no cross-platform execution was verified.

Git: origin was set to the user-supplied repository and `git ls-remote origin`
confirmed no remote branches. Actual author values were supplied by the user
and set repository-locally. Commit/publication state is recorded by Git history
and the remote branch. Chrome Computer Use
ended because it could not confidently verify the current URL; the user created
the repository directly. The unrelated connected GitHub account is not used to
attribute or publish this project's commits.

All 42 intended files passed per-file untracked whitespace and local Markdown
link checks. The initial check caught an extra TOML trailing blank line and CRLF
line endings in the newly copied license; those new files were normalized and
the complete check passed. The reference checkout remains unchanged. Check the
staged diff again before the authorized commit.

Not performed at this checkpoint: clean-wheel installation (scheduled in M5),
Linux/other-Python verification, derivation/removal experiments, replay,
generator comparisons, reduction or controlled research evaluation. M3–M6
remain required; the current tests and 26 solver proofs do not establish those
features or an empirical advantage.

## M3 core progress — not a completed milestone

The M1/M2 checkpoint `d6855fccec8bfcd66109d9231a0ea51f4965749c` was pushed to
`origin/master`; `git ls-remote origin refs/heads/master` matched that exact SHA.

Derivation and runtime-equivalence tests were added before their implementations
and initially failed for the missing module/function. The first search-limit
test exposed endpoint states missing from the discovered-state counter; that
was fixed before this checkpoint. The search preserves opaque placeholders,
excludes the target at every step, requires structural endpoints, checks every
guard and semantic obligation, and retains explicit inconclusive statuses.

`.venv/Scripts/python.exe -m pytest tests/test_derive.py tests/test_solver.py tests/test_rewrite.py --basetemp=tmp/pytest-m3-derive-bounds`
passed **42 tests in 11.41 s**. Ruff and strict mypy passed (20 source files).
`.venv/Scripts/python.exe -m pytest --basetemp=tmp/pytest-m3-core` then passed
**114 tests in 49.58 s**. `ruff check .`, `ruff format --check .`,
`mypy src tests`, and `git -c core.autocrlf=false diff --check` all passed.
No package build was repeated for this partial M3 progress checkpoint; the full
M3 review will require the build and end-to-end CLI journey.

M3 is still incomplete: no derive/audit/replay CLI, experiment configuration,
target-only generation, paired executions, snapshots, witness replay, or full
synthetic acceptance journey exists yet. No empirical removal finding is claimed.

## M3 complete — paired audits and replay

The preceding M3-core note describes its earlier partial checkpoint. M3 now
includes the complete CLI journey, strict single-run configuration, seeded
target-only generation, paired executions, bounded atomic JSON reports, complete
witness snapshots/hashes, template/concrete-path checking and independent replay.
The baseline generator receives no derivation data. No new dependency was added.

Behavioral tests first failed for missing config/audit/replay modules and CLI
commands. Later tests exposed missing report version metadata, absence of a
shared solver deadline, and acceptance of a template whose starting tree exceeded
a modified search limit. Each was fixed after its failing test. Replay tests
recompute checksums after modifying traces/costs/configuration/provenance, so
successful hashing alone cannot satisfy them.

Verification commands and actual outcomes:

- `.venv/Scripts/python.exe -m pytest --basetemp=tmp/pytest-m3-reviewed`:
  **145 passed in 69.65 s**.
- `.venv/Scripts/python.exe -m pytest tests/test_audit_replay.py::test_saved_m3_v1_fixture_replays_without_regenerating_its_report --basetemp=tmp/pytest-m3-golden-green`:
  **1 passed in 3.12 s**. This replays the actual preserved schema-v1 report,
  rather than regenerating the expected evidence with the current producer.
- `.venv/Scripts/python.exe -m ruff check .` and
  `.venv/Scripts/python.exe -m ruff format --check .`: **passed**, 31 files.
- `.venv/Scripts/python.exe -m mypy src tests`: **passed**, 31 source files.
- `.venv/Scripts/python.exe -m build --no-isolation`: **sdist and wheel built**
  with the previously documented Windows permission escalation. Review caught
  the missing experiment-config manifest entry; it was added and the build was
  repeated with configs/examples included.
- `.venv/Scripts/python.exe -m ruleaudit --help` and `--version`: **passed**,
  listing validate/derive/audit/replay and version 0.1.0.
- `git -c core.autocrlf=false diff --check`: **passed** for tracked changes;
  untracked/staged files receive additional checks before the checkpoint commit.

Manual commands (all completed with exit 0; each output directory was new):

```powershell
.venv/Scripts/python.exe -m ruleaudit validate --rules tests/fixtures/interference.json --out artifacts/m3-validate
.venv/Scripts/python.exe -m ruleaudit derive --rules tests/fixtures/interference.json --config experiments/interference-h4.json --target A --out artifacts/m3-derive
.venv/Scripts/python.exe -m ruleaudit audit --rules tests/fixtures/budget.json --config experiments/budget-h1.json --target A --out artifacts/m3-budget-h1
.venv/Scripts/python.exe -m ruleaudit audit --rules tests/fixtures/budget.json --config experiments/budget-h2.json --target A --out artifacts/m3-budget-h2
.venv/Scripts/python.exe -m ruleaudit audit --rules tests/fixtures/interference.json --config experiments/interference-h4.json --target A --out artifacts/m3-interference-h4
.venv/Scripts/python.exe -m ruleaudit audit --rules corpus/jog.json --config experiments/jog-smoke.json --target jog_pAdd3 --out artifacts/m3-jog-smoke
.venv/Scripts/python.exe -m ruleaudit replay --witness artifacts/m3-interference-h4/witness-000001.json --out artifacts/m3-replay
.venv/Scripts/python.exe -m ruleaudit replay --witness tests/fixtures/m3-witness-v1.json --out artifacts/m3-golden-replay
```

| Manual run | Tested | Positive deltas | With checked alternative | Deltas |
|---|---:|---:|---:|---|
| Synthetic budget H=1 | 4 | 4 | 4 | 1, 1, 1, 1 |
| Synthetic budget H=2 | 4 | 0 | 0 | 0, 0, 0, 0 |
| Synthetic interference H=4 | 4 | 4 | 4 | 2, 2, 2, 2 |
| JOG jog_pAdd3 smoke H=2 | 4 | 1 | 0 | 2, 0, 0, 0 |

A Python stdin loop called `replay(load_json(path))` on every numbered witness
in those four directories: **9/9 verified**. The JOG smoke produced a bounded
derivation miss and one unqualified removal regression; it does not demonstrate
usefulness of a derivable source rule. These are small smoke observations, not
the M6 controlled evaluation or evidence that guidance outperforms baselines.
The committed golden witness is synthetic and contains no machine paths/secrets.

Final checkpoint: `.venv/Scripts/python.exe -m pytest
--basetemp=tmp/pytest-m3-final-evidence` passed **146 tests in 47.55 s**, including
the saved v1 witness. `ruff check .`, `ruff format --check .`, `mypy src tests`
and `git -c core.autocrlf=false diff --check` passed (31 formatted/typed files).
`python -m build --no-isolation` successfully rebuilt the sdist and wheel;
archive inspection confirmed experiment configs, schema documentation and the
saved witness in the sdist, and all new modules in the wheel.

The tests also block Python socket connections during an audit, check explicit
CLI interruption status, reject report collisions without overwriting bytes,
exercise zero-coverage partial generation, solver exhaustion and snapshot/trace
tampering, and verify depth-128 report containers without relaxing depth-64
expression inputs. Linux, clean-wheel installation, CSV/reduction, all three
generators and the research matrix remain M4–M6 work.

## M4 — generation modes and overlap evidence

M4 adds seeded random and guided modes, one-operator contexts and generated
siblings, common complete-input bounds, a cumulative guidance-match cap and
per-match deadline checks. Configuration version 2 makes new bounds explicit;
version 1 remains supported without changing saved target/hole provenance.
Replay verifies guided templates and recomputes the actual competing match,
prefix, intermediate state, guards, context, traces and costs. No dependency added.

Test-first evidence: importing the new guided/random functions initially failed;
the work-cap test initially failed for missing `GuidanceBudget`. Implementations
then passed the focused suites. Coverage includes seed repetition, shared bounds,
duplicates, guard rejection, same-node/ancestor competition, first scheduled
matches in disjoint siblings, no-overlap/no-template exhaustion, no fallback,
baseline interfaces without derivations, config compatibility and rehashed
guidance tampering. The saved M4 fixture was copied from an actual emitted
synthetic witness after its missing-file test failed.

Actual checks:

- `.venv/Scripts/python.exe -m pytest tests/test_generation_modes.py tests/test_config_generate.py tests/test_audit_replay.py tests/test_experiment_cli.py --basetemp=tmp/pytest-m4-modes`:
  **48 passed in 27.87 s**.
- `.venv/Scripts/python.exe -m pytest tests/test_generation_modes.py --basetemp=tmp/pytest-m4-isolation`:
  **22 passed in 6.03 s** after adding schedule/baseline orchestration cases.
- `.venv/Scripts/python.exe -m pytest --basetemp=tmp/pytest-m4-full`:
  **168 passed in 74.70 s**.
- `.venv/Scripts/python.exe -m pytest tests/test_generation_modes.py::test_saved_m4_guided_witness_replays --basetemp=tmp/pytest-m4-golden-green`:
  **1 passed in 3.15 s**.
- Ruff check/format and mypy passed (32 source/test files), including correction
  of redundant test casts. Final checkpoint verification is recorded below.

Final checkpoint commands: `python -m pytest --basetemp=tmp/pytest-m4-final`
passed **169 tests in 38.78 s**. After replacing a source-text assertion with a
behavioral baseline-isolation check, `python -m pytest
tests/test_generation_modes.py::test_baseline_interfaces_do_not_receive_guidance
--basetemp=tmp/pytest-m4-baseline-final` passed **1 test in 4.14 s**.
All Python commands use `.venv/Scripts/python.exe`. `ruff check .`,
`ruff format --check .` and `mypy src tests` passed (32 files).
`python -m build --no-isolation` built the sdist and wheel with the documented
Windows escalation. Help/version passed. A standard-library inspection checked
local Markdown links and whitespace across 53 source/doc/config/test files and
the smoke-result count/actual replay statuses; Git whitespace checks passed.

The versioned [M4 smoke matrix](../experiments/m4-smoke-matrix.json) was executed
using subprocess `python -m ruleaudit audit` for each full config, accepting
only exit 0/3 and preserving each new directory. A follow-up Python loop called
`replay` on every emitted witness. [Results](../experiments/m4-smoke-results.json)
retain raw case rows and all zero/partial trials. All 49 witnesses verified in
the final sequential pass. The first driver stopped on an inconclusive corpus
validation during a JOG seed-1 target witness replay while tests ran concurrently;
that event is retained, not treated as a verified result or assigned an unproven
cause. See [experiment notes](../experiments/README.md) for exact caps, outcomes
and reproduction commands. No guidance advantage or source derivability is claimed.

M5/M6 remain: reduction and provenance for changed inputs, resilient status/CSV
reporting, clean-wheel installation, labeled scenarios, held-out expressions,
controlled evaluation and research reporting. Linux remains unverified.

## M5 — reduction, reporting and interruption (2026-10-23)

The `reduce` command now keeps the original generated witness, records allowed
strictly decreasing changes in a version-2 envelope, and checks every accepted
input's target path, paired delta and SMT evidence. Original v1 witnesses still
replay. Partial/interrupted minimization retains the last verified candidate.
CSV summaries and all command outputs use one bounded atomic/no-replace writer.
Audit record accumulation is bounded before another pair executes. Console
encoding and failure to save status cannot turn into unhandled tracebacks.
No dependency or semantic/operator/schedule contract changed.

Test-first evidence and fixes:

- Reporting tests initially **13 failed**, exposing missing CSV output, unsafe
  status-write error handling, separate validation output code and ASCII-console
  failure. The focused writer/CLI suite then **23 passed in 40.10 s**.
- Reduction tests initially failed to import the missing module; CLI tests then
  failed for the missing command. A trace-injected interruption test exposed
  inconsistent accepted history versus final input. A single tuple assignment
  now commits the input/evidence/history together. The combined reducer/CLI/
  reporting suite **35 passed in 20.62 s**.
- A full run had **202 passed, 2 failed in 72.67 s**: the old unsupported-version
  check needed a version/kind compatibility message, and a timed interpreter
  interruption was swallowed by a Z3 object's `__del__`, producing an unraisable
  traceback. A signal latch with explicit clock checkpoints fixed the latter;
  the missing-latch test was red first. Follow-up focused checks **51 passed in
  20.05 s**, and `.venv/Scripts/python.exe -m pytest
  --basetemp=tmp/pytest-m5-reviewed` **207 passed in 54.53 s**.
- Further tests cover refusing a smaller input that retains a path but loses
  its positive delta, refusing a positive delta that loses its initial path,
  zero solver calls, and a serialized-record preflight cap. The latter failed
  before implementation, then **1 passed in 3.61 s**. The preserved reduced
  fixture's missing-file test was red before copying the actual emitted report.

Manual commands, both exit 0:

```powershell
.venv/Scripts/python.exe -m ruleaudit reduce --witness tests/fixtures/m4-guided-witness-v1.json --config experiments/reduction.json --out artifacts/m5-reduction
.venv/Scripts/python.exe -m ruleaudit replay --witness artifacts/m5-reduction/witness.json --out artifacts/m5-reduction-replay
```

Observed: **9 -> 5 nodes**, **3 accepted / 14 attempted**, **delta 2**, **18 shrink
solver calls**. Origin verification/preparation took 0.1626 s; shrinking took 0.0489 s in this
small manual run. These are local smoke timings, not performance claims.

Clean-wheel setup used a fresh `tmp/m5-wheel-venv`, workspace-local TEMP/TMP,
and a cached exact runtime wheel downloaded with hashes. Commands:

```powershell
.venv/Scripts/python.exe -m pip download --require-hashes --no-deps --only-binary :all: -r requirements.lock --dest tmp/m5-wheelhouse
.venv/Scripts/python.exe -m venv tmp/m5-wheel-venv
.venv/Scripts/python.exe -m build --no-isolation
tmp/m5-wheel-venv/Scripts/python.exe -m pip install --no-index --find-links tmp/m5-wheelhouse --require-hashes -r requirements.lock
tmp/m5-wheel-venv/Scripts/python.exe -m pip install --no-index --no-deps dist/ruleaudit-0.1.0-py3-none-any.whl
tmp/m5-wheel-venv/Scripts/python.exe -m pip check
```

The wheel and sdist built with the documented Windows escalation. Offline clean
installation and `pip check` passed. From an empty `tmp/m5-clean-cwd`, the clean
interpreter ran with `-I`: verified `ruleaudit.__file__` is in `site-packages`
and pytest is absent; validated 26 JOG rules; derived/audited the synthetic
interference fixture; replayed an emitted audit witness; reduced the saved M4
witness and replayed the reduced output. All commands exited 0 under new
`artifacts/m5-clean-*` directories. The installed console entry point reported
`ruleaudit 0.1.0`. An initial verification helper failed printing its Unicode
installation path under isolated cp1252; using `ascii(path)` corrected that
helper. The product separately passes its strict-ASCII-console subprocess test.
The final record-cap change receives a rebuilt-wheel recheck at checkpoint.

Final regression command `.venv/Scripts/python.exe -m pytest
--basetemp=tmp/pytest-m5-checkpoint`: **210 passed in 53.95 s**. This includes
the actual preserved reduced witness and a final-clock interruption test that
first failed when the last verified input escaped through `KeyboardInterrupt`;
final timing capture now retains and returns that input. Ruff check/format,
mypy (37 source/test files), and Git whitespace checks passed.

Final packaging recheck: a forced reinstall in the first test venv failed when
this shell omitted workspace TEMP/TMP; pip used a protected Windows temporary
directory and left invalid-distribution warnings. No cleanup of unrelated
directories was attempted. A fresh `tmp/m5-final-wheel-venv` with workspace
TEMP/TMP installed the locked runtime and final wheel using the same offline
commands above and passed `pip check` without those warnings. Every installed
`.py` file was compared byte-for-byte with `src/ruleaudit/`; all matched.
The entire `-I` validation/derive/audit/replay/reduce/replay journey was repeated
from the empty working directory under new `artifacts/m5-final-clean-*` paths.
All commands exited 0; artifacts confirm **26/26 verified rules**, **4/4 qualified
synthetic audit findings**, **9 -> 5 nodes with delta 2**, and verified audit and
reduced replays. The final console entry point reported `ruleaudit 0.1.0`.
Archive inspection confirmed the reduction config, schema and saved v2 fixture
in the sdist, and exact current source in the wheel. Whitespace/local links
passed across 61 source/doc/config/test files after normalizing the new config
from Windows CRLF to LF.

M6 controlled evaluation, >=100 labeled scenarios, independent held-out inputs,
pilot sizing and the research report remain. Windows/Python 3.12 is exercised;
Linux remains unverified.
