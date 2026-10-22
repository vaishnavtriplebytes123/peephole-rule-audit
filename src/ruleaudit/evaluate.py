"""Sequential controlled trials, durable raw reports and explicit missing measurements."""

import os
import platform
from collections.abc import Callable
from importlib.metadata import version
from time import perf_counter, process_time
from typing import cast

from ruleaudit import __version__
from ruleaudit.config import config_document
from ruleaudit.corpus import Corpus, corpus_document
from ruleaudit.evaluation_config import EvaluationConfig, Trial, evaluation_document, trials
from ruleaudit.experiment import audit_experiment, validate_settings
from ruleaudit.io import InputError, JSONValue, canonical_bytes, content_hash, load_json
from ruleaudit.metrics import rate
from ruleaudit.reduce import reduce_witness
from ruleaudit.replay import replay
from ruleaudit.report import Cell, IncompleteError, ReportWriter

_COUNTS = (
    "cases_tested",
    "comparable_cases",
    "findings",
    "checked_alternative_findings",
    "eligible_cases",
    "primary_interference_cases",
    "primary_interference_findings",
    "solver_calls",
    "solver_unknowns",
)


def _replay(value: JSONValue, name: str, *, now: Callable[[], float]) -> dict[str, JSONValue]:
    started = now()
    try:
        result = replay(value, now=now)
        return {
            "file": name,
            "status": "verified",
            "reason": None,
            "witness_hash": result["witness_hash"],
            "seconds": now() - started,
        }
    except IncompleteError as error:
        return {"file": name, "status": "unknown", "reason": str(error), "seconds": now() - started}
    except InputError as error:
        return {"file": name, "status": "invalid", "reason": str(error), "seconds": now() - started}


