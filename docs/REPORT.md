# Peephole rule-removal audit: measured research report

2026-10-23. All six milestones, the full study, 350-test regression and final
installation/archive verification are complete. This report separates
primary measurements from supplementary coverage and reproducibility checks.

The workflow found replayable removal losses for source-derived rules with
checked two-step alternatives. In the preregistered H>=4 source stratum, guided
generation produced 32/180 qualified positive observations, versus 12/320 for
target-only generation. This is a result under the declared model and budgets,
with sparse coverage and repeated inputs; it does not establish general method
superiority or production-compiler runtime benefit. All 5,535 primary emitted
original/reduced witnesses verified on replay. A matched source example shows
an actual child rewrite blocking cancellation before the H budget is exhausted.

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

## Full source results: all 26 removal targets

All 6,240 declared source trials were visited, with no unstarted cells, against
the same complete 26-rule library. Counts are observations across actual
target/schedule/H/seed settings, not independent draws or distinct compiler bugs.

| Mode | Tested pairs | Positive deltas | Qualified positives | Eligible cases | H>=4 qualified / eligible |
|---|---:|---:|---:|---:|---:|
| Random | 8,320 | 0 | 0 | 0 | 0/0 (null) |
| Target | 8,320 | 5,137 | 86 | 640 | 12/320 (0.0375) |
| Guided | 360 | 69 | 69 | 360 | 32/180 (0.1778) |

Only Add5 and Add6 had discovered short templates under these bounds; all
eligible source cases used two-step paths. One-step empirical yield was zero,
although direct one-step discovery is exercised by independent contract tests.
The remaining targets are bounded misses, not proven non-derivable.

The H>=4 numerator was larger for guidance in this experiment. Across all H,
target-only found more qualified observations (86 versus 69). Target also
produced 5,051 positives without a checked initial alternative; these remain
separate. The sampled populations differ: there were **20 random, 510 target,
and 45 guided canonical input hashes**, reused across configurations. Guided
covered far fewer cases under the same four-case/64-attempt ceilings. These
facts limit comparisons and prevent interpreting thousands of observations as
thousands of independent inputs. Deduplicated positive configuration keys were
0/5,073/69 for random/target/guided; the key retains target and actual run settings.

All five seeds, including non-winning results, are retained:

| Seed | Target H>=4 positives / eligible | Guided H>=4 positives / eligible |
|---|---:|---:|
| 0 | 6/64 | 2/42 |
| 1 | 4/64 | 4/36 |
| 2 | 0/64 | 14/32 |
| 3 | 0/64 | 6/38 |
| 4 | 2/64 | 6/32 |

Per-target, per-seed and per-trial values/ranges are preserved in the
[machine-readable summary](../experiments/results/summary.json) and raw roots.
No significance test or population-level effect claim is made from these data.
For observed first-qualified findings across all H, target times ranged
0.695–1.107 s (median 0.759 s, 38 observed trials); guided ranged 0.539–1.058 s
(median 0.771 s, 39 observed). The other 2,042/2,041 trials were censored;
random had no qualified event. These conditional times include preprocessing
and are not uncensored all-trial performance estimates.

Positive operator deltas ranged 1–9 for target (median 2) and 1–8 for guided
(median 2). Twelve target-generated cases improved after removal (delta below
zero), and 3,171 had zero delta; all 8,320 random cases had zero delta. Guided
had 291 zero deltas. The summary retains the full positive/zero/negative scope.

Source trial statuses were 2,080 completed random; 2,047 completed/33 partial
target; 50 completed/2,030 partial guided. Partial generation and incomplete
reduction are explicit in the header bundles. There were no recorded source
search solver unknowns or replay unknown/invalid/not-run outcomes. Every one
of **5,206 originals and 77 reductions verified**. Search-phase query counts
were 233,440/235,360/218,600 for random/target/guided; they exclude replay queries.

## Reduction outcomes

