"""Command-line boundary; later milestones add the research commands."""

import argparse
import io
import platform
import sys
from collections.abc import Callable, Sequence
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path
from time import perf_counter
from typing import cast

from ruleaudit import __version__
from ruleaudit.config import load_config
from ruleaudit.corpus import Corpus, corpus_document, load_corpus
from ruleaudit.evaluate import evaluate
from ruleaudit.evaluation_config import parse_evaluation_config, validate_evaluation
from ruleaudit.experiment import audit_experiment, derive_experiment, validate_settings
from ruleaudit.interrupt import interruptible_clock
from ruleaudit.io import InputError, JSONValue, content_hash, load_json, parse_expression
from ruleaudit.ir import measure
from ruleaudit.reduce import parse_reduction_config, reduce_witness
from ruleaudit.replay import replay
from ruleaudit.report import Cell, IncompleteError, ReportWriter
from ruleaudit.solver import SolverLimits, Z3Backend, check_rule


def _validate(
    corpus: Corpus,
    writer: ReportWriter,
    limits: SolverLimits,
    *,
    now: Callable[[], float] = perf_counter,
) -> int:
    snapshot = corpus_document(corpus)
    backend = Z3Backend(limits, now=now)
    results: list[JSONValue] = []
    partial = False
    for rule in corpus.rules:
        result = check_rule(rule, backend=backend)
        partial |= result.status == "unknown"
        results.append(
            {
                "id": rule.id,
                "status": result.status,
                "valuation": {name: value for name, value in result.valuation},
                "reason": result.reason,
                "warning": result.warning,
            }
        )
    report: dict[str, JSONValue] = {
        "schema_version": 1,
        "tool_version": __version__,
        "python_version": platform.python_version(),
        "z3_version": version("z3-solver"),
        "status": "partial" if partial else "completed",
        "corpus": snapshot,
        "corpus_hash": content_hash(snapshot),
        "solver_settings": cast(dict[str, JSONValue], asdict(limits)),
        "solver_calls": backend.calls,
        "results": results,
    }
    writer.write("validation.json", report)
    writer.write_csv(
        "rules.csv",
        [
            ("id", "status", "reason", "warning"),
            *(
                tuple(
                    cast(Cell, cast(dict[str, JSONValue], result)[key])
                    for key in ("id", "status", "reason", "warning")
                )
                for result in results
            ),
        ],
    )
    return 3 if partial else 0


def _save_status(writer: ReportWriter | None, status: str, reason: str) -> None:
    if writer is None:
        return
    try:
        writer.write("status.json", {"status": status, "reason": reason[:512]}, status=True)
    except (OSError, IncompleteError, ValueError, KeyboardInterrupt) as error:
        print(f"ruleaudit: could not save status: {error}", file=sys.stderr)


def _reduce(
    value: JSONValue,
    settings: JSONValue,
    writer: ReportWriter,
    *,
    now: Callable[[], float] = perf_counter,
) -> int:
    result = reduce_witness(value, parse_reduction_config(settings), now=now)
    payload = cast(dict[str, JSONValue], result["payload"])
    original = cast(
        dict[str, JSONValue], cast(dict[str, JSONValue], payload["original"])["payload"]
    )
    final = cast(dict[str, JSONValue], payload["final"])
    pair = cast(dict[str, JSONValue], final["paired"])
    summary: dict[str, JSONValue] = {
        "schema_version": 1,
        "original_hash": cast(dict[str, JSONValue], payload["original"])["sha256"],
        "witness_hash": result["sha256"],
        "nodes_before": measure(
            parse_expression({"schema_version": 1, "expression": original["input"]})
        ).nodes,
        "nodes_after": measure(
            parse_expression({"schema_version": 1, "expression": final["input"]})
        ).nodes,
        "accepted": len(cast(list[JSONValue], payload["steps"])),
        "delta": pair["delta"],
        **{
            key: payload[key]
            for key in (
                "status",
                "reason",
                "attempts",
                "solver_calls",
                "preparation_seconds",
                "elapsed",
                "method",
                "reduction_config",
            )
        },
    }
    writer.write("witness.json", result)
    writer.write("reduction.json", summary)
    columns = ("nodes_before", "nodes_after", "accepted", "delta", "attempts", "status", "reason")
    writer.write_csv("summary.csv", [columns, tuple(cast(Cell, summary[key]) for key in columns)])
    return {"completed": 0, "partial": 3, "interrupted": 130}[cast(str, payload["status"])]


