# Product requirements: Peephole Rule Removal Audit

Status: **all six milestones implemented and verified**. Prepared 2026-10-22.
The user explicitly authorized all six milestones and periodic GitHub pushes on
2026-10-22. Verification remains required at each milestone.

## 1. Project overview and summary

A local command-line research tool that identifies short alternative derivations
for peephole rules and tests the operational consequences of removing those rules
from a small deterministic optimizer. It produces checked derivation witnesses,
replayable removal-regression witnesses, and comparisons of test generators.

Confirmed by the user: use the project from the latest slides; implement a Python
CLI; reuse this repository; establish documentation and review the plan before
application implementation. No current deadline or daily effort is specified.

The contracts below guide implementation. P0 means required for the research MVP,
P1 follow-up, P2 optional. Consequential contract changes still require review.

## 2. Problem statement and motivation

A rule can be reproduced by other rules yet remain useful in a bounded optimizer:
the replacement may require more steps or a competing rule may interfere with it.
Composition and this general observation are prior art. The proposed project
investigates a narrower question: can alternative derivations guide the generation
of understandable, reproducible examples of worse optimization after removal?

See [docs/RESEARCH.md](docs/RESEARCH.md) for the 14-paper basis and limits of claims.
The intended contribution is an evaluated diagnostic workflow, not a new theory
of redundancy or a guarantee that rule deletion is safe.

## 3. Goals and measurable success criteria

- For supported inputs, replay every emitted witness and reproduce its trace,
  stop reason, and output operator count, excluding timing metadata.
- Search for replacements of length 1 or 2 without using the removed rule.
- Distinguish verified, disproved, unsupported, unknown, and not-found-within-bounds.
- Implement three test generators and compare them under identical declared limits.
- Aim for 20–30 attributed supported rules and at least 100 labeled test scenarios;
  report actual supported counts and exclusions. Synthetic fixtures are separate.
- Demonstrate budget-only and scheduling-interference fixtures. Report measured
  real-corpus outcomes even if no real-corpus regression or guided advantage is found.
- No positive effect size is a completion requirement. Honest negative results count.

## 4. Target users

Primary: the student researcher preparing experiments and presenting the project.
Secondary: a professor/reviewer who needs to inspect assumptions and replay evidence.
Potential future user: a compiler engineer assessing a rule library; production
compiler integration is outside this MVP.

## 5. User stories and journeys

1. As a researcher, I normalize and attribute a rule corpus, run validation, and
   inspect invalid or unsupported rules before experiments.
2. I select a target rule, obtain a bounded alternative derivation, and inspect
   which conditions and bindings make it applicable.
3. I audit that target with fixed schedules, inputs, and budgets. I inspect both
   optimizer traces when removal increases final cost.
4. I replay and reduce a witness, then compare generator results from recorded seeds.
5. A reviewer receives a corpus, configuration, witness, and environment manifest
   and reproduces the evidence offline after installing dependencies.

## 6. MVP scope and explicit non-goals

P0: expression-tree IR; validated JSON corpus; SMT rule checking; bounded derivation;
deterministic rewriting; paired audits; three generators; replay; bounded reduction;
JSON/CSV reports; controlled evaluation and documentation.

Non-goals: web/desktop UI, accounts, database, cloud, LLVM/JVM integration, automatic
production rule deletion, unrestricted Java/LLVM parsers, complete symbolic rule
composition, equality-saturation implementation, machine-code generation, and
claims about measured program runtime. Exclude memory, control flow, floating
point, division, shifts, LLVM poison/undefined behavior, and shared SSA DAGs.

## 7. Functional requirements