def _run_trial(
    corpus: Corpus,
    settings: EvaluationConfig,
    trial: Trial,
    child: ReportWriter,
    deadline: float,
    *,
    now: Callable[[], float],
) -> tuple[dict[str, JSONValue], set[str]]:
    started, cpu_started = now(), process_time()
    search_seconds = replay_seconds = reduction_seconds = 0.0
    search_code = 3
    status, reason = "completed", "completed"
    replays: list[JSONValue] = []
    reductions: list[JSONValue] = []
    reduced_count = 0
    data: dict[str, JSONValue] | None = None
    try:
        child.write("config.json", config_document(trial.config))
        target = validate_settings(corpus, trial.config, trial.target)
        phase = now()
        try:
            search_code = audit_experiment(corpus, trial.config, target, child, now=now)
        except IncompleteError as error:
            status, reason = "partial", str(error)
        finally:
            search_seconds = now() - phase
        path = child.directory / "audit.json"
        if path.exists():
            loaded = load_json(path)
            if not isinstance(loaded, dict):
                raise InputError("audit.json", "invalid trial report")
            data = loaded
        if search_code == 3:
            status = "partial"
            if reason == "completed":
                reason = "search incomplete"
        for path in sorted(child.directory.glob("witness-*.json")):
            if now() >= deadline:
                status, reason = "partial", "overall-time-limit during replay"
                replays.append(
                    {
                        "file": path.name,
                        "status": "not-run",
                        "reason": "overall-time-limit",
                        "seconds": 0.0,
                    }
                )
                continue
            value = load_json(path)
            phase = now()
            outcome = _replay(value, path.name, now=now)
            replay_seconds += now() - phase
            replays.append(outcome)
            if outcome["status"] != "verified":
                status, reason = (
                    ("failed" if outcome["status"] == "invalid" else "partial"),
                    "witness replay did not verify",
                )
                if outcome["status"] == "invalid":
                    break
                continue
            payload = cast(dict[str, JSONValue], cast(dict[str, JSONValue], value)["payload"])
            if payload["alternative"] is None or reduced_count >= settings.reduce_per_trial:
                continue
            if now() >= deadline:
                status, reason = "partial", "overall-time-limit before reduction"
                break
            phase = now()
            reduced = reduce_witness(value, settings.reduction, now=now)
            reduction_seconds += now() - phase
            name = f"reduced-{reduced_count + 1:06d}.json"
            child.write(name, reduced)
            reduced_count += 1
            reduced_payload = cast(dict[str, JSONValue], reduced["payload"])
            final = cast(dict[str, JSONValue], reduced_payload["final"])
            from ruleaudit.io import parse_expression
            from ruleaudit.ir import measure

            reductions.append(
                {
                    "file": name,
                    "status": reduced_payload["status"],
                    "nodes_before": measure(
                        parse_expression({"schema_version": 1, "expression": payload["input"]})
                    ).nodes,
                    "nodes_after": measure(
                        parse_expression({"schema_version": 1, "expression": final["input"]})
                    ).nodes,
                    "attempts": reduced_payload["attempts"],
                    "solver_calls": reduced_payload["solver_calls"],
                }
            )
            if reduced_payload["status"] == "interrupted":
                status, reason = "interrupted", "reduction interrupted"
                break
            if reduced_payload["status"] != "completed":
                status, reason = "partial", "reduction incomplete"
            if now() >= deadline:
                status, reason = "partial", "overall-time-limit before reduced replay"
                break
            phase = now()
            outcome = _replay(reduced, name, now=now)
            replay_seconds += now() - phase
            replays.append(outcome)
            if outcome["status"] != "verified":
                status, reason = (
                    ("failed" if outcome["status"] == "invalid" else "partial"),
                    "reduced witness replay did not verify",
                )
                if outcome["status"] == "invalid":
                    break
    except IncompleteError as error:
        status, reason = "partial", str(error)
    except KeyboardInterrupt:
        status, reason = "interrupted", "trial interrupted"
    reported = {cast(dict[str, JSONValue], item)["file"] for item in replays}
    for pattern in ("witness-*.json", "reduced-*.json"):
        for path in sorted(child.directory.glob(pattern)):
            if path.name not in reported:
                replays.append(
                    {"file": path.name, "status": "not-run", "reason": reason, "seconds": 0.0}
                )
    if data is None and (child.directory / "audit.json").exists():
        data = cast(dict[str, JSONValue], load_json(child.directory / "audit.json"))
    known = data if data is not None else {}
    row: dict[str, JSONValue] = {
        "directory": child.directory.name,
        "target": trial.target,
        "strategy": trial.config.generation.strategy,
        "seed": trial.config.generation.seed,
        "h": trial.config.run.h,
        "traversal": trial.config.schedule.traversal,
        "priority": list(trial.config.schedule.priority),
        "config_hash": content_hash(config_document(trial.config)),
        "status": status,
        "reason": reason,
        "search_status": known.get("status", "partial"),
        **{key: known.get(key) for key in _COUNTS},
        "preprocessing_seconds": known.get("preprocessing_seconds"),
        "time_to_first_finding": known.get("time_to_first_finding"),
        "time_to_first_qualified_finding": known.get("time_to_first_qualified_finding"),
        "trial_to_first_finding": known.get("trial_to_first_finding"),
        "attempt_to_first_finding": known.get("attempt_to_first_finding"),
        "search_seconds": search_seconds,
        "replay_seconds": replay_seconds,
        "reduction_seconds": reduction_seconds,
        "total_seconds": max(0.0, now() - started),
        "cpu_seconds": process_time() - cpu_started,
    }
    generation = cast(dict[str, JSONValue], known.get("generation", {}))
    row.update(
        {
            "generation_attempts": generation.get("attempts"),
            "generation_duplicates": generation.get("duplicates"),
            "generation_rejections": generation.get("rejections"),
            "generation_matches": generation.get("match_attempts"),
        }
    )
    derived = cast(dict[str, JSONValue], known.get("derivation", {}))
    templates = cast(list[dict[str, JSONValue]], derived.get("witnesses", []))
    row.update(
        {
            "derivation_status": derived.get("status"),
            "one_step_templates": sum(
                len(cast(list[JSONValue], w["steps"])) == 1 for w in templates
            )
            if data is not None
            else None,
            "two_step_templates": sum(
                len(cast(list[JSONValue], w["steps"])) == 2 for w in templates
            )
            if data is not None
            else None,
        }
    )
    for prefix, selected in (
        (
            "original",
            [
                r
                for r in replays
                if cast(str, cast(dict[str, JSONValue], r)["file"]).startswith("witness-")
            ],
        ),
        (
            "reduced",
            [
                r
                for r in replays
                if cast(str, cast(dict[str, JSONValue], r)["file"]).startswith("reduced-")
            ],
        ),
    ):
        row[prefix + "_witnesses"] = (
            len(list(child.directory.glob("witness-*.json")))
            if prefix == "original"
            else len(list(child.directory.glob("reduced-*.json")))
        )
        row[prefix + "_replayed"] = sum(
            cast(dict[str, JSONValue], r)["status"] == "verified" for r in selected
        )
    row["replay_unknowns"] = sum(
        cast(dict[str, JSONValue], r)["status"] == "unknown" for r in replays
    )
    row["replay_invalid"] = sum(
        cast(dict[str, JSONValue], r)["status"] == "invalid" for r in replays
    )
    row["reductions"] = reductions
    row["replay_not_run"] = sum(
        cast(dict[str, JSONValue], r)["status"] == "not-run" for r in replays
    )
    for result_key, numerator, denominator in (
        ("finding_rate", "findings", "comparable_cases"),
        ("primary_rate", "primary_interference_findings", "primary_interference_cases"),
    ):
        row[result_key] = (
            rate(cast(int, row[numerator]), cast(int, row[denominator]))
            if row[numerator] is not None and row[denominator] is not None
            else None
        )
    regression_keys = {
        cast(str, r["case_key"])
        for r in cast(list[dict[str, JSONValue]], known.get("records", []))
        if r["comparable"] is True and cast(int, r["delta"]) > 0
    }
    try:
        child.write("replays.json", {"schema_version": 1, "replays": replays})
        child.write("metrics.json", row)
    except IncompleteError as error:
        if row["status"] not in ("failed", "interrupted"):
            row["status"], row["reason"] = "partial", str(error)
    child.write(
        "status.json",
        {"status": row["status"], "reason": cast(str, row["reason"])[:512]},
        status=True,
    )
    return row, regression_keys


