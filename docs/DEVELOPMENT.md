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
