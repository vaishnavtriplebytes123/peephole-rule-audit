"""Command-line boundary; later milestones add the research commands."""

import argparse
import os
import platform
import sys
from collections.abc import Sequence
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path
from typing import cast

from ruleaudit import __version__
from ruleaudit.corpus import corpus_document, load_corpus
from ruleaudit.io import InputError, JSONValue, canonical_bytes, content_hash
from ruleaudit.solver import SolverLimits, Z3Backend, check_rule


def _validate(rules_path: Path, output: Path, limits: SolverLimits) -> int:
    if output.exists():
        raise InputError("--out", "output path already exists; choose a new directory")
    corpus = load_corpus(rules_path)
    snapshot = corpus_document(corpus)
    backend = Z3Backend(limits)
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
    output.mkdir(parents=True, exist_ok=False)
    temporary = output / "validation.partial.json"
    with temporary.open("xb") as stream:
        stream.write(canonical_bytes(report))
        stream.flush()
        os.fsync(stream.fileno())
    destination = output / "validation.json"
    if os.name == "nt":
        # Windows rename is atomic and refuses an existing destination.
        temporary.rename(destination)
    else:
        # POSIX rename replaces destinations; hard links provide no-replace publication.
        os.link(temporary, destination)
        temporary.unlink()
    print(
        f"Validated {len(corpus.rules)} rules; status={report['status']}; "
        f"report={output / 'validation.json'}"
    )
    return 3 if partial else 0


def main(argv: Sequence[str] | None = None) -> int:
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
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    try:
        try:
            limits = SolverLimits(args.solver_timeout_ms, args.solver_max_calls)
        except ValueError as error:
            raise InputError("solver settings", str(error)) from error
        return _validate(args.rules, args.out, limits)
    except (InputError, FileExistsError) as error:
        print(f"ruleaudit: {error}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("ruleaudit: interrupted; validation did not complete", file=sys.stderr)
        return 130
    except OSError as error:
        print(f"ruleaudit: I/O failure: {error}", file=sys.stderr)
        return 4
    except Exception as error:
        print(f"ruleaudit: internal failure ({type(error).__name__}): {error}", file=sys.stderr)
        return 4
