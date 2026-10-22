# Implementation plan

Status: **all six milestones authorized — M1–M5 implemented**. Prepared 2026-10-22.
On 2026-10-22 the user explicitly authorized continuation through all six
milestones, periodic pushes, and creation of a new GitHub repository with a name
other than DesiCompiler. Milestones remain sequential and require recorded
verification evidence, but no further approval is required to begin the next.
The user supplied `vaishnavtriplebytes123/peephole-rule-audit` as origin and
actual Git author details, now configured locally. The initial implementation
checkpoint contains the foundation and M1/M2. See Git history/remote state for
publication status. Unrelated coursework and reference materials remain excluded.

## Architecture and rationale

Use one typed Python 3.12 package with a standard-library CLI, JSON/CSV files,
and a local Z3 dependency. A web server, database, plugin system, dependency
injection framework, distributed runner, and external APIs add no MVP value.
Use immutable expression nodes and explicit configuration objects. Keep pure
logic independent from CLI, filesystem, clocks, and solver adapters.

The core is a small declared optimizer used as an experimental model. It is not
a replacement for JOG or a production LLVM/JVM optimizer. Match the exact
semantic and bounded-derivation contracts in PRD.md Sections 10–11.

| Component | Responsibility and boundary |
|---|---|
| `ir.py` | Typed immutable expression/pattern nodes, structural equality, independent evaluator, node/depth/operator counts. No solver or filesystem. |
| `rules.py` | Rule and guard models, syntactic matching, substitution, provenance. No hidden folding or canonicalization. |
| `io.py` | Strict versioned JSON loading, size/schema validation, canonical encoding/hashes, atomic output. No executable formats. |
| `solver.py` | Convert supported expressions/guards to Z3; validity/counterexample/unknown result types; timeout and call accounting. |
| `rewrite.py` | Deterministic traversal, first-match ordering, bounded rewrite runner, locations and traces. |
| `derive.py` | Forward one/two-step alternative search, constant specializations, endpoint checks, scoped witnesses. Excludes target. |
| `generate.py` | Seeded random/target-only/guided strategies; bounded attempts and provenance. |
| `audit.py` | Paired executions, comparable-run checks, deltas and witness construction. |
| `replay.py` | Validate snapshots/hashes and recompute evidence independently of recorded results. |
| `reduce.py` | Deterministic shrinking, revalidation, and last-verified-candidate behavior. |
| `evaluate.py` | Controlled experiment matrix and raw per-trial metrics. |
| `report.py` | Stable JSON/CSV summaries, safe text fields, no inference from missing values. |
| `cli.py` | argparse commands, exit codes, concise summaries and error mapping. |

These are module responsibilities, not a requirement to create empty stubs up
front. Split or combine small modules when justified without changing public contracts.

### Data flow

```text
Rule corpus + configuration
  -> validate structure, semantics, provenance and supported scope
  -> derive scoped replacement templates (length <= 2; target excluded)
  -> generate candidate inputs under a recorded strategy/seed
  -> run same optimizer with target / without target
  -> check output equivalence, compare costs and record status
  -> replay and reduce eligible witnesses
  -> export raw data and summaries
```

No database or migrations. Versioned JSON schemas are the data contract; reject
unknown schema versions instead of silently migrating research evidence.

### Key internal interfaces

Proposed typed interfaces; exact signatures finalized with tests in their milestone:

- `check_rule(rule, limits) -> ValidationResult`: valid, invalid with valuation,
  unknown, unsupported, or unsatisfiable guard.
- `match(pattern, expression) -> Bindings | None`; `substitute(rhs, bindings) -> Expr`.
- `run(expr, rules, schedule, limits) -> RunResult`: output, trace, stop reason,
  cost, completed/partial status, counters.
- `derive(target, rules, search_config) -> DerivationSearchResult`: witnesses,
  specialization scope, coverage and inconclusive/exhaustion metadata.
- `generate(strategy, corpus, config, seed, optional_derivations) -> cases`:
  baseline implementations receive no derivations. Guided fallbacks are labeled.
- `audit_case(case, target, corpus, config) -> PairedResult`: identical shared
  settings, per-arm results, comparable flag, semantic status, cost delta.
- `replay(witness) -> ReplayResult`: recompute and compare every claimed result.

### Guided generation, concretely

1. Take a verified alternative template for A via B/C, including the intermediate term.
2. Enumerate bounded expression substitutions and permitted constant bindings.
3. Check other rules' actual syntactic matches at intermediate nodes. Prioritize
   instances with a competing match under the selected schedule; record that match.