def main(argv: Sequence[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(errors="backslashreplace")
    with interruptible_clock() as now:
        return _main(argv, now)


def _main(argv: Sequence[str] | None, now: Callable[[], float]) -> int:
    parser = argparse.ArgumentParser(
        prog="ruleaudit",
        description="Bounded peephole rule-removal audit research CLI.",
        epilog="Operator count is a structural cost; it does not measure CPU runtime.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command")
    validate = commands.add_parser(
        "validate", help="validate a bounded, versioned JSON rule corpus"
    )
    validate.add_argument("--rules", type=Path, required=True)
    validate.add_argument("--out", type=Path, required=True, help="new output directory")
    validate.add_argument("--solver-timeout-ms", type=int, default=1000)
    validate.add_argument("--solver-max-calls", type=int, default=1000)
    for name in ("derive", "audit"):
        command = commands.add_parser(name, help=f"run bounded {name} research work")
        command.add_argument("--rules", type=Path, required=True)
        command.add_argument("--config", type=Path, required=True)
        command.add_argument("--target", required=True)
        command.add_argument("--out", type=Path, required=True)
    replay_command = commands.add_parser(
        "replay", help="recompute a self-contained removal witness"
    )
    replay_command.add_argument("--witness", type=Path, required=True)
    replay_command.add_argument("--out", type=Path, required=True)
    reduce_command = commands.add_parser(
        "reduce", help="shrink a witness while preserving its checked regression"
    )
    reduce_command.add_argument("--witness", type=Path, required=True)
    reduce_command.add_argument("--config", type=Path, required=True)
    reduce_command.add_argument("--out", type=Path, required=True)
    evaluate_command = commands.add_parser(
        "evaluate", help="run controlled generator comparisons or held-out random inputs"
    )
    evaluate_command.add_argument("--rules", type=Path, required=True)
    evaluate_command.add_argument("--config", type=Path, required=True)
    evaluate_command.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    writer: ReportWriter | None = None
    try:
        if args.out.exists():
            raise InputError("--out", "output path already exists; choose a new directory")
        if args.command == "validate":
            try:
                limits = SolverLimits(args.solver_timeout_ms, args.solver_max_calls)
            except ValueError as error:
                raise InputError("solver settings", str(error)) from error
            corpus = load_corpus(args.rules)
            writer = ReportWriter(args.out, 100 * 1024**2)
            code = _validate(corpus, writer, limits, now=now)
        elif args.command == "replay":
            data = load_json(args.witness)
            writer = ReportWriter(args.out, 8192)
            result = replay(data, now=now)
            writer.write("replay.json", result)
            code = 0
        elif args.command == "reduce":
            value, settings = load_json(args.witness), load_json(args.config)
            limits_reduction = parse_reduction_config(settings)
            writer = ReportWriter(args.out, limits_reduction.max_output_bytes)
            code = _reduce(value, settings, writer, now=now)
        elif args.command == "evaluate":
            corpus = load_corpus(args.rules)
            matrix = parse_evaluation_config(load_json(args.config))
            validate_evaluation(corpus, matrix)
            writer = ReportWriter(args.out, matrix.max_output_bytes)
            code = evaluate(corpus, matrix, writer, now=now)
        else:
            corpus, config = load_corpus(args.rules), load_config(args.config)
            target = validate_settings(corpus, config, args.target)
            writer = ReportWriter(args.out, config.max_output_bytes)
            try:
                code = (derive_experiment if args.command == "derive" else audit_experiment)(
                    corpus, config, target, writer, now=now
                )
            except ValueError as error:
                raise InputError("experiment", str(error)) from error
        now()
        status = {0: "completed", 3: "partial", 4: "failed", 130: "interrupted"}[code]
        writer.write("status.json", {"status": status}, status=True)
        print(f"{args.command}: {status}; reports={args.out}")
        return code
    except (InputError, FileExistsError) as error:
        _save_status(writer, "failed", str(error))
        print(f"ruleaudit: {error}", file=sys.stderr)
        return 2
    except IncompleteError as error:
        _save_status(writer, "partial", str(error))
        print(f"ruleaudit: partial: {error}", file=sys.stderr)
        return 3
    except KeyboardInterrupt:
        _save_status(writer, "interrupted", "work interrupted")
        print("ruleaudit: interrupted; work did not complete", file=sys.stderr)
        return 130
    except OSError as error:
        _save_status(writer, "failed", str(error))
        print(f"ruleaudit: I/O failure: {error}", file=sys.stderr)
        return 4
    except Exception as error:
        _save_status(writer, "failed", str(error))
        print(f"ruleaudit: internal failure ({type(error).__name__}): {error}", file=sys.stderr)
        return 4