Reduction selected the first qualified findings up to the declared per-trial
cap, not the smallest examples. Source target/guided reductions numbered 38/39.
Median node decreases per reduced witness were 4/2, with ranges 0–9/0–7;
unchanged results are retained. Five target and nine guided reductions completed;
33/30 were bounded partials with their last verified candidates. Shrinking used
799/727 recorded solver calls, separate from preparation and replay. All 77
source reduced envelopes independently replayed. A shrink may alter the detailed
trace while preserving the required checked path and positive delta; it is not
a proof of the same causal mechanism or a globally smallest witness.

### A matched scheduling example

The first qualified H>=4 original in sorted source batch/trial/file order is
preserved as [a self-contained witness](../tests/fixtures/source-qualified-witness.json),
with [selection](../experiments/source-example.json) and
[matched primary-cell data](../experiments/source-example-contrast.json).
It was generated by target-only mode, seed 4, H=8, postorder and the recorded
permuted priority. It is an illustrative case selected by trial/file order,
independently of delta magnitude, and is not an additional primary sample.

Let a=2147483647, b=`(x + 2147483648) xor not(z)`, c=`not(z and z)`.
The input is `(a-b)+(b-c)`. Add5 directly rewrites it to `a-c`, cost 3.
The checked alternative is Add2 at root, giving `(a+b)-(b+c)`, then Sub11 at
root, also giving `a-c`. In the actual target-free postorder run, the second
step instead moves the constant in child 0: `(a+b)` becomes `(b+a)`. That breaks
the ordered structural cancellation pattern, and the run reaches no-match at
cost 11. The with-target run reaches no-match at cost 3 after one step; the
target-free run does so after two steps, within H=8.

The existing preorder cell uses identical input/provenance and every other
config field, including rule priority and limits. Its recorded costs are 3/3
with both stops no-match. This is concrete schedule-sensitive removal usefulness
in the declared model. It is not a JOG/JVM runtime measurement or evidence about
the complete production matcher, canonicalization passes or rule library.

## Primary held-out results and explicit coverage completion

All 15 declared target/seed trials were visited. Fourteen tested their entire
2,000-input sequence; Add5/seed 100003 stopped at position 748 after one paired
semantic unknown. Five saved sequences contain 10,000 slots and 9,425 globally
unique input hashes (575 cross-seed repeated slots). The primary result remains
unchanged:

| Target | Tested / comparable pairs | Positive deltas | Eligible cases | Qualified deltas |
|---|---:|---:|---:|---:|
| Add2 | 10,000 / 10,000 | 6 | 0 | 0 |
| Add3 | 10,000 / 10,000 | 4 | 0 | 0 |
| Add5 | 8,748 / 8,747 | 0 | 7 | 0 |

All ten unqualified witnesses verified; no reductions were eligible. Add5's
primary rate is 0/7, while Add2/Add3 rates are null. Primary counts are 28,748
tested / 28,747 comparable, with nine negative and 28,728 zero deltas. Seven
eligible cases do not support a broad generalization or safe-deletion claim.

The preregistered suffix pass then attempted only Add5's untouched positions
749–2000 using the same saved trees and frozen paired settings. It completed
all **1,252 pairs**, with one eligible alternative, zero findings and zero
new unknowns, in 14.015 s wall / 13.641 s CPU. This separate coverage pass
continued individual inconclusive pairs by policy and retained the original
unknown rather than retrying it into a favorable primary result. Together,
primary prefixes and the supplement attempted all 30,000 planned target-pairs;
29,999 were comparable and the original unknown remains inconclusive. The
supplement is not pooled silently into the primary effect table above.

## Resources, reproducibility and release verification

| Primary scope | Visited trials | Evaluation work wall s | CPU s | Original output bytes |
|---|---:|---:|---:|---:|
| Synthetic budget | 240 | 43.834 | 31.625 | 2,795,857 |
| Synthetic interference | 240 | 69.825 | 53.828 | 5,914,717 |
| Source corpus | 6,240 | 7,594.233 | 6,975.234 | 619,130,893 |
| Primary held-out | 15 | 290.878 | 281.453 | 25,281,386 |