4. Place the instantiated target expression in bounded contexts: a hole alone,
   one unary operator, or one binary operator with a generated sibling. Check
   context and input bounds; regenerate/recheck the concrete alternative path.
5. Execute paired runs. A match is only a test-generation hint, not proof of interference.

This design avoids promising a general unifier. Include the generation cost and
unsuccessful attempts in timing/coverage reports. If no overlap candidate exists,
report that fact; any target-only fallback must be separately labeled and excluded
from claims about overlap guidance.

## Ordered milestones

Each milestone starts with Git status and relevant PRD review, uses behavioral
tests before implementation, and ends with actual verification evidence, diff
review, updated documentation, and reviewable checkpoints. Commits/pushes follow
the user's standing authorization. Dependencies are sequential except independent
documentation within an approved milestone.

### M0 — Foundation and approval

- Deliverables: README, PRD, AGENTS, ignore/environment template, this plan,
  development baseline, research references, reusable workflow prompts.
- Verification: all expected files exist; Markdown links resolve locally; no
  unrelated changes or secrets introduced; ignore behavior keeps future code,
  tests, corpus, configs and lockfiles trackable; no duplicate Git repository.
- Acceptance: user reviews the proposed contracts and approves the plan or requests changes.
- Approval: user explicitly authorized all six milestones and periodic pushes,
  supplied the GitHub destination and author identity; checkpoint commits exist.

### M1 — Reproducible environment and bounded IR

- Depends on M0 approval. Requirements FR-01/02/11 (foundation portions).
- Deliverables: pyproject.toml, `src/` package, pytest setup, typed IR, independent
  evaluator, strict JSON expression validation, initial `--help`/`--version`,
  runtime/development requirements inputs and exact locks, updated setup instructions.
- Proposed dependencies: runtime `z3-solver`; dev `pytest`, `hypothesis`, `ruff`,
  `mypy`, `build`, `pip-tools`. Resolve compatible exact versions at setup, retain
  transitive locks, and record Python/tool versions. No unrelated dependency installs.
- Tests first: overflow/underflow, constants at boundaries, bitwise operators,
  bool-vs-int rejection, duplicate JSON fields, malformed/deep/oversized inputs,
  non-ASCII filesystem paths and deterministic serialization.
- Acceptance: independent evaluator and input contracts pass; editable install
  exposes help/version; Ruff, mypy, pytest and package build run successfully.
- Verification: development commands below; do not claim full CLI workflows exist yet.

### M2 — Validated rule corpus and deterministic optimizer

- Depends on M1. Requirements FR-02/03/05/12 and rule-specific FR-01.
- Deliverables: matcher, substitution, constant guards, Z3 adapter, trace runner,
  `validate` command, synthetic fixtures, initial reviewed corpus and exclusions manifest.
- Review normalized JOG/Alive candidates against source semantics and source
  licenses before redistribution. Cite source revisions/locations and explain
  deviations. The existing reference checkout is read-only source material.
- Acceptance: valid/invalid/unknown/unsatisfiable-guard outcomes distinguished;
  repeated metavariables and guards enforced; hand-written preorder/postorder,
  H=0/1/2, priority, no-match, identity and cycle traces match expectations.
- Tests: real Z3 integration plus injected timeout/unknown adapter outcomes;
  independent expression evaluation; growth limits; rule input errors and CLI exits.
- Risk gate: if fewer than 20 compatible rules exist, report actual coverage and
  propose a scope adjustment; do not disguise synthetic rules as corpus evidence.

### M3 — Bounded derivation and paired removal audit

- Depends on M2. Requirements FR-04/06/08 (initial), FR-11.
- Deliverables: scoped derivation search; `derive` and `audit`; target-only generator
  for initial cases; snapshots, hashes, traces, JSON output; `replay` command.
- Acceptance: A/B/C fixture produces a two-step witness. With H=1 the target-free
  run has higher cost; with H=2 it catches up. A/B/D/C interference fixture
  reproduces a worse result at H>=4 despite a two-step alternative. Both are
  explicitly synthetic. Each witness states specialization scope.
- Tests: target excluded at every step, structural endpoints, unavailable guards,
  case with no bounded path, identical paired settings, replay tampering,
  invalid/unknown semantic checks, empty findings and output collisions.
- Verification: complete validate -> derive -> audit -> replay subprocess journey;
  full automated checks. Report any real-corpus findings separately.

### M4 — Guided generation and fair baselines

- Depends on M3. Requirements FR-07/10 (generation portions).
- Deliverables: random, target-pattern-only, and derivation/overlap-guided modes;
  provenance, seed records, uniqueness keys and attempt counters; baseline isolation tests.
