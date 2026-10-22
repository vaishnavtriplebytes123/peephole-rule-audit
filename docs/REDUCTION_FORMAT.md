# Reduction and robust reports

M5 adds `ruleaudit reduce --witness FILE --config FILE --out NEW_DIRECTORY`.
The reduction configuration has exactly `schema_version: 1`, `max_attempts`
(0–10,000, default 1,000), `max_accepted` (0–256, default 64), `seconds`
(0–3,600, default 60), `solver` (existing strict timeout/call limits) and
`max_output_bytes` (existing 8 KiB–1 GiB limits). Input is an original version-1
removal witness with a checked alternative. A reduced witness cannot be nested
as a new origin; replay of both original and reduced forms remains supported.

Origin replay uses its recorded caps and is timed separately. Reduction's clock
and solver cap begin after origin replay. All shrink preparation, tests and
proof checks count against that cap. A soft deadline can be exceeded by the
current paired run with identical per-arm limits; inconclusive pairs are never
accepted. The last verified input remains available on exhaustion/interruption.

Candidates are enumerated deterministically in preorder, replacing an operator
by a direct child (subtree/context deletion), then by constant 0; variables may
be replaced by 0, and constants by distinct smaller values from 0, 1, and half
the old value. Identity/duplicate candidates are skipped. Each accepted input
strictly decreases the lexicographic tuple `(node count, sum of constant values,
sum of variable-name character codes)`. Restart enumeration after acceptance.
This is ordered greedy local shrinking, with no global minimum claim. The
original template's constant specialization must remain applicable. Inputs stay
within the original complete-input bounds and the M1 ceilings. Reduction may
use 0/1 outside the original generation domain; it never claims the changed
input came directly from the recorded generator attempt.

The reduced envelope has exactly `schema_version: 2`,
`kind: "reduced-removal-witness"`, `payload`, and `sha256` over the payload.
The payload contains the complete `original` witness, `reduction_config`,
`steps`, `final`, `status`, `reason`, `attempts`, `solver_calls`,
`preparation_seconds`, `elapsed`, and `method`. Each accepted step records the
location, replacement kind/value, input hashes before/after, measures, and the
new input, paired traces/costs and concrete alternative. Replay checks the origin,
each allowed shrink and strict decrease, then recomputes every accepted pair and
alternative under the original schedule/H/growth/semantics. The final record
must equal the last checked record. Timings/resource counters are bounded
metadata, not proof of deterministic search completeness. A partial witness can
replay as verified evidence while still recording incomplete minimization.

`reduce` writes `reduction.json`, `witness.json`, `summary.csv` and `status.json`.
Audits additionally write `cases.csv`; validation writes `rules.csv`. CSV is
UTF-8 with standard quoting. Text cells beginning (after whitespace/control
characters) with `=`, `+`, `-`, or `@` are prefixed with an apostrophe. Numeric
cells retain their numeric values; null becomes empty. JSON remains the complete
unmodified evidence. All JSON/CSV files use the shared atomic, no-replacement,
10 MiB-per-file writer and total output cap, reserving 4 KiB for status.
Failure to save status is caught and reported on stderr, including on interruption.
During CLI execution SIGINT (and SIGBREAK on Windows) is latched until the next
clock checkpoint, where it becomes `KeyboardInterrupt`. The signal handler itself
returns safely, so native solver object cleanup cannot swallow the request as
an unraisable exception. Existing handlers are restored after the command.
Native calls still obey their explicit timeouts; this is cooperative interruption.
Audit case-record accumulation also obeys the 10 MiB JSON ceiling in memory:
before another pair, reserve its concrete provenance plus bounded result fields,
snapshots and report metadata. Exhaustion stops before executing an unrecordable
pair and produces explicit partial status with `report-record-limit`.
