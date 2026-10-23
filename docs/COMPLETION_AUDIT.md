# Completion audit

All six authorized MVP milestones are implemented. Application source remains
byte-identical to frozen commit `9ae9254`; final changes publish evidence, tests
and documentation. This inventory maps the original requirements to actual
verification, with unmeasured platform/research claims explicit.

## Product acceptance criteria

The final full suite (`python -m pytest --basetemp=tmp/pytest-final-all`) passed
**350 tests in 66.97 s**. Test files below are under `tests/`; implementation is
under `src/ruleaudit/`. Tests include real Z3 integration and injected unknown,
deadline and I/O failures, with independent arithmetic/fixture expectations.

| Requirement | Authoritative evidence | Outcome |
|---|---|---|
| FR-01 strict inputs | io/corpus/config parsers; test_io, test_corpus, test_rules, test_config_generate and evaluation config tests: duplicate keys/IDs, fields/operators, unbound RHS/guards, bool/int, depth/size/node/identifier and path limits | Passed |
| FR-02 total bv32/cost | Independent ir.py evaluator; arithmetic/property tests, 36 labeled word scenarios, generated rewrite preservation and deliberately invalid rewrite negative control in test_rewrite_properties | Passed |
| FR-03 SMT outcomes | test_solver: valid identity, invalid rule with independently evaluated valuation, unsatisfiable guard, unknown/query/deadline exhaustion. Actual held-out unknown retained | Passed |
| FR-04 target-free short paths | test_derive: direct/two-step, target excluded at every step, opaque placeholders, constants/guards, subtree locations, structural endpoint, bounded misses and unknown rejection. Add5/Add6 each yielded one two-step template; no direct source template found under bounds | Passed; incomplete search explicit |
| FR-05 deterministic rewriting | test_rewrite and 48 labeled pairs: priority/restart/traversal/H/growth/identity/cycles/locations/stops. Actual source postorder/preorder contrast in test_source_witness | Passed |
| FR-06 exact pairing | test_audit_replay: same input/config/seed/priority minus only target, comparability/unknown. Seven fixed reruns match all 769 common cases' inputs/provenance/costs/stops | Passed |
| FR-07 three generators | test_generation_modes: repeatability, baseline interface isolation, domains/contexts, actual overlap/provenance, no fallback and all bounds. All three modes executed across every source target and synthetic grid | Passed; sparse guidance coverage visible |
| FR-08 reports/replay | Legacy/v2 fixtures, hash/trace/cost/seed/schema/rehash tamper tests. 5,535/5,535 primary witnesses verified and archived with file/payload hashes. Clean installed CLI replayed an extracted source ZIP entry | Passed |
| FR-09 reduction | test_reduce: strict decrease, checked path/positive delta, invalid changes rejected, last verified on time/query/interruption, chain tampering. Saved 9-to-5-node result and all 77 source reduced envelopes verified | Passed; greedy, not global minimum |
| FR-10 controlled metrics | Full 6,735-trial/47,380-case records; all zeros/negatives/partials/unknown retained. Summary includes per-mode/target/seed, denominators, reuse, censoring, distributions, queries/resources/reduction. Supplements not pooled into primary samples | Passed |
| FR-11 offline/error CLI | Subprocess success/invalid/partial/real-interruption/collision tests, no overwrite, CSV escaping, disk/status/ASCII failures, socket-blocked evaluation. Isolated installed-wheel journey passes all six commands and pip check; pytest absent | Passed on Windows/Python 3.12 |
| FR-12 attributed corpus | corpus/README.md, jog.json, exclusions/license: 26 rules pinned to source revision/location, original forms/restrictions and Apache redistribution record; 94 scoped exclusions. test_curated_corpus verifies provenance/semantic identities | Passed for declared subset |

FR-13 production adapter and FR-14 GUI remain explicitly outside the MVP.

## Milestones and named gates