- Acceptance: all strategies repeat semantic output for a seed; random/target-only
  do not use derivation data; guided candidates expose their intermediate matching
  evidence; no silent fallback; budgets cap both execution and generation work.
- Tests: known overlap case, no-overlap case, guard-unsatisfiable substitutions,
  duplicate generation, bound exhaustion, contexts and competing ancestor matches.
- Verification: small equal-budget comparison on synthetic and initial corpus cases;
  no requirement that guided generation wins.

### M5 — Witness reduction, reporting, and CLI robustness

- Depends on M4. Requirements FR-08/09/11 and completed error contracts.
- Deliverables: `reduce`; JSON/CSV summaries; bounded deletion/subtree/constant
  reduction; revalidation; interruption/partial output handling; public schema docs.
- Acceptance: reductions keep target derivation applicable and positive paired
  delta, and recheck semantics; strict decreasing size measure ensures progress;
  replay rejects hash/trace/cost tampering. CSV cannot turn text fields into formulas.
- Tests: reduction that must be rejected because it loses the target/path, disk
  failure, interruption, pre-existing output path, unsupported schema and malformed witness.
- Verification: full tests/checks, wheel build and clean-wheel-install smoke demo.

### M6 — Evaluation, reproducibility, and research report

- Depends on M5. Requirements FR-10/12 and remaining research acceptance criteria.
- Deliverables: finalized supported corpus (target 20–30 rules), >=100 labeled
  scenarios across fixture categories, pilot measurements, versioned experiment
  configs, raw results, summaries, replayable witnesses and documented limitations.
- Run synthetic fixtures separately from the supported real-rule corpus. Keep a
  held-out corpus of generated expressions independent of guidance tuning.
- Acceptance: all three strategies evaluated under controlled settings; zero
  findings and all partial runs visible; replay rate and actual resources measured;
  manuscript/demo claims match raw results. Review corpus inclusion/exclusion bias.
- Verification: rerun representative saved seeds; replay all emitted final
  witnesses; full tests/checks; clean installation and professor-facing demo.
- Before a costly full matrix, report the pilot-based time/disk estimate and
  configured caps. No external spending/services without authorization.

## Evaluation protocol proposed for M6

Pilot preregistration (2026-10-23, before pilot execution): versioned
`experiments/pilot-{jog,budget,interference}.json` use seed 0, H=1/4, both
traversals and corpus/seeded-permuted priority, all three generators. Source
targets are chosen structurally: lexicographically first Add and Sub IDs, then
the remaining rule with most constant metavariables (ID breaks ties), not from
removal outcomes. There are 72 source and 24 trials per synthetic fixture.
Shared caps: 4 cases, 64 generation attempts, depth expansion 2, complete inputs
63 nodes/depth 5, five boundary constants, four contexts, 10,000 guidance matches;
search 256 states/10,000 matches/64 bindings/5 s; 5,000 solver calls at 1,000 ms;
optimizer 2 s per arm, 1,000 nodes/depth 32; 15 s per trial. Each pilot command
caps elapsed time at 600 s and total output at 128 MiB. Replay every emitted
witness; reduce the first qualified finding per trial with 32 attempts/8 accepted
shrinks/2 s/200 solver calls, then replay it. No full-matrix caps or claims are
fixed until these pilot time/disk costs are recorded.

The measured pilot and resulting fixed main matrix are now recorded in
[docs/EVALUATION_PROTOCOL.md](docs/EVALUATION_PROTOCOL.md). That protocol
supersedes the provisional 10,000-pair and H=16/32 ceilings below; the older
proposal is retained here to make the pre-full-run resource adjustment explicit.

- Primary search comparison: each target/schedule/H/seed/strategy receives the
  same maximum 10,000 paired executions, attempt ceiling, and time ceiling.
  A pair means two optimizer runs. Record unique and total attempted cases.
- Provisional seeds: 5 fixed values. H: 1, 2, 4, 8, 16, 32. Primary interference
  analysis uses H>=4 and cases with a checked <=2-step alternative; distinguish
  simple budget-only examples. Traversal: preorder/postorder. Priority: fixed
  corpus order and one seeded permutation, at most four schedule combinations.
- Random: bounded supported trees. Target-only: target-pattern instantiations
  and contexts without derivation access. Guided: same allowed domains/contexts
  with intermediate-overlap prioritization. Preserve equal domain and size bounds.
- Test generation depth initially <=4. Constant domains explicitly recorded and
  include boundary values. Held-out set: 2,000 expressions/seed x 5 seeds, generated
  independently and evaluated on the chosen targets with identical paired settings.
