# Bounded derivation contract (M3)

The library enumerates constant-valued LHS metavariables from an explicit,
ordered, duplicate-free domain of at most 16 unsigned 32-bit literals.
Expression-valued metavariables become opaque runtime variables `_s0`, `_s1`,
etc., assigned by sorted metavariable name. A pattern cannot match inside an
opaque placeholder. Every target guard must hold for the constant binding.

For each binding, breadth-first forward search tries rules in corpus order at
preorder tree positions, excluding the target ID. It seeks one alternative of
length 1 or 2. There is no zero-step witness. Each matched rule must satisfy its
guards, and the endpoint must structurally equal the instantiated target RHS.
Semantic equivalence alone is insufficient for the endpoint test. Identity and
cycle successors are deduplicated, while nonzero paths reaching the exact
endpoint remain eligible.

All input rules are SMT-checked before search. Invalid, unsatisfiable-guard, or
unsupported rules cannot supply evidence. Solver inconclusiveness prevents
verified output. Each emitted path also has its instantiated step equalities
and overall equality checked independently through the SMT boundary.

A template records the target ID, constant bindings, residual placeholder map,
start/endpoint trees, local rewrite locations, rule IDs, substitutions, guard
checks, and semantic status. Its scope is the listed specialization/template;
the library does not automatically call the original rule globally redundant.

Defaults: 2 steps, 1,000 discovered states, 100,000 matching attempts, 64 constant
bindings, and 60 seconds. Hard maxima are 2 steps, 10,000 states, 1,000,000
attempts, 1,024 constant bindings, and 3,600 seconds. Zero matching attempts or
seconds is permitted and immediately inconclusive. Intermediate terms stay
within 10,000 nodes and depth 128. Solver limits are separate and cumulative
through the supplied backend. These are resource choices, not measurements.

Search reports attempted matches, discovered states, bindings examined, guard
rejections, growth exclusions, and solver inconclusiveness. Results are `found`,
`not-found-within-bounds`, or `partial`. A bounded miss is always inconclusive.
Resource exhaustion can yield `partial` with already verified templates; those
templates remain valid only for their stated scope. Only the first checked path
per constant binding is retained; this is not exhaustive path enumeration.
States count unique trees per constant binding, including start and endpoint,
then sum across examined bindings. A guard rejection counts one rejected target
binding or matched rule application, rather than individual false predicates.

CLI/configuration and snapshot/replay encoding are still M3 implementation work.
