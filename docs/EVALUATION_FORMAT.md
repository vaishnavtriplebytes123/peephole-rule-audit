# Controlled evaluation (M6)

The runner and resource pilot are verified. The main matrix and resource caps
are fixed in [the evaluation protocol](EVALUATION_PROTOCOL.md), before full
experiments. Full study results remain pending.

`ruleaudit evaluate --rules FILE --config FILE --out NEW_DIRECTORY` consumes an
evaluation configuration, separate from single-run and reduction configurations.
It has exactly `schema_version: 1`, `kind` (`evaluation` or `heldout-evaluation`), `base` (full single-run
config), `targets`, `seeds`, `h_values`, `traversals`, `priorities`,
`permutation_seed`, `order_seed`, `max_trials`, `seconds`, `max_output_bytes`,
`reduce_per_trial` and `reduction` (full reduction configuration).

Bounds: 1–100 unique target IDs from the corpus; 1–5 distinct unsigned 64-bit
seeds; 1–6 distinct H values in 0–10,000; nonempty unique traversals from
preorder/postorder and priorities from corpus/permuted. Base priority must equal
corpus order. Both permutation/order seeds are unsigned 64-bit integers.
`max_trials` is 0–10,000; overall seconds 0–86,400; output 8 KiB–1 GiB;
`reduce_per_trial` is 0–100. Each ordinary evaluation grid cell evaluates random/target/guided.
Only schedule, H, generator mode and seed vary from `base`; all other caps,
domains and bounds are shared. Actual full configs are saved per trial.

Corpus priority is literal source order. Permuted priority uses an independent,
recorded seeded shuffle, shared by every mode/seed at that schedule. Trial
descriptors are independently shuffled using `order_seed` to avoid always
running one mode last. The ordering RNG never generates expressions. Unstarted
grid cells are counted as not run, not zero findings. Time/output exhaustion
stops between trials; incomplete trials remain visible and are never invented
as completed equal-budget trials.

Every comparable case now has `eligible_alternative` (boolean) and
`alternative_steps` (1/2/null), checked using the same scoped derivations and SMT
contracts even for non-findings. Inconclusive cases have null eligibility. The
legacy `checked_alternative` retains its positive-finding attachment meaning.
`eligible_cases` counts checked paths, `checked_alternative_findings` counts
qualified positive deltas. At H>=4 these give the primary interference denominator
and numerator; below H=4 the primary denominator is zero and rate is null.
Absence of a template or bounded miss does not establish non-derivability.
The H>=4 stratum is an operational eligibility convention, not proof that a
particular positive delta was caused by scheduling interference. Budget effects
can still occur in that stratum; trace inspection is needed for causal examples.

`case_key` hashes canonical input hash, target ID, corpus hash, full schedule,
full run limits and `semantics: "bv32-total-tree-v1"`. It excludes mode/seed;
aggregates deduplicate these keys across seeds and retain distinct schedule/H
settings. Findings/comparable-case rates and qualified/eligible-case rates are
different metrics; division by zero is null. No finding leaves trial/attempt/time
to first finding null (censored). Per-trial values, partials and ranges remain
available; no significance claim follows from a tiny sample.

Each numbered trial directory retains its audit/config snapshots, case rows,
witnesses, `replays.json`, optional numbered reduced witnesses, and `metrics.json`.
All emitted original and reduced witnesses are replayed; unknown/invalid replay
outcomes are distinct. Reduction selects the first qualified findings in emitted
order up to the declared cap, not the smallest observed examples. Reduction
partial status does not invalidate already checked paired evidence.

The root writes `evaluation.json` (snapshots, per-trial metrics and aggregates),
`trials.csv` and `status.json`. Child bytes count against the one shared output
cap; root summaries/status receive reserved space. Per-file 10 MiB and bounded
record accumulation still apply. Reports record search/preparation, replay,
reduction, trial work and evaluation work wall/CPU costs separately. Root trial
rows additionally record `wall_seconds`/`wall_cpu_seconds` around child creation,
work and metadata publication; `total_seconds`/`cpu_seconds` are work timings
captured before the child publishes its own metrics. Pilot rows predating these
extra publication-inclusive fields retain their original scope. Root `elapsed`
ends before its own final summary/CSV publication and excludes process startup.
`solver_calls`/`solver_unknowns` are search-phase counters; replay outcomes and
shrinking counters are separate, not an invented total native-query count. No mode
gets free derivation preparation. Missing trial reports have null measurements,
never fabricated zeroes. Software/OS/CPU count metadata are recorded; memory
usage is not inferred from a configured bound.

The explicit `heldout-evaluation` kind evaluates random only. It requires the
base generator to be random with only the hole context; no baseline modes are
silently substituted. Before any trial, it saves a target-independent unique
input sequence per seed in `heldout-inputs-NNNNNN.json`, including full generator
settings, actual trees/hashes, original attempt indices and counters. Snapshot
selection receives no corpus, target or derivation. Each snapshot is bounded
to 100,000 expression nodes and 8 MiB of case records, in addition to the shared
file/output/time caps. Incomplete preparation saves the available sequence when
space permits and starts no trials; an output preflight preserves summary space.

Each held-out trial recomputes the baseline stream and verifies its ordered
input hashes against that saved sequence. A complete run must match the entire
sequence; an incomplete run may match a labeled partial prefix. A mismatch is
a failed trial in both child and parent metrics. Missing trial reports have an
unreported sequence check. The root lists snapshot filenames, hashes and counts.
Other generator aggregates have zero trials and null rates, not evidence that
they were evaluated on held-out inputs. Pilot and final held-out seeds are
distinct and the protocol fixes selection before inspecting those inputs.