| Gate | Actual evidence |
|---|---|
| M0 foundation/authority | README/PRD/PLAN/AGENTS/.gitignore/.env.example, development/research/workflow and reusable prompts exist. User authorized all milestones/pushes and supplied GitHub destination and repository-local identity; unrelated coursework preserved. |
| M1 environment/IR | Python 3.12.14 venv, separate runtime/dev inputs and exact SHA locks (one runtime, 23 dev-environment packages), hash-required install, typed immutable IR/parser/evaluator/help/version/build. |
| M2 rules/optimizer | Matcher/guards/solver/trace/validate, reviewed 26-rule source subset and 94 exclusions, direct semantic/order/resource tests and actual source validation. |
| M3 derivation/audit/replay | Full command journey, synthetic H1/H2 budget and H>=4 competing expansion traces; self-contained snapshots/config/hashes/replay. |
| M4 generators | All three strategies, shared input/attempt/work ceilings, intermediate competing matches, no fallback; earlier 12-cell smoke and its initial inconclusive replay retained separately. |
| M5 reduction/reporting | Reduce/v2 chain replay, last-verified interruption, bounded atomic JSON/CSV/no-overwrite/error exits, public schemas and clean wheel tests. |
| M6 study | 112 labeled scenarios, measured pilots/estimates/preregistered full configs, 6,240 source + 480 synthetic + 15 held-out trials, complete raw data/report/resources, seven seed reruns, professor demo. All primary cells visited, partials retained. |
| Held-out coverage | Primary 28,748 tested/28,747 comparable with one retained unknown; separate untouched suffix 1,252/1,252. All 30,000 planned target-pairs attempted, 29,999 comparable; primary estimate unchanged. |
| Professor demo | All 11 commands exit 0, all 30 emitted original/reduced witnesses verified. Source postorder costs 3/11 vs otherwise matched preorder 3/3, both no-match within H8. |
| Packaging/install | Wheel/sdist build, full evidence/docs/licenses/configs/tests in sdist. Fresh offline runtime-only wheel venv passes pip check. Empty-CWD -I journey passes all six commands; all 23 installed Python files equal frozen source, pytest absent, extracted archive replay and all 26 new witness replays pass. |
| Small performance smoke | Installed four-rule/100-case/H8 audit: 2.035 s wall / 0.656 s audit CPU, completed, one witness verified. Actual auditing process queried mask 15/four logical processors on recorded 12-logical-processor host. |
| Data integrity | Independent counts/ZIP/file/payload/input-prefix checks reconcile all 6,735 trials/47,380 cases/5,535 witnesses. All 6,735 original full audits reconstruct byte-for-byte including actual config/partial reasons. Published raw Git object bytes checked against worktree. |
| Final checks/publication | 350 tests, Ruff check/format, strict mypy (source/tests/two research procedures), build, local links, LF/trailing whitespace, ignore behavior and Git whitespace pass. Intended diff/explicit staging list reviewed; final push verified through remote HEAD equality. Exact commands and earlier failures/repairs in DEVELOPMENT.md. |

## Evidence and limits

- [Report](REPORT.md): methods, synthetic/source/held-out results, all seeds,
  negative/zero cases, reuse, censoring, reduction and threats.
- [Protocol](EVALUATION_PROTOCOL.md): measured pilots/estimates, fixed caps,
  time scopes, selection and separately registered checks.
- [Results](../experiments/results/README.md): immutable primary cases/trials,
  replay ledgers, inputs, audit headers/configs, ZIP witnesses, execution/summary,
  separate supplementary and installation records.
- [Offline verifier](../experiments/verify_results.py): hashes/counts/input
  prefixes/audit reconstruction. It checks recorded replay results; fresh SMT
  replay uses the replay CLI separately.
- [Research basis](RESEARCH.md): 14-paper record and targeted source checks,
  Optgen full-text access limitation and KBC preprint; no exhaustive novelty claim.

No server/database/UI/paid service or audit networking was added. JSON stays
data; no executable rule loading, eval, exec, pickle or shell interpolation is
used to process rules. Effects/caps stay explicit. The sole runtime dependency
is the pinned local z3-solver; no secrets or automatic .env loading are required.
Original artifacts and unrelated coursework remain untouched.

Windows/Python 3.12/Unicode/space paths are exercised. Linux, peak RSS, different
four-physical-core hardware, shared SSA and production runtime remain unverified
or outside the MVP. The performance proposal was a measurement target, not a
user-imposed hardware gate. Semantic validity, derivability and usefulness remain
distinct; unknowns, bounded misses, zero results and H>=4 eligibility are never
converted into proof of safe deletion or causal interference.
