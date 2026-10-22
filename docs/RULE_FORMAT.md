# Rule corpus format (schema version 1)

M2 uses a corpus envelope with exactly `schema_version` (integer 1), `kind`
(`synthetic` or `source`), and a nonempty `rules` array of at most 100 rules.
Runtime expression limits also apply to each rule side. At most 64 guards are
allowed per rule. Rule IDs are unique ASCII identifiers of at most 64 characters.

Each rule has exactly `id`, `lhs`, `rhs`, `guards`, and `provenance`.
Patterns use the expression operator shapes in [EXPRESSION_FORMAT.md](EXPRESSION_FORMAT.md),
except that runtime `var` nodes are replaced by
`{"op":"meta","name":"X","kind":"expr"}` or a `const` kind metavariable.
An expression metavariable matches any subtree. A constant metavariable matches
only a literal constant node, without evaluating an expression. Repeated names
must have identical subtrees and consistent kinds. All RHS and guard names must
be bound by the LHS.

Guards are conjunctions. Each has exactly `op` (`eq` or `ne`), `left`, and
`right`. An operand is either a string naming a constant metavariable or a literal
integer from 0 through 4294967295. Boolean integers are rejected. `ne` means
inequality, with no ordering interpretation.

Provenance has eight required nonempty text fields: `source_url`, `revision`,
`location`, `original`, `normalized`, `restrictions`, `license`, and
`redistribution`. Each field is bounded to 16,384 characters. Source URLs are
attribution data; the application never fetches them. A synthetic corpus must
identify its constructed origin. Provenance completeness is a structural check,
not automatic verification of a user's attribution or license assertions.

Identity rules are retained, with an explicit validation warning; each use
consumes one rewrite step. Validation reports distinguish `verified`, `invalid`
with a valuation, `unsatisfiable_guard`, and `unknown`. Unsupported operators are
rejected on input and should be recorded in a source exclusions manifest.

The optimizer receives a traversal and exact ordered list of all active rule IDs.
It restarts from the root after each first matching rewrite. Root location is
`[]`; child indices are zero-based. Node/depth growth ceilings are 10,000/128,
and H is at most 10,000. M2 chooses a default per-execution time ceiling of 60 s,
configurable from 0 through 3,600 s; time-limited and interrupted results are
partial. A growth-limit stop is a completed deterministic bounded execution;
the offending match is not applied. Solver
timeouts are 1–60,000 ms (default 1,000), and solver calls are bounded from 0
through 1,000,000 (default 1,000). Exhausted calls are inconclusive.

The `validate --rules FILE --out NEW_DIRECTORY` command writes a version-1
`validation.json` containing the corpus snapshot and canonical hash, tool and
solver versions, each validation outcome, warnings and actual solver call count.
The directory must not exist. Exit 0 means validation completed (invalid semantic
rules are reported as data); exit 3 means solver inconclusiveness; malformed
input/collisions use 2, I/O failures use 4, interruption uses 130.