| ID | Priority | Requirement |
|---|---|---|
| FR-01 | P0 | Load and strictly validate versioned JSON rule/config/expression files. |
| FR-02 | P0 | Implement explicit 32-bit modular expression semantics and operator cost. |
| FR-03 | P0 | Validate supported rules and instantiated derivations with Z3 and bounded calls. |
| FR-04 | P0 | Find one/two-step replacement paths excluding the target rule. |
| FR-05 | P0 | Run deterministic, traceable bounded rewriting. |
| FR-06 | P0 | Audit identical inputs with/without exactly one target rule. |
| FR-07 | P0 | Generate random, target-pattern-only, and derivation-guided inputs. |
| FR-08 | P0 | Write versioned, attributable reports and replay witnesses. |
| FR-09 | P0 | Reduce witnesses while preserving the regression and valid evidence. |
| FR-10 | P0 | Compare generators with controlled budgets and transparent metrics. |
| FR-11 | P0 | Provide offline CLI help, diagnostics, predictable exits, and resource controls. |
| FR-12 | P0 | Maintain a reviewed corpus with provenance and licensing records. |
| FR-13 | P1 | Add a production compiler adapter after defining its semantic differences. |
| FR-14 | P2 | Provide an optional read-only HTML report or GUI. |

## 8. Acceptance criteria

| ID | Observable acceptance criteria |
|---|---|
| FR-01 | Reject duplicate JSON keys/rule IDs, unknown fields/operators, unbound RHS/guard variables, malformed types, and exceeded limits; show field path and reason without a traceback by default. |
| FR-02 | Independent evaluator passes wraparound, repeated-variable, bitwise, and nested-expression fixtures; variables/constants cost 0 and each operator node costs 1. |
| FR-03 | A known valid rule is verified, a deliberately invalid rule has a replayable valuation counterexample, and timeout/unknown/unsatisfiable guards never count as verified usable rules. |
| FR-04 | Recover constructed A-via-B-C and direct alternatives, reject paths using A, check every step/guard, require structural endpoint equality to the instantiated A RHS, and label bounded misses as inconclusive. |
| FR-05 | Hand-authored preorder/postorder and priority fixtures match expected traces; repeated runs produce identical semantic results; budget and growth limits stop correctly. |
| FR-06 | Both runs share input, rule ordering minus A, traversal, H, growth limits, and semantics; positive delta = cost(without A) - cost(with A); no different random seed or rule reorder in one arm. |
| FR-07 | All modes are seed-repeatable; baseline modes do not inspect derivations; guided mode records its path and competing-match evidence; exhausted generation yields explicit partial status. |
| FR-08 | Reports include necessary input/config/corpus snapshots and hashes; replay checks them and recomputes traces/costs; altered hashes or unsupported schema versions fail clearly. |
| FR-09 | Every accepted reduction strictly decreases a declared size measure and is rechecked; output replays; timeout returns the last verified candidate; do not claim globally smallest witnesses. |
| FR-10 | Produce per-seed/per-target/per-schedule metrics and summaries including zero findings, timeouts, exclusions, and coverage; denominators and uniqueness keys are specified. |
| FR-11 | A subprocess CLI test covers success, invalid input, partial execution, interruption, and report-path collision; audit execution makes no network requests. |
| FR-12 | Each included rule has a stable ID, source URL/revision/location, original and normalized form, semantic restrictions, and license/redistribution review; unsupported rules are listed with reasons. |

## 9. UI/UX requirements

Terminal interface only. Use standard argparse help, text errors on stderr, and a
brief result summary on stdout. Do not use color as the only status signal. JSON
and CSV supply machine-readable results. No screens, authentication states, or
browser navigation are needed.

States: validating, running with optional stderr progress, completed, completed
with zero findings, partial/inconclusive, interrupted, and failed. Error messages
must identify the action to fix the problem. No fabricated percentage completion.

Proposed exits: 0 completed (including zero regressions), 2 invalid input/config,
3 incomplete due to declared limits or solver inconclusiveness, 4 I/O/internal
failure, 130 interrupted. Findings themselves are data, not process failures.

## 10. Data and semantic contracts

### IR and rules

M1's concrete runtime JSON shape and canonical encoding are specified in
[docs/EXPRESSION_FORMAT.md](docs/EXPRESSION_FORMAT.md): a version-1 envelope
containing an `expression`, tagged `op` nodes, and ordered `args` for operators.

Runtime expression tags: `var(name)`, `const(value)`, binary `add/sub/and/or/xor`,
unary `not`. Constants in JSON are integers in [0, 2^32-1]; Python booleans are
not accepted as integers. Runtime variables are mathematical unknown bit-vectors,
not source-code identifiers to execute. Arithmetic wraps modulo 2^32.