def _aggregates(rows: list[JSONValue], uniques: dict[str, set[str]]) -> list[JSONValue]:
    result: list[JSONValue] = []
    for strategy in ("random", "target", "guided"):
        selected = [
            cast(dict[str, JSONValue], row)
            for row in rows
            if cast(dict[str, JSONValue], row)["strategy"] == strategy
        ]
        known = [row for row in selected if row["cases_tested"] is not None]
        counts = {
            key: sum(cast(int, row[key]) for row in known) if known else None for key in _COUNTS
        }
        item: dict[str, JSONValue] = {
            "strategy": strategy,
            "trials": len(selected),
            "reported_trials": len(known),
            "unreported_trials": len(selected) - len(known),
            "completed_search_trials": sum(row["search_status"] == "completed" for row in selected),
            "partial_trials": sum(row["status"] != "completed" for row in selected),
            **counts,
            "unique_regression_keys": len(uniques[strategy]),
        }
        item["finding_rate"] = (
            rate(cast(int, counts["findings"]), cast(int, counts["comparable_cases"]))
            if known
            else None
        )
        item["primary_rate"] = (
            rate(
                cast(int, counts["primary_interference_findings"]),
                cast(int, counts["primary_interference_cases"]),
            )
            if known
            else None
        )
        times = [cast(float, row["total_seconds"]) for row in selected]
        item["total_seconds_range"] = [min(times), max(times)] if times else None
        for key in (
            "original_witnesses",
            "original_replayed",
            "reduced_witnesses",
            "reduced_replayed",
            "replay_unknowns",
            "replay_invalid",
            "replay_not_run",
        ):
            item[key] = sum(cast(int, row[key]) for row in selected)
        item["replay_rate"] = rate(
            cast(int, item["original_replayed"]) + cast(int, item["reduced_replayed"]),
            cast(int, item["original_witnesses"]) + cast(int, item["reduced_witnesses"]),
        )
        result.append(item)
    return result


