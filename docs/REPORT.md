# Peephole rule-removal audit: research report

Draft, 2026-10-23. The implementation, full synthetic matrices and primary
held-out run are verified; source matrices are still executing. Source conclusions, representative
reruns, final resource totals and the completion audit remain pending. Numerical
results below identify their completed scope explicitly.

## Question and claim boundaries

Can short alternative derivations guide discovery of reproducible inputs on
which removing a rule worsens a bounded deterministic optimizer's output?
This project implements that diagnostic workflow and compares random,
target-pattern-only and intermediate-overlap-guided generation. It distinguishes
semantic equality, a checked realizable path and empirical removal usefulness.
The output cost is tree operator count, not measured machine-code runtime.

The observation that redundant rules can help under resource limits is prior
work: [Enumo, Section 4.3](https://rtjoa.com/papers/oopsla23-enumo.pdf) discusses
useful redundancy. Rule inference/selection through derivability is established
by [Ruler](https://cnandi.com/docs/oopsla21-cr.pdf), and composition/cycle analysis
is established by [termination checking](https://people.cs.rutgers.edu/~santosh.nagarakatte/papers/icse2016-alive-loops.pdf).
This tool does not claim a new theory of redundancy, new two-step composition,
or a guarantee that production rule deletion is safe.

## Executable model

Expressions are immutable trees over variables, unsigned 32-bit constants,
add/sub/and/or/xor/not with total modular semantics. Matching is ordered and
structural, including repeated metavariables and constant-only bindings. There
is no implicit folding, commutative matching, SSA sharing, memory, control flow,
floating point, shifts, division or LLVM poison/undefined behavior.

Z3 checks rule identities, each instantiated alternative step, endpoint equality
and paired output equivalence under finite timeout/call budgets. Unknown,
timeout and search exhaustion are inconclusive. This follows the discipline
of explicit semantic checking illustrated by
[Alive](https://people.cs.rutgers.edu/~santosh.nagarakatte/papers/alive-pldi15.pdf),
with a substantially narrower total-tree domain.

The optimizer visits preorder or postorder, left-to-right, applies the first
matching rule in the declared priority and restarts at the root. Successful
rewrites consume H, including identity/cycle steps. Operator growth/depth and
elapsed limits are explicit. Each removal pair uses the identical input,
schedule, H and limits, excluding exactly one target while retaining other
rule priorities. An incomplete or semantically inconclusive pair is excluded
from the comparable denominator and retained in raw data.

Alternative discovery is bounded forward search of one/two steps, excluding the
target. Expression metavariables become opaque placeholders; constant bindings
come from the recorded finite domain. A found template covers those listed
specializations, not every instance of the source rule. The guided generator
requires a checked two-step intermediate and an overlapping competing scheduled
match. It has no random/target fallback; one-step-only templates cannot generate
guided cases in this implementation. Both baselines lack derivation access for
input generation. All modes pay for the same bounded preprocessing.

Witnesses preserve corpus/config/input/provenance, alternative evidence and
both traces. Replay regenerates seed/attempt input provenance and recomputes
the evidence. Reduction accepts only strict decreases of its recorded measure
that preserve the positive comparable delta and the original alternative's
applicability; every accepted shrink is rechecked. This is bounded greedy
reduction, not a global minimum.

## Corpus and controls

The source subset contains 26 normalized JOG rules at revision
`3011b9de21eae081448517fc77a85f4e8d5113d0`, with per-rule source/location,
original/normalized form, restrictions and redistribution metadata. Screening
covered only AddNodeExample.java and SubNodeExample.java; 94 scoped exclusions
are recorded. It did not screen the whole repository. The subset favors
guard-free supported syntax and can bias coverage. Its total-tree identities
do not reproduce JOG compiler applicability/profitability conditions. See
[the corpus record](../corpus/README.md) and the original
[JOG paper](https://users.ece.utexas.edu/~gligoric/papers/ZhiqiangETAL23Jog.pdf).

Two constructed corpora are separate controls. With `ONE=add(X,0)` and
`TWO=add(ONE,0)`, the budget fixture has A:TWO->X, B:TWO->ONE, C:ONE->X.
At H=1/preorder/A-first, removing A leaves an unfinished two-step replacement;
H=2 catches up. The interference fixture adds D:ONE->TWO before C, allowing
B,D to alternate without finishing C. Other schedules can make both arms
equally good or equally bad. These are teaching controls, not production
compiler discoveries or evidence of global novelty.

The fixed correctness dataset has 112 labeled parameterized scenarios:
36 modular boundary cases, 16 guards, 12 structural matches and 48 paired
schedule/budget cases. Expected values use fixed tables and hand-derived
recurrences, not optimizer-generated labels. They are separate from empirical
case denominators. The latest full regression passed 347 tests in 68.70 s;
Ruff/format/mypy and clean-wheel checks passed. Detailed actual commands and
intermediate failures are in [DEVELOPMENT.md](DEVELOPMENT.md).

## Fixed evaluation protocol

The main grid uses all 26 source targets, five seeds (0–4), H=1/2/4/8, both
traversals, corpus priority/one seeded permutation, and all three modes:
6,240 source plus 480 synthetic trials. Each trial has a four-case ceiling,
64 generation attempts, the five boundary constants, hole/not/add-left/add-right
contexts, input 63 nodes/depth 5 and shared work/time/solver bounds. Actual
coverage can be smaller; identical caps do not imply equal tested counts.
Trials are independently shuffled. Five source batches retain all targets and
non-winning seeds. Full settings and pilot-based time/disk estimates were
fixed before full execution in [EVALUATION_PROTOCOL.md](EVALUATION_PROTOCOL.md).

The held-out check uses random generation without targets/derivations, depth 4,
hole only, five disjoint seeds and 2,000 unique trees per seed. Every selected
target uses the same saved ordered trees (10,000 seed/input slots; cross-seed
duplicates are possible), checked against actual audit input hashes. Target
selection used bounded derivation strata before those inputs existed: Add5,
Add2 as an explicitly empty one-step-stratum fallback, then Add3. The catalog
found two-step templates only for Add5/Add6, and no one-step template under
its bounds. It does not prove the other rules non-derivable. A separate
100-case/seed-424242 resource pilot preceded final held-out caps.

Rates distinguish all positive deltas/comparable cases from qualified positive
deltas/eligible cases. An eligible case has a checked initial alternative even
when its delta is zero. The H>=4 primary stratum is an operational convention,
not proof that scheduling caused a positive delta; budget effects can remain.
Zero denominators are null. No finding leaves time/trial/attempt-to-first
censored, not zero. Unique keys include input, target, corpus, actual schedule,
H and run limits, deduplicating generator/seed only. Missing reports and
unstarted cells are not imputed as zero. Search query/unknown counters, replay
outcomes and shrinking counters retain separate scopes.

## Completed full synthetic results

Both grids visited all 240 declared trials, with no unstarted cells. Counts
below include all seeds and all schedules/H; rates in the last column use only
the H>=4 eligible stratum. Positive counts include unqualified deltas.

| Fixture / mode | Tested pairs | Positive deltas | Eligible cases | Primary rate |
|---|---:|---:|---:|---:|
| Budget / random | 320 | 0 | 0 | null |
| Budget / target | 320 | 20 | 320 | 0 |
| Budget / guided | 32 | 4 | 32 | 0 |
| Interference / random | 320 | 9 | 0 | null |
| Interference / target | 320 | 80 | 320 | 0.25 |
| Interference / guided | 320 | 80 | 320 | 0.25 |

All 80 budget guided trials were partial generation runs; they remain in the
denominator records, including zero-coverage cells. The interference trials
were all complete. Budget had 24 original/9 reduced witnesses, interference
169 original/40 reduced; all **242/242** emitted witnesses verified. The nine
random interference findings have no checked initial alternative. These results
do not show a guidance advantage over target-only generation. They demonstrate
that the declared model distinguishes the two constructed effects and preserves
replayable evidence.

Budget evaluation work took 43.834 s wall / 31.625 s CPU and produced 2,795,857
bytes; interference took 69.825 s / 53.828 s CPU and 5,914,717 bytes. Driver
wall times, including process startup/publication, were 45.102/71.203 s.
These structural experiments do not measure compiled-program runtime.
Exact raw metrics/cases and every emitted witness are preserved under
[results](../experiments/results/), with hashes and read-back-verified archives.

## Completed primary held-out results

All 15 declared target/seed trials were visited. Fourteen tested the complete
2,000-input sequence; Add5/seed 100003 stopped at position 748 after one paired
semantic unknown. The five saved seed sequences contain 10,000 slots and 9,425
globally unique input hashes (575 cross-seed repeated slots). Counts below retain
the partial prefix and exclude its unknown from comparable cases.

| Target | Tested / comparable pairs | Positive deltas | Eligible cases | Qualified deltas |
|---|---:|---:|---:|---:|
| Add2 | 10,000 / 10,000 | 6 | 0 | 0 |
| Add3 | 10,000 / 10,000 | 4 | 0 | 0 |
| Add5 | 8,748 / 8,747 | 0 | 7 | 0 |

All ten unqualified original witnesses verified on replay; no reductions were
eligible. Add5's primary rate is 0/7, while Add2/Add3 rates are null. Seven
eligible cases are too few to support a broad generalization claim. The
result neither establishes absence of other alternatives nor safe deletion.
The primary tested total is **28,748**, not the planned 30,000 ceiling. Root
work took **290.878 s wall / 281.453 s CPU**, producing **25,281,386 bytes**;
driver wall was **292.570 s**. Search counters recorded 59,092 calls and one
semantic unknown, separately from replay query costs.

A preregistered supplemental coverage pass will attempt only the untouched
1,252-input Add5 suffix after the main matrices, using the same frozen settings.
It will retain the original unknown and report separately; the original primary
table above will not be replaced by a more favorable retry. Its outcomes are
not yet measured.

## Pending final results and reproducibility checks

Supplemental held-out and full source results, per-target/per-seed distributions, deduplicated
yields, alternative-length yields, time-to-first/reduction/resource summaries,
representative saved-seed reruns, and final replay coverage remain to be filled
from terminal outputs. No source effectiveness conclusion is drawn yet.

Execution is frozen at code `9ae9254`, with source/config/corpus/lock hashes in
[the run manifest](../experiments/full-run-manifest.json). The environment is
Python 3.12.14, Z3 5.3.1.0, Windows AMD64, 12 visible logical processors and
8,216,317,952 physical-memory bytes. Timings come from an interactive OneDrive
workspace; peak memory and four-core performance were not measured. Linux was
not exercised. These remain limitations rather than inferred achievements.

## Threats to validity

The convenience subset and tiny four-case main cells limit external validity
and rare-event power. Finite constants, opaque placeholders, two-step search
and syntactic matching limit derivation coverage. Guided two-step/overlap
requirements can produce very low coverage; a partial generator is not a
completed equal-count comparison. Resource outcomes can vary with host load.
Synthetic construction favors the effects it was designed to demonstrate.
No statistical significance, production runtime benefit, whole-rule redundancy,
global minimality or safe deletion follows from these observations.

The [14-paper research record](RESEARCH.md) documents related methods and access
limits, including Optgen's incomplete full-text access and KBC's preprint status.
Implementation-stage checks retrieved 13 PDFs and inspected relevant passages/
abstracts; this is not an exhaustive novelty search or a new full rereading.
The proposed contribution is the evaluated, auditable diagnostic workflow;
claims must remain narrower than the actual model and measured data.