Rule patterns additionally support metavariables explicitly classified as
expression-valued or constant-valued. Repeated metavariables must match identical
subtrees. RHS/guard metavariables must be bound on the LHS. Guards are conjunctions
of equality/inequality between constant metavariables and literal constants;
inequality means `!=`, not signed or unsigned ordering. No hidden canonicalization,
commutative matching, or constant folding: any rewrite must be a declared rule.

For SMT validation, expression metavariables are arbitrary 32-bit values. Check
guard satisfiability and then guard AND (LHS != RHS); UNSAT for the latter proves
equivalence under those semantics. UNKNOWN is not a proof. SMT validation does
not establish that an optimizer will choose a path.

### Bounded derivation contract

M3's concrete search bounds and template-record contract are recorded in
[docs/DERIVATION_FORMAT.md](docs/DERIVATION_FORMAT.md).

The MVP uses forward syntactic matching and substitution, not complete general
composition/unification. Start from a target pattern with symbolic expression
placeholders and a bounded enumeration of constant bindings. Remaining expression
placeholders are opaque: matching must not specialize them silently. Apply other
rules at explicit expression-tree positions for at most two steps. Intermediate
guards must evaluate for the constant binding; the endpoint must structurally
equal the instantiated target RHS. Verify semantics separately.

Witnesses record constant bindings, residual symbolic placeholders, rewrite
locations, substitutions, and guard checks. They are valid only for their declared
specialization/template scope, not automatically for every instance of the original
target rule. Alternative paths requiring deeper specialization or unsupported
guards may be missed; report that limitation. Ground instances can also be checked.

### Optimizer contract

Traverse nodes in configured preorder or postorder (children left to right), try
rules in explicit priority order at each node, apply the first matching rule,
and restart traversal from the root. Count one successful rewrite as one H step,
including syntactic identity rewrites if allowed. Retain identity rules only with
an explicit warning; they can consume the budget. No implicit optimizer passes.

Stop reasons: no-match, rewrite-budget, growth-limit, time-limit, interrupted.
For a match exceeding node/depth limits, stop before applying it; do not silently
skip it for another rule. H=0 returns the input. Cycles terminate at H; cycle
annotations do not change execution. Time-limit runs are partial and not eligible
as primary comparable regression measurements.

### Reports and relationships

M3's concrete single-run configuration, snapshot/replay encoding, and explicit
storage caps are specified in [docs/EXPERIMENT_FORMAT.md](docs/EXPERIMENT_FORMAT.md).

M4 extends configuration to version 2 with shared `generation.max_nodes` (1–1000)
and `generation.max_depth` (1–64) bounds for the complete input in every mode.
Version 1 remains readable with its original defaults and target/hole generation.
`depth` still caps random/substitution expansion (0–4). Contexts are `hole`,
`not`, or `OP-left`/`OP-right` for each supported binary operator, with one bounded
generated sibling. Random and target generation receive no derivations. Guided
generation checks a concrete verified template, including its endpoint, then
requires an actual first scheduled target-free match at an intermediate state
that differs from and overlaps the next declared path step (ancestor, same node,
or descendant). Record the template, prefix, intermediate tree, expected step,
competing step and context. This is a scheduling hint; paired execution decides
whether removal hurts. No overlap or no two-step template yields explicit
generation exhaustion; there is no baseline fallback. All template scans, failed
attempts and derivation preparation count against the same end-to-end clock.
Version 2 also includes `generation.max_match_attempts` (0–1,000,000, default
100,000) for cumulative guided syntactic matching across the run; deadline and
match exhaustion stop generation explicitly with partial status. Other modes
consume zero guidance matches. This work is reported separately from solver calls.

M5's reduction and CSV contracts are specified in
[docs/REDUCTION_FORMAT.md](docs/REDUCTION_FORMAT.md). Reduction preserves the
original generated witness and records changed inputs separately. It requires a
checked original alternative, positive comparable pairs and a checked alternative
for every accepted shrink. Report-write errors must not escape error handlers;
retain available partial files and print a concise error if status cannot be saved.

