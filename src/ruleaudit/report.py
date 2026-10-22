"""Bounded filesystem publication, with explicit partial files and no replacement."""

import json
import os
import re
from pathlib import Path

from ruleaudit.io import JSONValue


class IncompleteError(RuntimeError):
    pass


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
        destination = self.directory / filename
        if destination.exists():
            raise FileExistsError(f"report already exists: {destination}")
        temporary = self.directory / (filename + ".partial")
        available = min(
            4096 if status else 10 * 1024**2, self.remaining if status else self.remaining - 4096
        )
        size = 0
        encoder = json.JSONEncoder(
            ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
        with temporary.open("xb") as stream:
            for chunk in encoder.iterencode(data):
                encoded = chunk.encode("ascii")
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
