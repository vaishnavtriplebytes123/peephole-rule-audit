# Evaluation protocol and pilot record

Status (2026-10-23): runner and pilot complete; full experiments, labeled
scenario dataset, held-out execution and final report remain. This document
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

Create at least 100 labeled parameterized scenarios across semantic, matching,
guard, schedule and budget categories, with independent expected outcomes.
They are correctness scenarios, not additional source benchmarks or a substitute
for the experiment's case denominator.

Preserve the proposed held-out size: 2,000 unique expressions per seed, five
independent seeds, generated without target patterns or derivations. Fix the
held-out selection/generation protocol before looking at those inputs, measure
a separate held-out resource pilot, then execute it. It is not yet run and is
not included in the main-matrix resource estimate above. A final research report
must reconcile raw metrics, eligibility, exclusions, reruns, replay outcomes and
limitations, with no inference from absent or null values.
