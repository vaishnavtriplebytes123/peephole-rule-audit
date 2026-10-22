# Labeled correctness scenarios

[The fixed dataset](../tests/fixtures/labeled-scenarios.json) contains **112
parameterized scenarios**: 36 word-semantics, 16 guard, 12 structural-match and
48 paired schedule/budget cases. IDs are unique; pytest checks the declared
counts and executes every scenario. They supplement the existing contract tests.
They are neither 112 independent real benchmarks nor experiment-case evidence.

The arithmetic oracle is a fixed unsigned 32-bit table for add/sub/and/or/xor/not,
including zero, maximum, the sign boundary and complementary alternating bits.
Guard rows declare equality/inequality outcomes for constant bindings and literal
or metavariable operands. Matching rows declare exact bindings or no-match,
including repeated metavariables, constant-only kinds, operand order, and the
syntactically distinct `x` and `add(x,0)` despite semantic equivalence.

The paired fixture oracle uses `ONE=add(X,0)`, `TWO=add(ONE,0)` and rules:
`A:TWO->X`, `B:TWO->ONE`, `C:ONE->X`; interference additionally has
`D:ONE->TWO`. The input is TWO with either variable x or the maximum constant;
there is no automatic constant folding. Three schedules cross H=0/1/2/4:

- A-first preorder: with A, one step reaches X. Without A, budget takes B,C
  and reaches X after two steps; interference alternates B,D indefinitely,
  with one operator after odd H and two after even H.
- A-first postorder: budget takes C at child 0 then at root, reaching X after
  two steps in both arms. Interference takes D at the innermost ONE repeatedly,
  adding one operator per step, at paths 0, 00, 000, and so on in both arms.
- C-first preorder: both arms take C at root twice, reaching X after two steps.

H=0 retains TWO and stops at the rewrite budget. Reaching a normal form on the
last allowed rewrite still reports rewrite-budget; an extra available step is
needed to observe no-match. Each row stores the resulting tree, cost, ordered
rule/location trace and stop reason for both arms. These expectations were
constructed from the recurrences above without calling application algorithms
or a solver to generate their values. The missing-dataset test failed before
the data was written, then all 113 dataset/coverage tests passed.
