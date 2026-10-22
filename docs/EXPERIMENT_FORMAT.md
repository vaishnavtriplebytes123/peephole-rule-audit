# Single-run experiments and removal witnesses (schema 1)

M3 introduces a single-run configuration. M6 will add an explicit matrix of
these runs. A configuration has exactly `schema_version` (integer 1),
`schedule`, `run`, `search`, `generation`, `solver`, `seconds`, and
`max_output_bytes`. The nested schedule/run/search/solver fields are the full
fields of the corresponding typed library objects; no unknown fields are allowed.
The schedule lists every corpus rule ID exactly once. Removing a target filters
that one ID from the same schedule and corpus order, preserving all other settings.

Generation has exactly `strategy`, `seed`, `cases`, `attempts`, `depth`,
`constants`, and `contexts`. M3 supports `target` and `contexts: ["hole"]`.
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
zero coverage. Expressions remain within the M1 input bounds.

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
