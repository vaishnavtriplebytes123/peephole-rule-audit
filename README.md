# Peephole Rule Removal Audit

A local research CLI for testing whether removing a derivable peephole
optimization rule makes a bounded, deterministic optimizer less effective.

**Status: M1–M5 verified; M6 runner and resource pilot verified, full study pending.**
The user authorized implementation and periodic GitHub pushes on 2026-10-22.
The `validate`, `derive`, `audit`, `replay`, `reduce`, and `evaluate` commands are implemented.
All three generation modes and small equal-cap comparisons are implemented.
Reduction, bounded JSON/CSV reports and the controlled evaluation runner are
available. The [112 labeled scenarios](docs/SCENARIOS.md) and independent held-out
runner are verified. The full matrix, held-out execution and research report
remain M6 work. No submission date is assumed.

The tool can pair a checked alternative rewrite sequence with a replayable
example of worse optimization after rule removal and supports random,
target-pattern-only, and derivation-guided test generation. Operator count is the
initial cost measure; it is not a claim about execution speed.

## Authoritative documents

- [PRD.md](PRD.md): product behavior, scope, acceptance criteria, and open decisions.
- [AGENTS.md](AGENTS.md): persistent engineering and change-management rules.
- [PLAN.md](PLAN.md): proposed architecture, milestones, and review gates.
- [Development environment](docs/DEVELOPMENT.md): observed baseline and planned commands.
- [Research basis](docs/RESEARCH.md): prior work, contribution boundaries, and evaluation discipline.
- [Agent workflow](docs/WORKFLOW.md): planning and milestone prompts and review checklist.

## Workflow

1. Provide an attributed, normalized JSON rule corpus and an experiment configuration.
2. Validate the supported rules with explicit 32-bit modular semantics.
3. Search for one- or two-step alternatives that exclude a selected rule.
4. Run the same expressions and optimizer settings with and without that rule.
5. Inspect and replay traces where removal increases final operator count.
6. Compare generators under the same limits and reduce qualified witnesses.

`ruleaudit validate --rules corpus/jog.json --out artifacts/validation-NEW`
validates the initial 26-rule source corpus. Output directories must be new.
See [runnable examples](experiments/README.md) for the complete synthetic
validate → derive → audit → replay → reduce journey and pilot evaluation commands.
The [evaluation protocol](docs/EVALUATION_PROTOCOL.md) records actual pilot costs
and the main matrix fixed before full execution. There is no server, database,
account, or UI.

## Proposed repository layout

```text
src/ruleaudit/       # application package, added after plan approval
tests/              # unit, integration, property, and CLI tests
corpus/             # attributed normalized rules, added after source/license review
experiments/        # versioned experiment configurations, not generated results
docs/               # development, research, and workflow documentation
artifacts/          # generated reports; ignored by Git
```

Existing presentation materials, a reference JOG checkout, and unrelated
coursework are preserved and explicitly excluded from this application's Git
baseline. Small curated test fixtures will live under `tests/fixtures/` and remain
tracked. Dependency lockfiles will be tracked when created in Milestone 1.

## Next step

Follow [PLAN.md](PLAN.md) sequentially, recording checks at each milestone.
See [the expression format](docs/EXPRESSION_FORMAT.md) for the M1 library contract
and [development instructions](docs/DEVELOPMENT.md) for setup.
The user-created GitHub repository is
[peephole-rule-audit](https://github.com/vaishnavtriplebytes123/peephole-rule-audit).
See [corpus notes](corpus/README.md) for source selection, normalization,
attribution, and limitations, and [verification evidence](docs/DEVELOPMENT.md)
for the locked environment and milestone checks. Input/configuration and witness
contracts are in [EXPERIMENT_FORMAT.md](docs/EXPERIMENT_FORMAT.md).
Reduction, signal handling and CSV safety are specified in
[REDUCTION_FORMAT.md](docs/REDUCTION_FORMAT.md).
