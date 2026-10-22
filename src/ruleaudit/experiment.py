"""Sequential experiment orchestration with explicit counters and work boundaries."""

import platform
from collections.abc import Callable
from dataclasses import asdict
from importlib.metadata import version
from time import perf_counter, process_time
from typing import cast

from ruleaudit import __version__
from ruleaudit.audit import audit_case, check_corpus
from ruleaudit.config import Config, config_document
from ruleaudit.corpus import Corpus, corpus_document
from ruleaudit.derive import DeriveResult, derive
from ruleaudit.generate import GuidanceBudget, guided_attempt, random_attempt, target_attempt
from ruleaudit.io import InputError, JSONValue, canonical_bytes, content_hash, expression_node
from ruleaudit.records import EncodingBudget, case_document, derivation_document, make_witness
from ruleaudit.report import Cell, IncompleteError, ReportWriter
from ruleaudit.rules import Rule
from ruleaudit.solver import Z3Backend

MAX_AUDIT_BYTES = 10 * 1024**2


def validate_settings(corpus: Corpus, config: Config, target_id: str) -> Rule:
    ids = tuple(rule.id for rule in corpus.rules)
    if len(config.schedule.priority) != len(ids) or set(config.schedule.priority) != set(ids):
        raise InputError("schedule.priority", "must list every corpus rule exactly once")
    target = next((rule for rule in corpus.rules if rule.id == target_id), None)
    if target is None:
        raise InputError("target", "unknown target ID")
    return target


def snapshots(corpus: Corpus, config: Config, target: Rule) -> dict[str, JSONValue]:
    corpus_data, config_data = corpus_document(corpus), config_document(config)
    return {
        "schema_version": 1,
        "tool_version": __version__,
        "environment": {"python": platform.python_version(), "z3-solver": version("z3-solver")},
        "target": target.id,
        "corpus_kind": corpus.kind,
        "corpus": corpus_data,
        "corpus_hash": content_hash(corpus_data),
        "config": config_data,
        "config_hash": content_hash(config_data),
    }


def derivation_result_document(result: DeriveResult) -> dict[str, JSONValue]:
    budget = EncodingBudget()
    return {
        "status": result.status,
        "reason": result.reason,
        "match_attempts": result.match_attempts,
        "states": result.states,
        "bindings_examined": result.bindings_examined,
        "guard_rejections": result.guard_rejections,
        "growth_exclusions": result.growth_exclusions,
        "solver_unknowns": result.solver_unknowns,
        "elapsed": result.elapsed,
        "witnesses": [derivation_document(w, budget) for w in result.witnesses],
    }


def derive_experiment(
    corpus: Corpus,
    config: Config,
    target: Rule,
    writer: ReportWriter,
    *,
    now: Callable[[], float] = perf_counter,
) -> int:
    backend = Z3Backend(config.solver, deadline=now() + config.seconds, now=now)
    from dataclasses import replace

    result = derive(
        target,
        corpus.rules,
        replace(config.search, seconds=min(config.search.seconds, config.seconds)),
        config.generation.constants,
        backend=backend,
        now=now,
    )
    if result.reason == "interrupted":
        raise KeyboardInterrupt
    report = {
        **snapshots(corpus, config, target),
        **derivation_result_document(result),
        "solver_calls": backend.calls,
    }
    writer.write("derivations.json", report)
    return 3 if result.status == "partial" else 0