M6 adds the matrix contract in [docs/EVALUATION_FORMAT.md](docs/EVALUATION_FORMAT.md).
Alternative eligibility is checked for every comparable case, including zero
deltas, separately from the legacy positive-finding attachment field. Primary
interference rates divide qualified positive findings by eligible cases at H>=4;
zero eligible cases produce null rates. Uniqueness keys include canonical input,
target, corpus, schedule, H, growth/time limits and the versioned 32-bit semantics,
and exclude generator/seed so cross-seed deduplication is explicit.
H>=4 defines an eligibility stratum; it does not itself prove interference caused
a positive delta. Budget effects may remain and require separate trace analysis.
An explicit heldout-evaluation configuration runs only random generation and
preserves concrete target-independent inputs before auditing. All selected
targets share those ordered sequences; incomplete prefixes and mismatches are
reported separately. Ordinary evaluation still compares all three modes.

A run references one corpus/configuration and contains candidates, derivations,
generated cases, paired executions, witnesses, and metrics. A witness refers to
one target, one input, and two ordered traces. Include schema/tool versions,
dependency versions, canonical corpus/config hashes, seed, generator, schedule,
H, costs, stop reasons, elapsed time, solver status, and generation provenance.
Store self-contained data snapshots for replay; never serialize executable objects.

Proposed input defaults: file <=10 MiB, <=100 rules, expression <=1,000 nodes and
depth <=64, identifier <=64 ASCII characters from `[A-Za-z_][A-Za-z0-9_]*`.
Generic JSON object field names are bounded to 64 characters before recursive
path construction; all declared schema fields and maximum-length binding IDs fit.
Proposed optimizer growth ceiling: 10,000 nodes and depth 128; H maximum 10,000.
Validate numeric settings as finite non-negative values with explicit maxima.
Defaults are reviewable implementation choices, not measurements.

## 11. API and external integrations

No HTTP API or external service. Public interface is the local CLI and versioned
JSON/CSV files. argparse handles syntax; a standard-library schema validator
handles structural validation without an additional schema-framework dependency.

CLI contracts (all six commands, full experiments and report verified):

```text
ruleaudit validate --rules FILE --out NEW_DIRECTORY
ruleaudit derive --rules FILE --config FILE --target RULE_ID --out NEW_DIRECTORY
ruleaudit audit --rules FILE --config FILE --target RULE_ID --out NEW_DIRECTORY
ruleaudit replay --witness FILE --out NEW_DIRECTORY
ruleaudit reduce --witness FILE --config FILE --out NEW_DIRECTORY
ruleaudit evaluate --rules FILE --config FILE --out NEW_DIRECTORY
```

Configuration includes generators, seeds, target IDs, traversal/priority lists,
H values, constant domains, generation/node limits, solver timeout, and run caps.
Z3 is a local library dependency. Installation may require network access;
experiment execution must not. No automatic source downloads or corpus updates.

M2 concretizes corpus/guard/provenance JSON and bounded solver/optimizer settings
in [docs/RULE_FORMAT.md](docs/RULE_FORMAT.md). These caps are implementation
limits, not measured performance claims.

## 12. Authentication, authorization, and access control

No accounts or service boundary. The local OS user controls input/output file
permissions. No elevated privileges required. Never execute content from corpora
or reports. Output paths are user-selected; data fields cannot redirect writes.

## 13. Non-functional requirements

- Security: strict parsing, resource caps, no dynamic evaluation or subprocess
  execution of inputs, no secrets, no network during experiments, safe CSV output.
- Reliability: deterministic semantic results for identical inputs/settings and
  versioned environments; atomic completed-file writes and explicit partial status.
- Performance: proposed small smoke run (<=10 rules, 100 cases, H<=8) within 60 s
  on a recorded four-core CPU/8 GB machine; measure before treating as achieved.
- Compatibility: support Python 3.12 and Windows first. Use pathlib/UTF-8 and test
  spaces and Unicode paths. Linux compatibility remains unverified until exercised.
- Accessibility: plain text help, readable tables, machine-readable files, no color dependency.
- Maintainability: typed module contracts, tests against independent expectations,
  minimal dependencies, tracked lockfiles, and documented assumptions.
- Scalability: bounded research batches, sequential execution first. No distributed
  workers or large-scale scalability commitments in the MVP.

## 14. Errors, edge cases, and failures