def evaluate(
    corpus: Corpus,
    settings: EvaluationConfig,
    writer: ReportWriter,
    *,
    now: Callable[[], float] = perf_counter,
) -> int:
    started, cpu_started = now(), process_time()
    deadline = started + settings.seconds
    rows: list[JSONValue] = []
    snapshot = corpus_document(corpus)
    config = evaluation_document(settings)
    row_bytes = len(canonical_bytes({"corpus": snapshot, "config": config})) + 16384
    row_allowance = 8192 + settings.reduce_per_trial * 512 + len(corpus.rules) * 70
    uniques = {name: set[str]() for name in ("random", "target", "guided")}
    reason = "completed grid"
    root_reserve = min(20 * 1024**2, settings.max_output_bytes // 2)
    for index, trial in enumerate(trials(corpus, settings), 1):
        if len(rows) >= settings.max_trials:
            reason = "trial-limit"
            break
        if now() >= deadline:
            reason = "overall-time-limit"
            break
        if row_bytes + row_allowance > 10 * 1024**2:
            reason = "summary-record-limit"
            break
        allocation = min(trial.config.max_output_bytes, writer.remaining - root_reserve)
        if allocation < 8192:
            reason = "overall-output-limit"
            break
        trial_started, trial_cpu_started = now(), process_time()
        child = ReportWriter(writer.directory / f"trial-{index:06d}", allocation)
        try:
            row, keys = _run_trial(corpus, settings, trial, child, deadline, now=now)
        finally:
            writer.remaining -= allocation - child.remaining
        row["wall_seconds"] = now() - trial_started
        row["wall_cpu_seconds"] = process_time() - trial_cpu_started
        rows.append(row)
        row_bytes += len(canonical_bytes(row)) + 1
        uniques[trial.config.generation.strategy].update(keys)
        if row["status"] in ("interrupted", "failed"):
            reason = cast(str, row["reason"])
            break
    statuses = {cast(str, cast(dict[str, JSONValue], row)["status"]) for row in rows}
    status = (
        "failed"
        if "failed" in statuses
        else "interrupted"
        if "interrupted" in statuses
        else "partial"
        if len(rows) < settings.expected_trials or "partial" in statuses
        else "completed"
    )
    result: dict[str, JSONValue] = {
        "schema_version": 1,
        "kind": "evaluation-result",
        "tool_version": __version__,
        "environment": {
            "python": platform.python_version(),
            "z3-solver": version("z3-solver"),
            "os": platform.platform(),
            "machine": platform.machine(),
            "logical_cpus": os.cpu_count(),
        },
        "corpus_kind": corpus.kind,
        "corpus": snapshot,
        "corpus_hash": content_hash(snapshot),
        "config": config,
        "config_hash": content_hash(config),
        "status": status,
        "reason": reason,
        "expected_trials": settings.expected_trials,
        "finished_trials": len(rows),
        "not_run": settings.expected_trials - len(rows),
        "trials": rows,
        "aggregates": _aggregates(rows, uniques),
        "elapsed": now() - started,
        "cpu_seconds": process_time() - cpu_started,
        "bytes_before_summary": settings.max_output_bytes - writer.remaining,
    }
    writer.write("evaluation.json", result)
    columns = (
        "directory",
        "target",
        "strategy",
        "seed",
        "h",
        "traversal",
        "status",
        "cases_tested",
        "findings",
        "eligible_cases",
        "primary_rate",
        "generation_attempts",
        "search_seconds",
        "replay_seconds",
        "reduction_seconds",
        "total_seconds",
        "wall_seconds",
        "wall_cpu_seconds",
        "original_witnesses",
        "original_replayed",
        "reduced_witnesses",
        "reduced_replayed",
    )
    writer.write_csv(
        "trials.csv",
        [
            columns,
            *(
                tuple(cast(Cell, cast(dict[str, JSONValue], row)[key]) for key in columns)
                for row in rows
            ),
        ],
    )
    return {"completed": 0, "partial": 3, "interrupted": 130, "failed": 4}[status]
