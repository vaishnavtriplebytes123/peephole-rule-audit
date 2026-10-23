"""The preregistered Add5/100003 coverage supplement; never changes primary results.

Run only after the full matrix driver is terminal. Uses the frozen ruleaudit APIs
on the saved positions 749–2000; this is a research procedure, not a CLI mode.
"""

import argparse
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from time import process_time
from typing import cast

from ruleaudit.audit import audit_case, check_corpus
from ruleaudit.config import config_document
from ruleaudit.corpus import parse_corpus
from ruleaudit.derive import derive
from ruleaudit.evaluation_config import parse_evaluation_config, trials
from ruleaudit.experiment import derivation_result_document, snapshots, validate_settings
from ruleaudit.generate import random_attempt
from ruleaudit.interrupt import interruptible_clock
from ruleaudit.io import (
    InputError,
    JSONValue,
    canonical_bytes,
    content_hash,
    expression_node,
    load_json,
)
from ruleaudit.metrics import case_key
from ruleaudit.records import EncodingBudget, case_document, ground_alternative, make_witness
from ruleaudit.replay import replay
from ruleaudit.report import IncompleteError, ReportWriter
from ruleaudit.solver import Z3Backend


def run(primary: Path, output: Path, *, now: Callable[[], float]) -> int:
    parent = cast(dict[str, JSONValue], load_json(primary / "evaluation.json"))
    trial_rows = cast(list[dict[str, JSONValue]], parent["trials"])
    selected = [r for r in trial_rows if r["target"] == "jog_pAdd5" and r["seed"] == 100003]
    if len(selected) != 1:
        raise InputError("primary", "expected the one preregistered Add5/100003 trial")
    trial = selected[0]
    directory = cast(str, trial["directory"])
    if directory != "trial-000011" or trial["status"] != "partial":
        raise InputError("primary", "unexpected trial identity/status")
    corpus = parse_corpus(parent["corpus"])
    matrix = parse_evaluation_config(parent["config"])
    candidates = [
        item.config
        for item in trials(corpus, matrix)
        if item.target == "jog_pAdd5" and item.config.generation.seed == 100003
    ]
    if len(candidates) != 1:
        raise InputError("primary.config", "expected one saved config for Add5/100003")
    config = candidates[0]
    target = validate_settings(corpus, config, "jog_pAdd5")
    audit = cast(dict[str, JSONValue], load_json(primary / "trial-000011-cases.json"))
    prefix = cast(list[dict[str, JSONValue]], audit["records"])
    if len(prefix) != 748 or prefix[-1]["semantic_status"] != "unknown":
        raise InputError("primary", "expected the retained 748-input prefix and final unknown")
    input_files = cast(list[dict[str, JSONValue]], parent["heldout_inputs"])
    source_input = next(item for item in input_files if item["seed"] == 100003)
    if source_input["file"] != "heldout-inputs-000001.json":
        raise InputError("primary.inputs", "unexpected fixed input filename")
    input_doc = cast(dict[str, JSONValue], load_json(primary / source_input["file"]))
    saved = cast(list[dict[str, JSONValue]], input_doc["cases"])
    if (
        len(saved) != 2000
        or [r["input_hash"] for r in prefix] != [r["input_hash"] for r in saved[:748]]
        or config.generation.strategy != "random"
        or config.generation.seed != 100003
        or config.run.h != 4
        or config.seconds != 600
        or config.solver.max_calls != 100000
        or config.solver.timeout_ms != 1000
        or config.max_output_bytes != 64 * 1024**2
        or content_hash(config_document(config)) != trial["config_hash"]
        or content_hash(input_doc) != source_input["hash"]
    ):
        raise InputError("primary", "saved input/config consistency check failed")
    writer = ReportWriter(output, config.max_output_bytes)
    writer.write("config.json", config_document(config))
    selection: dict[str, JSONValue] = {
        "primary_evaluation_hash": content_hash(parent),
        "input_snapshot_hash": content_hash(input_doc),
        "primary_directory": directory,
        "retained_prefix_count": 748,
        "retained_unknown_input_hash": prefix[-1]["input_hash"],
        "first_position": 749,
        "last_position": 2000,
        "policy": "Untouched suffix; retain inconclusive pairs; no primary replacement",
    }
    writer.write("selection.json", selection)
    started, cpu_started = now(), process_time()
    deadline = started + config.seconds
    backend = Z3Backend(config.solver, deadline=deadline, now=now)
    records: list[JSONValue] = []
    outcomes: list[JSONValue] = []
    findings = comparable = eligible = qualification_unknowns = 0
    status, reason = "completed", "all saved suffix inputs attempted"
    derived_doc: JSONValue = None
    raw_bytes = 0
    try:
        validation = check_corpus(corpus, backend=backend)
        if validation.checked is None:
            raise IncompleteError("supplement corpus validation did not verify")
        paths = derive(
            target,
            corpus.rules,
            replace(config.search, seconds=min(config.search.seconds, max(0.0, deadline - now()))),
            config.generation.constants,
            backend=backend,
            now=now,
        )
        derived_doc = derivation_result_document(paths)
        if paths.reason == "interrupted":
            raise KeyboardInterrupt
        if paths.status == "partial":
            status, reason = "partial", paths.reason
        for position, item in enumerate(saved[748:], 749):
            if now() >= deadline or backend.calls >= config.solver.max_calls:
                raise IncompleteError("supplement time/query cap")
            case = random_attempt(config.generation, cast(int, item["attempt"]))
            if case is None or expression_node(case.expression) != item["input"]:
                raise InputError("supplement.input", "seed/attempt did not reproduce saved tree")
            key = content_hash(expression_node(case.expression))
            if key != item["input_hash"]:
                raise InputError("supplement.input", "input hash mismatch")
            pair = audit_case(
                case.expression,
                target.id,
                validation.checked,
                config.schedule,
                config.run,
                backend=backend,
                now=now,
            )
            eligibility: bool | None = None
            length: int | None = None
            filename: str | None = None
            if pair.comparable and pair.delta > 0:
                try:
                    witness = make_witness(
                        corpus, config, case, pair, paths.witnesses, backend=backend
                    )
                    alternative = cast(dict[str, JSONValue], witness["payload"])["alternative"]
                    eligibility = alternative is not None
                    if isinstance(alternative, dict):
                        length = len(cast(list[JSONValue], alternative["steps"]))
                except IncompleteError:
                    qualification_unknowns += 1
                    witness = make_witness(corpus, config, case, pair, (), backend=backend)
                # Reserve the bounded raw summary before publishing another witness.
                if writer.remaining < len(canonical_bytes(witness)) + 10 * 1024**2:
                    raise IncompleteError("supplement output cap before witness")
                filename = f"witness-{findings + 1:06d}.json"
                writer.write(filename, witness)
                findings += 1
            elif pair.comparable:
                eligibility = False
                try:
                    for template in paths.witnesses:
                        grounded = ground_alternative(
                            template,
                            case.expression,
                            target,
                            corpus,
                            config.run,
                            backend,
                            EncodingBudget(),
                        )
                        if grounded is not None:
                            eligibility = True
                            length = len(cast(list[JSONValue], grounded["steps"]))
                            break
                except IncompleteError:
                    eligibility = None
                    qualification_unknowns += 1
            record: dict[str, JSONValue] = {
                "position": position,
                "input_hash": key,
                "case_key": case_key(key, target.id, cast(str, parent["corpus_hash"]), config),
                "provenance": case_document(case, EncodingBudget()),
                "cost_with": pair.cost_with,
                "cost_without": pair.cost_without,
                "delta": pair.delta,
                "comparable": pair.comparable,
                "semantic_status": pair.semantic_status,
                "stop_with": pair.with_target.stop_reason,
                "stop_without": pair.without_target.stop_reason,
                "eligible_alternative": eligibility,
                "alternative_steps": length,
                "witness": filename,
            }
            size = len(canonical_bytes(record)) + 1
            if raw_bytes + size > 9 * 1024**2:
                raise IncompleteError("supplement record cap")
            records.append(record)
            raw_bytes += size
            comparable += int(pair.comparable)
            eligible += int(eligibility is True)
            if pair.semantic_status == "invalid":
                status, reason = "failed", "invalid paired semantics"
                break
        for path in sorted(output.glob("witness-*.json")):
            if now() >= deadline:
                raise IncompleteError("supplement time cap during replay")
            try:
                result = replay(load_json(path), now=now)
                outcomes.append(
                    {
                        "file": path.name,
                        "status": result["status"],
                        "witness_hash": result["witness_hash"],
                    }
                )
            except IncompleteError as error:
                outcomes.append({"file": path.name, "status": "unknown", "reason": str(error)})
                status, reason = "partial", "supplement replay inconclusive"
            except InputError as error:
                outcomes.append({"file": path.name, "status": "invalid", "reason": str(error)})
                status, reason = "failed", "supplement witness failed replay"
                break
    except IncompleteError as error:
        status, reason = "partial", str(error)
    except KeyboardInterrupt:
        status, reason = "interrupted", "supplement interrupted"
    except InputError as error:
        status, reason = "failed", str(error)
    reported = {cast(dict[str, JSONValue], item)["file"] for item in outcomes}
    for path in sorted(output.glob("witness-*.json")):
        if path.name not in reported:
            outcomes.append({"file": path.name, "status": "not-run", "reason": reason})
    if status == "completed" and (comparable != len(records) or qualification_unknowns):
        status, reason = "partial", "coverage attempted with inconclusive classifications"
    report: dict[str, JSONValue] = {
        **snapshots(corpus, config, target),
        "kind": "heldout-coverage-supplement",
        "selection": selection,
        "status": status,
        "reason": reason,
        "derivation": derived_doc,
        "requested_cases": 1252,
        "cases_tested": len(records),
        "not_run": 1252 - len(records),
        "comparable_cases": comparable,
        "findings": findings,
        "eligible_cases": eligible,
        "qualified_findings": sum(
            cast(dict[str, JSONValue], r)["eligible_alternative"] is True
            and cast(int, cast(dict[str, JSONValue], r)["delta"]) > 0
            for r in records
        ),
        "qualification_unknowns": qualification_unknowns,
        "pair_unknowns": sum(
            cast(dict[str, JSONValue], r)["semantic_status"] == "unknown" for r in records
        ),
        "solver_calls_search": backend.calls,
        "records": records,
        "replays": outcomes,
        "elapsed": now() - started,
        "cpu_seconds": process_time() - cpu_started,
    }
    writer.write("supplement.json", report)
    writer.write("status.json", {"status": status, "reason": reason}, status=True)
    print(f"suffix: {status}; cases={len(records)}/1252; findings={findings}; out={output}")
    return {"completed": 0, "partial": 3, "failed": 4, "interrupted": 130}[status]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--primary", type=Path, default=Path("experiments/results/heldout"))
    parser.add_argument("--out", type=Path, required=True)
    options = parser.parse_args()
    with interruptible_clock() as clock:
        raise SystemExit(run(options.primary, options.out, now=clock))