All eight commands visited **6,735 trials / 47,380 pairs** with no unstarted
cells. Whole-driver wall time was **8,046.822 s (2.24 hours)**; root work times
exclude process startup and their final summary publication. No mode receives
free derivation preparation. Base seconds/queries cap audit search; replay
uses snapshot caps and reduction has its own scope. All phases add to
end-to-end time under the overall soft matrix deadline. Native-query counters
cover search only; replay outcomes and shrinking counters remain separate.

Seven protocol-fixed saved-seed reruns reproduced all 769 common cases' inputs,
provenance, costs/stops and shared positive witness semantics, excluding timing.
Coverage and classifications also matched. The same held-out case again
returned unknown under identical caps; both outcomes are retained. All eight
new rerun witnesses verified. These checks are not additional primary samples.

The 350-test suite passed in 66.97 s, including independent arithmetic/fixture
oracles, generated rewrite preservation with an invalid-rule negative control,
tampering/error/unknown/interruption cases and the real source scheduling example.
The professor walkthrough ran all 11 listed commands successfully and independently
replayed every one of its 30 emitted original/reduced witnesses. A separate
four-rule/100-case/H8 smoke completed in 1.962 s CLI wall / 0.625 s audit CPU
under a four-logical-processor parent/child allocation probe; its one witness
verified. This is not a result on a different four-physical-core machine.

Primary witness replay was **5,535/5,535**. Raw case/header/config data and
every emitted original/reduced witness are distributed under
[results](../experiments/results/) with file/payload hashes and read-back-checked
ZIP bundles. Original CLI outputs remain untouched under ignored artifacts.
The main code is frozen at `9ae9254`; source/config/corpus/lock hashes and
exact ordered commands are in [the execution manifest](../experiments/full-run-manifest.json).
Windows Git checkout conversion was explicitly tested and fixed so stored
source/config and raw CSV hashes remain reproducible.

Environment: Python 3.12.14, Z3 5.3.1.0, Windows AMD64, 12 visible logical
processors, 8,216,317,952 physical-memory bytes. Timings are from an interactive
OneDrive workspace, with publication/curation alongside some matrix activity;
heavy native tests were deferred until the matrices finished. They are
descriptive host measurements without isolation guarantees. Peak memory,
different four-physical-core hardware and Linux runtime remain unverified.
The final runtime-only wheel installs offline with the exact runtime hash lock
and passes `pip check`. From an empty directory with isolated Python (`-I`),
all six commands pass, all 23 installed Python files match the frozen source,
pytest is absent, an extracted primary source witness replays, and all 26 newly
emitted original/reduced witnesses verify. An additional installed 100-case smoke
queries the auditing process itself: affinity mask 15 (four logical processors),
2.035 s CLI wall / 0.656 s audit CPU, one emitted witness verified. These
installation checks are supplementary and do not change primary effect estimates.

## Threats to validity

The convenience subset and tiny four-case main cells limit external validity
and rare-event power. Finite constants, opaque placeholders, two-step search
and syntactic matching limit derivation coverage. Guided two-step/overlap
requirements can produce very low coverage; a partial generator is not a
completed equal-count comparison. Resource outcomes can vary with host load.
Synthetic construction favors the effects it was designed to demonstrate.
Tree cost counts repeated occurrences separately; a shared SSA DAG can have
different costs for repeated terms.
No statistical significance, production runtime benefit, whole-rule redundancy,
global minimality or safe deletion follows from these observations.

The [14-paper research record](RESEARCH.md) documents related methods and access
limits, including Optgen's incomplete full-text access and KBC's preprint status.
Implementation-stage checks retrieved 13 PDFs and inspected relevant passages/
abstracts; this is not an exhaustive novelty search or a new full rereading.
The proposed contribution is the evaluated, auditable diagnostic workflow;
claims must remain narrower than the actual model and measured data.