def audit_experiment(
    corpus: Corpus,
    config: Config,
    target: Rule,
    writer: ReportWriter,
    *,
    now: Callable[[], float] = perf_counter,
) -> int:
    from dataclasses import replace

    started, cpu_started = now(), process_time()
    backend = Z3Backend(config.solver, deadline=started + config.seconds, now=now)
    if config.seconds == 0:
        raise IncompleteError("overall-time-limit")
    validation = check_corpus(corpus, backend=backend)
    if validation.status == "unknown":
        raise IncompleteError("corpus validation inconclusive")
    if validation.checked is None:
        invalid = [name for name, result in validation.results if result.status != "verified"]
        raise InputError("corpus", f"unusable rules: {', '.join(invalid)}")
    remaining = max(0.0, config.seconds - (now() - started))
    derived = derive(
        target,
        corpus.rules,
        replace(config.search, seconds=min(config.search.seconds, remaining)),
        config.generation.constants,
        backend=backend,
        now=now,
    )
    if derived.reason == "interrupted":
        raise KeyboardInterrupt
    preprocessing = now() - started
    fixed_report: dict[str, JSONValue] = {
        **snapshots(corpus, config, target),
        "derivation": derivation_result_document(derived),
        "validation": [
            {"id": name, **cast(dict[str, JSONValue], asdict(result))}
            for name, result in validation.results
        ],
    }
    # Remaining fields are bounded counters, flags, times and short stop reasons.
    report_overhead = len(canonical_bytes(fixed_report)) + 4096
    raw_bytes = 2
    partial = derived.status == "partial"
    reasons: list[JSONValue] = [derived.reason] if partial else []
    records: list[JSONValue] = []
    seen = set()
    attempts = duplicates = rejections = generated = findings = comparable = qualified = 0
    first_finding: float | None = None
    guidance_budget = GuidanceBudget(
        config.generation.max_match_attempts,
        allow_work=lambda: now() - started < config.seconds,
    )
    for attempt in range(1, config.generation.attempts + 1):
        if now() - started >= config.seconds:
            partial = True
            reasons.append("overall-time-limit")
            break
        attempts = attempt
        if config.generation.strategy == "random":
            case = random_attempt(config.generation, attempt)
        elif config.generation.strategy == "target":
            case = target_attempt(target, config.generation, attempt)
        else:
            try:
                case = guided_attempt(
                    target,
                    config.generation,
                    attempt,
                    derived.witnesses,
                    corpus.rules,
                    config.schedule,
                    config.run,
                    budget=guidance_budget,
                )
            except IncompleteError as error:
                partial = True
                reasons.append(str(error))
                break
        if case is None:
            rejections += 1
            continue
        if case.expression in seen:
            duplicates += 1
            continue
        provenance = case_document(case, EncodingBudget())
        record_allowance = len(canonical_bytes(provenance)) + 1024
        if report_overhead + raw_bytes + record_allowance > MAX_AUDIT_BYTES:
            partial = True
            reasons.append("report-record-limit")
            break
        seen.add(case.expression)
        generated += 1
        pair = audit_case(
            case.expression,
            target.id,
            validation.checked,
            config.schedule,
            config.run,
            backend=backend,
            now=now,
        )
        filename: str | None = None
        checked_alternative: bool | None = None
        comparable += int(pair.comparable)
        if pair.comparable and pair.delta > 0:
            filename = f"witness-{findings + 1:06d}.json"
            witness = make_witness(corpus, config, case, pair, derived.witnesses, backend=backend)
            checked_alternative = (
                cast(dict[str, JSONValue], witness["payload"])["alternative"] is not None
            )
            writer.write(filename, witness)
            qualified += int(checked_alternative)
            findings += 1
            if first_finding is None:
                first_finding = now() - started
        records.append(
            {
                "input_hash": content_hash(expression_node(case.expression)),
                "provenance": provenance,
                "cost_with": pair.cost_with,
                "cost_without": pair.cost_without,
                "delta": pair.delta,
                "comparable": pair.comparable,
                "semantic_status": pair.semantic_status,
                "stop_with": pair.with_target.stop_reason,
                "stop_without": pair.without_target.stop_reason,
                "witness": filename,
                "checked_alternative": checked_alternative,
            }
        )
        raw_bytes += len(canonical_bytes(records[-1])) + 1
        if not pair.comparable:
            partial = True
            reasons.append("pair-inconclusive")
            break
        if generated == config.generation.cases:
            break
    if generated < config.generation.cases:
        partial = True
        reasons.append("generation-incomplete")
        if (
            config.generation.strategy == "guided"
            and generated == 0
            and attempts == config.generation.attempts
            and rejections + duplicates == attempts
        ):
            reasons.append("no-overlap-candidate-within-bounds")
    report: dict[str, JSONValue] = {
        **fixed_report,
        "status": "partial" if partial else "completed",
        "reasons": reasons,
        "cases_generated": generated,
        "cases_tested": len(records),
        "comparable_cases": comparable,
        "findings": findings,
        "checked_alternative_findings": qualified,
        "records": records,
        "generation": {
            "attempts": attempts,
            "duplicates": duplicates,
            "rejections": rejections,
            "match_attempts": guidance_budget.matches,
        },
        "solver_calls": backend.calls,
        "preprocessing_seconds": preprocessing,
        "computation_seconds": now() - started,
        "cpu_seconds": process_time() - cpu_started,
        "time_to_first_finding": first_finding,
    }
    writer.write("audit.json", report)
    columns = (
        "input_hash",
        "cost_with",
        "cost_without",
        "delta",
        "comparable",
        "semantic_status",
        "stop_with",
        "stop_without",
        "checked_alternative",
        "witness",
    )
    writer.write_csv(
        "cases.csv",
        [
            columns,
            *(
                tuple(cast(Cell, cast(dict[str, JSONValue], row)[key]) for key in columns)
                for row in records
            ),
        ],
    )
    return 3 if partial else 0