- Pilot adjusts matrix size/caps before the full run, not after observing winners.
  Record any protocol changes and why. At 30 targets x 4 schedules x 6 H x 5
  seeds x 3 modes x 10,000 pairs, the upper bound is 108 million pairs; this is
  a ceiling, not a promised run. The earlier 10–30 CPU-hour estimate is unverified.
- Report preparation/search cost separately and end-to-end time including derivation
  discovery; don't give guided testing free preprocessing in time-to-finding claims.
- Metrics: unique regression inputs per target/config; total tested/unique cases;
  finding rate with explicit denominator; trials/time to first finding (absent is
  censored, not zero); output cost delta; reduced node counts; replay success;
  solver unknown/timeout counts; one-step vs two-step yield; partial/excluded counts.
- Unique regression key: canonical input hash + target ID + corpus hash + schedule
  + H + semantic/growth settings. Cross-seed aggregates deduplicate explicitly.
- Retain raw per-seed metrics and report distributions/ranges; do not claim
  statistical significance from a tiny sample or omit non-winning seeds.

## Validation commands and evidence

See docs/DEVELOPMENT.md for commands and detailed evidence. Tests, lint, typing,
builds and CLI checks now exist. Remaining milestone capabilities must not be
inferred from these foundation/core checks.

| Milestone | Status | Evidence / remaining gate |
|---|---|---|
| M0 | Complete | All six milestones and periodic pushes explicitly authorized; foundation evidence in docs/DEVELOPMENT.md. |
| M1 | Complete | Python 3.12.14 venv, exact runtime/dev SHA-256 locks (23 dev-environment packages), hash-required reinstall and editable installation verified. Typed IR/input contracts, help/version, Ruff, mypy and sdist/wheel build pass. |
| M2 | Complete | 95 tests pass in the locked environment; Ruff/format/mypy/build pass. Matcher/guards/solver/optimizer and validate CLI verified; 26/26 source rules verified, 94 scoped exclusions recorded. Commands/evidence in docs/DEVELOPMENT.md. |
| M3 | Complete | Derive/audit/replay CLI, strict config, seeded target generation, paired runs, snapshots/hashes and independent replay implemented. Full 146-test regression including saved-v1 replay passes; Ruff/mypy/build and manual CLI journey pass. Synthetic H=1/2 and H=4 criteria reproduced; 9/9 manual witnesses replayed. Detailed commands/results in docs/DEVELOPMENT.md. |
| M4 | Complete | Seeded random/target/guided modes, shared complete-input/attempt/work bounds, explicit contexts/overlap provenance, independent replay and no-fallback tests. Twelve equal-cap smoke trials on synthetic/source corpora; 49/49 emitted witnesses verified on sequential replay, with an earlier inconclusive replay retained in the record. Checks and limits in docs/DEVELOPMENT.md and experiments/README.md. |
| M5 | Complete | Original/reduced witness replay, deterministic shrinking with strict decrease and path/delta/SMT checks, last-verified interruption behavior, bounded JSON/CSV and guarded status errors. 210 tests, Ruff/format/mypy and build pass; offline clean-wheel CLI journey passes. Saved 9-to-5-node reduction retains delta 2. Commands/results in docs/DEVELOPMENT.md. |
| M6 | In progress | Comparable-case eligibility metrics and bounded evaluate CLI verified; 227 tests pass. Pilot executed all 120 trials, recorded 360 pairs and verified all 48 emitted originals/reductions. Main matrix/caps fixed from measured pilot in docs/EVALUATION_PROTOCOL.md. Labeled scenarios, independent held-out data, full runs and research report remain. |

## Security and operational risks

JSON files can cause parser/memory pressure: bound file size before parsing and
depth/node counts before recursive processing; map parser recursion errors to
input errors. Use capped solver calls and experiment deadlines. Treat unexpected
solver failure as inconclusive/failure, not a valid rule. Record all caps.
Output filenames are fixed by the application inside an explicitly selected new
directory; rule IDs cannot be filenames or path fragments. CSV text is escaped
against spreadsheet formula interpretation. No executable deserialization.

## Decisions and review gates

- Confirmed: Python CLI research scope and reuse of current repository.
- Proposed: semantics, limited search, toolchain, module boundaries, milestone order,
  output contracts and experimental defaults in this plan/PRD.
- No deadline/date or hardware restriction imposed by the user.
- Git uses the existing `master`; origin is the user-provided
  `https://github.com/vaishnavtriplebytes123/peephole-rule-audit.git`.
  `git ls-remote origin` confirmed an empty repository. Commit attribution is
  configured repository-locally from the user's explicit values. Preserve the
  existing branch; do not create another repository or alter global identity.
- Continuation through all six milestones and creation of a new repository are
  authorized. Record verified destination/account attribution before publishing.
