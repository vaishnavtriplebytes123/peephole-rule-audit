# Evaluation protocol and pilot record

Status (2026-10-23): runner, 112 labeled scenarios and both resource pilots are
complete; full experiments, held-out execution and final report remain. This document
fixes the main matrix before executing it. Pilot outcomes are preliminary.

## Resource pilot

The configurations were recorded in PLAN.md before execution:
`experiments/pilot-budget.json`, `pilot-interference.json` and `pilot-jog.json`.
Selection used rule structure, not removal outcomes: first Add/Sub IDs in lexical
order, then most constant metavariables with ID tie-breaking. The resulting
source targets were `jog_pAdd2`, `jog_pSub10`, `jog_pAddMoveConstantRight`.
Each uses the complete 26-rule source corpus; synthetic corpora remain separate.

| Pilot | Trials / not run | Wall seconds | CPU seconds | Output bytes |
|---|---:|---:|---:|---:|
| Synthetic budget | 24 / 0 | 7.792 | 5.359 | 335,536 |
| Synthetic interference | 24 / 0 | 10.705 | 8.156 | 571,980 |
| Source subset | 72 / 0 | 117.275 | 99.859 | 5,103,454 |

All **42 originals and 6 reduced witnesses verified** on replay. The raw pilot
record includes every case row, trial metric and replay outcome in
`experiments/pilot-results.json`; full original directories remain under ignored
`artifacts/m6-pilot-*`. Per-trial pilot `total_seconds` stops before metadata
publication; whole-evaluation wall/CPU measurements include that publication.

The primary H>=4 rate was 0 for target/guided budget cases, and 0.25 for both
target/guided interference cases. Random had no eligible initial alternatives.
The three source targets had no discovered bounded alternatives: all source
primary rates are null, even though target generation recorded 20 unqualified
positive deltas. All 24 source guided trials and 8 synthetic budget guided trials
were partial generation runs; they remain visible. No guidance advantage,
whole-rule derivability or safe deletion is established by this pilot.

Observed environment: Python 3.12.14, locked Z3 5.3.1.0, Windows AMD64,
12 visible logical processors, processor string `Intel64 Family 6 Model 186
Stepping 3, GenuineIntel`, 8,216,317,952 physical-memory bytes. CIM was
unavailable; memory was read with Windows `GlobalMemoryStatusEx`. Peak process
memory was not measured. These are interactive OneDrive-workspace timings,
not isolated compiler-runtime measurements or evidence on a four-core machine.

## Main matrix fixed after the pilot, before full execution

Use all 26 source targets and both synthetic target-A fixtures separately.
Keep the pilot's constant domain, contexts, expression/work bounds, solver caps,
search caps, per-trial limit and four-case execution cap. Use seeds 0–4,
H=1/2/4/8, both traversals, corpus priority and the one seeded permutation, and
all three modes. This is **6,240 source + 480 synthetic = 6,720 trials**, at most
26,880 pairs. The small per-trial cap emphasizes grid coverage; power to detect
rare regressions is limited. No statistical significance claim is planned.

This replaces the provisional 10,000-pair/6-H ceiling with an explicit feasible
experiment. H=16/32 is omitted for resource reasons, before the full outcome is
known. No corpus target or non-winning seed is removed. Source targets are split
in corpus order into batches of at most six (1,440 trials/batch), using identical
settings and trial-order protocol. Every batch gets a 14,400 s soft wall cap and
512 MiB total output cap; each synthetic command gets 1,200 s and 128 MiB.
All unstarted/partial cells remain visible. No baseline fallback is introduced.

Linear extrapolation from the source pilot is about **2.82 hours / 442 MB** for
source trials; synthetic trials add about **3.1 minutes / 9 MB**. A factor-four
allowance is approximately **11.5 hours / 1.8 GB** overall. These are estimates,
not measured full-run costs: target diversity, extra qualifying paths/replays,
larger H, host load and filesystem effects can change them. The batch caps are
hard declared ceilings, not promises to consume those resources. Actual wall,
CPU, solver/generation work, output bytes, partials and replay rates will be
reported. Every final emitted witness must be replayed, including reductions.

## Remaining independent checks

