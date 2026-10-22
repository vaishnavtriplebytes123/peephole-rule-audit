# Single-run experiments and removal witnesses

M3 introduces a single-run configuration. M6's explicit matrix is specified in
[EVALUATION_FORMAT.md](EVALUATION_FORMAT.md). A single-run configuration has exactly `schema_version` (integer 1 or 2),
`schedule`, `run`, `search`, `generation`, `solver`, `seconds`, and
`max_output_bytes`. The nested schedule/run/search/solver fields are the full
fields of the corresponding typed library objects; no unknown fields are allowed.
The schedule lists every corpus rule ID exactly once. Removing a target filters
that one ID from the same schedule and corpus order, preserving all other settings.

Version-1 generation has exactly `strategy`, `seed`, `cases`, `attempts`, `depth`,
`constants`, and `contexts`, supporting `target` and `contexts: ["hole"]`.
M4 writes version 2, additionally requiring `max_nodes` (1–1000), `max_depth`
(1–64) and `max_match_attempts` (0–1,000,000, default 100,000). Old version-1
configs/witnesses retain the original target/hole streams and input limits.
Unknown versions/fields are rejected. Original generated witness envelopes remain
version 1. M5's reduced witnesses use a separate version-2 envelope, specified in
[REDUCTION_FORMAT.md](REDUCTION_FORMAT.md), retaining their complete original.
Bounds: unsigned 64-bit seed, 1–10,000 requested unique cases, 0–1,000,000
attempts, depth 0–4, and 1–16 distinct unsigned 32-bit constants. Each attempt
uses `depth` expansion levels for expression metavariable substitutions (0 means
a leaf); the fixed target pattern is retained. The complete input still obeys
the M1 node/depth ceilings. Each attempt
has its own deterministic Random instance seeded by SHA-256 of the seed,
strategy, attempt index, and stream name. Attempt indices start at 1. This lets
replay regenerate a specific attempt directly, without trusting recorded bindings.
Target generation receives no alternative derivations. Invalid guards, duplicates,
and size exclusions consume attempts. Exhaustion is explicitly partial, including
zero coverage. Expressions remain within the shared complete-input bounds.

Version 2 supports `random`, `target`, and `guided`. Contexts are a nonempty
unique list from `hole`, `not`, and `OP-left`/`OP-right` for
`add/sub/and/or/xor`. The name denotes the child occupied by the generated core;
the other child is an independently generated sibling. Context and sibling use
separate deterministic RNG streams. Baseline functions accept no derivations.
All modes share the constant domain, expansion limit, full-input bounds,
context vocabulary, accepted-case/attempt ceilings and end-to-end clock.

Guided generation instantiates verified two-step templates and checks every
concrete path step, guard, growth bound and structural endpoint. At the state
after its first step, it finds the actual first target-free scheduled match.
The match must differ from the next expected step and overlap its location
(ancestor/same/descendant). A first match in a disjoint sibling is not accepted
as overlap. A growth-stopped match is not a chosen rewrite. Provenance records
the template, target location, concrete prefix, full intermediate tree, expected
step and competing step, including bindings/guards. Replay verifies the template
and regenerates these facts rather than trusting labels. A hint is not evidence
of a positive removal delta. One-step-only alternatives and no-overlap templates
produce no guided cases; no baseline fallback occurs. Zero coverage records
`no-overlap-candidate-within-bounds` and partial status.

Guidance matching consumes one cumulative `max_match_attempts` budget per run,
including declared-step matching and all rejected competing matches. Checks at
each match also enforce the soft overall deadline. Reports include the actual
`generation.match_attempts`; baseline modes consume zero. Deduplication happens
after generation, so duplicate guided cases still consume scan work. All modes
currently share derivation preparation for optional finding qualification;
baseline generation does not receive those templates. Preparation time and
solver calls are included for every mode; M6 must retain this accounting.

`seconds` is a 0–3,600 s overall soft deadline, checked at work boundaries.
Each optimizer arm separately has the identical `run.seconds` ceiling. A pair
may finish beyond the overall deadline; it is never compared using unequal arm
limits. Per-call solver timeouts remain explicit. Time-limit/interrupted arms or
unknown/invalid output equivalence are never eligible regression witnesses.

Experiment reports are UTF-8 JSON, capped at 10 MiB per file and 100,000 serialized expression
node occurrences per document. Total output defaults to 100 MiB, configurable
from 8 KiB through 1 GiB; 4 KiB is reserved for final status. These storage caps
produce partial status rather than silently dropping findings. Output is a new
directory; filenames are fixed or numeric indices, never corpus-controlled paths.
Files are published atomically without replacing destinations. Interrupted or
failed temporary files keep `.partial` labels. The generic JSON container ceiling
is raised to 300 for snapshots of depth-128 outputs; expression input depth stays 64.

`derive` writes `derivations.json`; `audit` writes `audit.json`, numbered
`witness-000001.json` files for eligible positive deltas, and `status.json`.
M5 also writes `cases.csv` for audits and `rules.csv`/`status.json` for validation,
using the same bounded, no-replacement writer. CSV escaping and cooperative
interruption are described in [REDUCTION_FORMAT.md](REDUCTION_FORMAT.md).
The audit records raw per-case costs, stops, comparable flags, input hashes,
generation attempts and provenance, including zero findings. A checked alternative
is attached when applicable; its absence does not prove non-derivability.
`findings` counts all comparable positive deltas; `checked_alternative_findings`
counts only emitted regression witnesses with a checked alternative. These
counts must not be conflated in research claims. Nonfinding cases are not
automatically labeled as having a checked alternative.
Ground alternative steps are checked again after concrete instantiation and
context insertion. Synthetic/source corpus kinds remain distinct.

A removal witness is an envelope with exactly `schema_version: 1`,
`kind: "removal-witness"`, `payload`, and `sha256`. The payload contains tool and
Python/Z3 versions; complete corpus/config snapshots and canonical hashes;
target, input, generation provenance; both runs with ordered traces, substitutions,
guard checks, costs, stops and elapsed metadata; and an optional checked template
plus concrete alternative. The envelope hash covers the entire payload.

Replay checks hashes and schemas, validates all corpus rules, regenerates the
recorded generation attempt, recomputes both optimizer arms and semantic checks,
and compares all claimed results using type-sensitive canonical JSON. Only elapsed
metadata and producer environment metadata may differ. Alternative paths are
rechecked from their declared steps, guards and structural endpoints, without
trusting recorded substitutions, costs, or solver labels. Unsupported tool/schema
versions fail. Replay does not access the network or the original corpus paths.

Exit 0: completed bounded work, including a bounded derivation miss/zero regressions;
2: malformed input, tampered evidence, unusable corpus or existing output path;
3: incomplete bounds/deadline/solver/storage; 4: I/O/internal failure; 130: interruption.
A bounded miss remains inconclusive even when enumeration within its scope completed.
