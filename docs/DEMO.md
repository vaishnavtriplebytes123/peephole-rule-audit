# Reviewer demonstration

Run from the repository root after the locked installation in
[DEVELOPMENT.md](DEVELOPMENT.md). The tool runs locally; no account, service or
network is used during these commands. Every output directory must be new.
The complete walkthrough should be read alongside its JSON/status files.

```powershell
$py = '.venv/Scripts/python.exe'
$demo = Join-Path 'artifacts' ('review-' + [guid]::NewGuid().ToString('N'))
& $py -m ruleaudit --help
& $py -m ruleaudit validate --rules corpus/jog.json --out "$demo/validation"
& $py -m ruleaudit derive --rules tests/fixtures/interference.json --config experiments/interference-h4.json --target A --out "$demo/derivation"
& $py -m ruleaudit audit --rules tests/fixtures/interference.json --config experiments/interference-h4.json --target A --out "$demo/interference"
& $py -m ruleaudit replay --witness "$demo/interference/witness-000001.json" --out "$demo/replay"
& $py -m ruleaudit reduce --witness tests/fixtures/m4-guided-witness-v1.json --config experiments/reduction.json --out "$demo/reduction"
& $py -m ruleaudit replay --witness "$demo/reduction/witness.json" --out "$demo/reduced-replay"
& $py -m ruleaudit evaluate --rules tests/fixtures/interference.json --config experiments/pilot-interference.json --out "$demo/comparison"
```

Inspect each command's exit immediately: 0 means completed, 3 means bounded
partial/inconclusive, 2 invalid input/collision, 4 I/O or failed verification,
130 interruption. Do not continue as though a missing report or nonzero exit
were a successful result. Native timeouts and host load can change resource
outcomes; status/reason fields are part of the evidence.

The initial corpus has 26 attributed JOG-derived rules, all verified in the
recorded environment. Validation checks equality under total modular 32-bit tree
semantics, not unrestricted Java/JVM/LLVM behavior. Source admission/exclusion
and redistribution details are in [the corpus record](../corpus/README.md).

For the synthetic interference fixture, write `ONE=add(X,0)` and
`TWO=add(ONE,0)`. A removes TWO in one step. The checked alternative B,C also
reaches X in two steps; removing A leaves B,D,C priority, where D expands ONE
back into TWO before C can remove it. At H=4/preorder, the declared input
therefore ends at cost 0 with A and cost 2 without A. Inspect `derivations.json`,
`audit.json` and a witness's two traces to distinguish semantic validity,
the alternative path, and actual scheduled behavior. Every emitted finding is
recomputed by replay, including bindings, locations, guards, stops and costs.

The supplied guided witness reduction previously measured 9 to 5 nodes while
preserving a checked path and delta 2. The reduced envelope includes the origin
and every accepted shrink. Replay checks that chain independently. The result
is a bounded greedy reduction, not a globally smallest witness.

The comparison uses 24 controlled pilot trials and reports random/target/guided
separately, including zero findings, null denominators and partial trials. It is
a synthetic teaching example. Use [the evaluation protocol](EVALUATION_PROTOCOL.md)
and versioned full-study results for empirical claims about the source corpus.
The primary H>=4 eligibility rate alone does not identify causal interference.

To demonstrate budget-only behavior separately:

```powershell
& $py -m ruleaudit audit --rules tests/fixtures/budget.json --config experiments/budget-h1.json --target A --out "$demo/budget-H1"
& $py -m ruleaudit audit --rules tests/fixtures/budget.json --config experiments/budget-h2.json --target A --out "$demo/budget-H2"
```

At H=1 the target-free B,C alternative has not finished; H=2 lets it catch up
for the leaf substitutions in these configs. This example does not require a
competing expansion rule. The [112 labeled scenarios](SCENARIOS.md) provide
independent expected outputs/traces for both fixtures under other schedules/H.

Operator count is the declared cost measure, not CPU runtime. A checked template
covers its listed constants/opaque placeholders; a bounded miss proves nothing
about whole-rule derivability. Zero observed regressions never justify safe
production deletion. These limits apply equally to positive and negative results.

## Source-derived scheduling example

The first source batch also produced a checked example for `jog_pAdd5`, selected
by fixed trial/file order rather than largest delta. Replay its complete saved
postorder evidence, then audit the existing matching preorder configuration:

```powershell
& $py -m ruleaudit replay --witness tests/fixtures/source-qualified-witness.json --out "$demo/source-postorder-replay"
& $py -m ruleaudit audit --rules corpus/jog.json --config experiments/source-example-preorder.json --target jog_pAdd5 --out "$demo/source-preorder"
```

For input hash `0521ba51931b13ee406e17880aede69b17399acb2efdd72f013b96a20b6a0423`,
the primary postorder record has costs 3/11 (delta 8); the matching preorder
record has costs 3/3. Both reach no-match within H=8. Add2 followed by Sub11 is
a checked alternative; a child constant-commutation step preempts Sub11 in the
postorder run. See [the report's worked example](REPORT.md) for expressions,
trace explanation, selection and scope. This is a model result using source
patterns, not a measured production-compiler regression.