The fixed labeled dataset will contain 112 parameterized scenarios: 36 modular
arithmetic/bitwise boundary cases, 16 equality/inequality guards, 12 structural
matches (including semantically equal but structurally different inputs), and
48 paired schedule/budget cases from the two synthetic fixtures, three schedules,
four H values and two leaf bindings. Expected arithmetic comes from fixed word
tables; fixture traces come from hand-worked recurrences documented with the
dataset, without executing the optimizer to generate the oracle. These are
correctness scenarios, not additional source benchmarks or a substitute for
the experiment's case denominator.

Preserve the proposed held-out size: 2,000 unique expressions per seed, five
independent seeds, generated without target patterns or derivations. Fix the
held-out selection/generation protocol before looking at those inputs, measure
a separate held-out resource pilot, then execute it. It is not yet run and is
not included in the main-matrix resource estimate above. A final research report
must reconcile raw metrics, eligibility, exclusions, reruns, replay outcomes and
limitations, with no inference from absent or null values.

Held-out preregistration (before generating those inputs): use random-only
generation, hole context, depth expansion 4, full input 63 nodes/depth 5, the
same five boundary constants, 100,000 attempt ceiling, and independent seeds
100003/100019/100043/100049/100057. Save the 2,000 unique concrete input trees,
attempt indices, hashes and full generator settings per seed before auditing;
each target must use exactly the same saved sequence, or an explicitly partial
prefix. No target pattern or derivation participates in input selection.

Choose source targets by a complete bounded derivation catalog using the main
search caps/domain: lexicographically first target with a two-step template,
first remaining with a one-step template, and first remaining without a template.
If a stratum is empty, record it and use the first remaining ID; never select on
removal findings. Use H=4, corpus priority, preorder. The independent resource
pilot uses seed 424242 and 100 cases per chosen target, never a final held-out
seed; time/query/output caps will be fixed from its measured cost before the
full held-out execution. Held-out is a generalization check, not a new comparison
of all three generators. Root config kind `heldout-evaluation` will explicitly
select that mode and preserve the normal three-mode evaluation contract.

The completed 26-target bounded catalog is preserved in
`experiments/heldout-target-catalog.json`: Add5 and Add6 each have one discovered
two-step template; no one-step templates were discovered under these bounds.
The preregistered selection therefore gives Add5, Add2 (empty one-step stratum
fallback) and Add3. This is a bounded miss, not proof of non-derivability.
Catalog discovery took 11.807 s; selected IDs did not use removal outcomes.
The independent held-out pilot config uses 100 cases, seed 424242, 100,000 attempts,
depth 4, hole only, 63 nodes/depth 5, 600 s per trial, 5,000 solver calls at 1,000 ms,
64 MiB per trial, and 600 s/128 MiB overall. Search, per-arm limits, reduction
settings, H=4/preorder/corpus order and constant domain remain as declared above.

The held-out pilot completed all 3 targets / 300 pairs in **7.537 s wall,
6.313 s CPU**, producing **454,886 bytes**, with no positive deltas, eligible
cases, solver unknowns or emitted witnesses. Each target checked the same full
100-input sequence. Search used 304/307/304 solver calls. Raw rows and the saved
pilot inputs are preserved in `experiments/heldout-pilot-results.json`.
This seed is excluded from final held-out inputs. Zero eligible cases do not
show that a target lacks alternatives.

Before full execution, the held-out command is fixed at 15 trials (3 targets x
5 seeds), 2,000 cases per trial / **30,000 pairs** over **10,000 distinct saved
input slots** (2,000 per seed; cross-seed duplicates remain possible). Keep the
pilot generation/search/per-arm/timeout/reduction settings; raise the per-trial
solver cap to 100,000 because the observed ~3 calls/case projects ~6,000 calls
for 2,000 cases, above the pilot's 5,000 cap. Per-trial time remains 600 s and
output 64 MiB; overall caps are 14,400 s / 512 MiB. Point linear cost is about
**12.6 minutes / 45.5 MB**, with a factor-four allowance **50.3 minutes / 182 MB**.
These are pilot extrapolations, not full-run results; rare findings, larger
witnesses and host load can increase actual cost. Every emitted witness must
still be replayed and every partial/not-run prefix retained.
