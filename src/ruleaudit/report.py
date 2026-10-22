"""Bounded filesystem publication, with explicit partial files and no replacement."""

import csv
import io
import json
import os
import re
import unicodedata
from collections.abc import Iterable, Iterator, Sequence
from pathlib import Path

from ruleaudit.io import JSONValue


class IncompleteError(RuntimeError):
    pass


type Cell = str | int | float | bool | None


def csv_cell(value: Cell) -> Cell:
    if value is None:
        return ""
    if isinstance(value, str):
        index = 0
        while index < len(value) and (
            value[index].isspace() or unicodedata.category(value[index]) in {"Cc", "Cf"}
        ):
            index += 1
        if value[index : index + 1] in ("=", "+", "-", "@"):
            return "'" + value
    return value


class ReportWriter:
    def __init__(self, directory: Path, max_bytes: int) -> None:
        if type(max_bytes) is not int or not 8192 <= max_bytes <= 1024**3:
            raise ValueError("invalid output byte budget")
        directory.mkdir(parents=True, exist_ok=False)
        self.directory = directory
        self.remaining = max_bytes

    def write(self, filename: str, data: JSONValue, *, status: bool = False) -> None:
        if re.fullmatch(r"[A-Za-z0-9_-]+\.json", filename) is None:
            raise ValueError("report filename must be a plain JSON filename")
        encoder = json.JSONEncoder(
            ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
        self._publish(
            filename, (chunk.encode("ascii") for chunk in encoder.iterencode(data)), status=status
        )

    def write_csv(self, filename: str, rows: Iterable[Sequence[Cell]]) -> None:
        if re.fullmatch(r"[A-Za-z0-9_-]+\.csv", filename) is None:
            raise ValueError("report filename must be a plain CSV filename")

        def chunks() -> Iterator[bytes]:
            for row in rows:
                buffer = io.StringIO(newline="")
                csv.writer(buffer, lineterminator="\r\n").writerow(csv_cell(cell) for cell in row)
                yield buffer.getvalue().encode("utf-8")

        self._publish(filename, chunks())

    def _publish(self, filename: str, chunks: Iterable[bytes], *, status: bool = False) -> None:
        destination = self.directory / filename
        if destination.exists():
            raise FileExistsError(f"report already exists: {destination}")
        temporary = self.directory / (filename + ".partial")
        available = min(
            4096 if status else 10 * 1024**2, self.remaining if status else self.remaining - 4096
        )
        size = 0
        with temporary.open("xb") as stream:
            for encoded in chunks:
                if size + len(encoded) > available:
                    raise IncompleteError("report-size-limit; partial file retained")
                stream.write(encoded)
                size += len(encoded)
                self.remaining -= len(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        if os.name == "nt":
            temporary.rename(destination)
        else:
            os.link(temporary, destination)
            temporary.unlink()