Reject malformed/oversized JSON, duplicate IDs, path collisions, empty rule corpus,
unknown targets, bad priorities, unsupported operators, invalid guards, and unsupported
schema versions. Empty generated-case sets are valid zero-coverage/partial results.
Remove only one target at a time; keep remaining rule order unchanged.

SMT counterexamples must be distinguishable from optimization regressions. Invalid
rules block primary experiments; an explicit supported subset must be created and
validated instead of silently dropping them. Unknown/timeouts leave affected cases
inconclusive. Report unavailable dependencies with setup instructions.

Handle no-match, cycles, insufficient budget, guarded paths unavailable, all cases
deduplicated, memory/growth limits, interrupted runs, disk errors, and incompatible
replay versions. Never overwrite an existing output directory. On interruption,
retain only explicitly marked partial reports; never publish an incomplete file
as a completed run. Bound generation attempts independently of accepted-case counts.

## 15. Testing requirements and definition of done

Unit tests: IR evaluation, matching, substitution, guards, cost, validation, traversal,
budgets, serialization, and unique-case keys. Property tests: independent modular
evaluation and rewrite preservation on generated bounded trees. Integration tests:
complete validation-to-replay and guided-vs-baseline harness. CLI subprocess tests:
exit codes, stderr/stdout, Unicode paths, malformed input, and file collisions.

Use known-invalid rules and mutated traces as negative controls. Check mocked
unknown results in unit tests and at least one real solver-backed integration run.
Hand-worked fixtures supply expected traces; tests must not copy the implementation
as their own oracle. Synthetic labels cannot establish effectiveness on real rules.

Done for a milestone: acceptance criteria addressed, relevant tests/checks actually
run, intended diff reviewed, documentation updated, limitations reported, user
review requested. A checkpoint commit follows only explicit authorization. Final
research completion also requires actual baseline comparisons, reproducible artifacts,
source attribution, and reports that separate verified observations from hypotheses.

## 16. Deployment and operations

Install a local package in a virtual environment. No deployment service, database,
migrations, or production start command. Build a wheel and verify CLI installation
from that wheel in a clean test environment at the packaging milestone.

Keep runtime/development dependency locks and record versions in experiments.
Keep generated output under ignored `artifacts/`; explicitly curate small fixtures
and reference results separately when needed. No telemetry, automatic cleanup,
external uploads, or paid services. Record hardware and wall/CPU time for evaluation.

## 17. Assumptions, dependencies, risks, and open questions

Confirmed scope is recorded in Section 1. Proposed choices: Python 3.12, standard
library CLI, Z3, pytest/Hypothesis/Ruff/mypy/build and pip-tools for development.
Exact compatible dependency versions/locks will be resolved and verified in M1,
not invented during planning. Current machine baseline is in docs/DEVELOPMENT.md.

Risks: corpus subset may be too small; guards reduce replacement coverage;
syntactic search is incomplete; guided testing may not beat baseline; artificial
fixtures may exaggerate value; reduction can lose derivation applicability; time
limits introduce noise; production IR behavior differs. Mitigate by recording
exclusions, preserving witnesses, fixed-count primary experiments, per-seed results,
independent baselines, and explicit scope limits.

Computing estimates: development 4 CPU cores/8 GB RAM/5 GB storage; evaluation
8 cores/16 GB/10 GB, no GPU/cloud needed. These are estimates, not user-imposed
resource limits. Larger resources can be used if the evaluation justifies them.
The earlier 10–30 CPU-hour estimate is provisional; pilot measurements must size
the experiment matrix before a full run. No deadline is currently enforced.

All milestones are authorized. M1 fixed exact dependencies; M2 documented the
initial source subset and redistribution review. Pilot-based experiment caps and
all primary outcomes are recorded in [the protocol](docs/EVALUATION_PROTOCOL.md)
and [report](docs/REPORT.md). User-provided Git identity and origin are configured
locally. The [completion audit](docs/COMPLETION_AUDIT.md) maps acceptance criteria
to actual evidence.

## 18. Future enhancements excluded from MVP

General symbolic unification/composition, richer predicates, longer derivations,
SSA DAGs, LLVM/Java adapters, equality saturation, machine-runtime evaluation,
parallel/distributed experiments, automatic rule-library editing, and graphical
reports. Each requires a separate scope and semantic-contract review.
