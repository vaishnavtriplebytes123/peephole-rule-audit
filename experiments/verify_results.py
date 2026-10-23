"""Verify published evidence offline; does not run a new experiment or use the network.

Run after installing ruleaudit: python experiments/verify_results.py
This checks stored hashes, counters, archives and audit reconstruction. Recorded
replay outcomes are checked for consistency; a fresh SMT replay is a separate CLI
operation described in results/README.md.
"""

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any

from ruleaudit.config import config_document
from ruleaudit.corpus import parse_corpus
from ruleaudit.evaluation_config import parse_evaluation_config, trials
from ruleaudit.io import canonical_bytes, content_hash, load_json


def read(path: Path) -> Any:
    return json.loads(path.read_bytes())


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    root = Path(__file__).resolve().parent / "results"
    inventory = read(root / "evidence-manifest.json")
    for name, digest in inventory["files"].items():
        path = root / name
        assert path.resolve().is_relative_to(root.resolve()), name
        assert sha(path.read_bytes()) == digest, name
    total = dict(trials=0, cases=0, witnesses=0, replayed=0, reconstructed=0)
    for manifest_file in sorted(root.glob("*/manifest.json")):
        directory = manifest_file.parent
        manifest = read(manifest_file)
        for name, digest in manifest["files"].items():
            assert Path(name).name == name
            assert sha((directory / name).read_bytes()) == digest, (directory, name)
        evaluation = read(directory / "evaluation.json")
        rows = (
            read(directory / "cases.json")["trials"]
            if (directory / "cases.json").exists()
            else [read(p) for p in sorted(directory.glob("trial-*-cases.json"))]
        )
        records = {row["directory"]: row["records"] for row in rows}
        assert len(rows) == len(evaluation["trials"]) == manifest["counts"]["trials"]
        case_count = 0
        for row in evaluation["trials"]:
            cases = records[row["directory"]]
            assert cases is not None  # All fixed primary cells have published reports.
            case_count += len(cases)
            assert len(cases) == row["cases_tested"]
            assert sum(c["comparable"] is True for c in cases) == row["comparable_cases"]
            assert sum(c["comparable"] is True and c["delta"] > 0 for c in cases) == row["findings"]
            assert sum(c["eligible_alternative"] is True for c in cases) == row["eligible_cases"]
            assert (
                sum(c["checked_alternative"] is True for c in cases)
                == row["checked_alternative_findings"]
            )
            assert all(c["cost_without"] - c["cost_with"] == c["delta"] for c in cases)
            assert row["primary_interference_cases"] == (
                row["eligible_cases"] if row["h"] >= 4 else 0
            )
            assert row["primary_interference_findings"] == (
                row["checked_alternative_findings"] if row["h"] >= 4 else 0
            )
        assert case_count == manifest["counts"]["cases"]
        witnesses = read(directory / "witnesses.json")["witnesses"]
        assert len(witnesses) == manifest["counts"]["witnesses"]
        for archive in sorted({w["archive"] for w in witnesses}):
            selected = [w for w in witnesses if w["archive"] == archive]
            with zipfile.ZipFile(directory / archive) as bundle:
                assert set(bundle.namelist()) == {w["entry"] for w in selected}
                for witness in selected:
                    data = bundle.read(witness["entry"])
                    value = json.loads(data)
                    assert len(data) == witness["bytes"]
                    assert sha(data) == witness["file_sha256"]
                    assert (
                        sha(canonical_bytes(value["payload"]))
                        == value["sha256"]
                        == witness["payload_sha256"]
                    )
        assert (
            sum(w["replay"]["status"] == "verified" for w in witnesses)
            == manifest["counts"]["replayed"]
        )
        inputs = {}
        for item in evaluation.get("heldout_inputs", []):
            saved = read(directory / item["file"])
            assert content_hash(saved) == item["hash"]
            assert len(saved["cases"]) == item["cases"]
            hashes = [case["input_hash"] for case in saved["cases"]]
            assert len(set(hashes)) == len(hashes)
            assert all(content_hash(c["input"]) == c["input_hash"] for c in saved["cases"])
            inputs[item["seed"]] = hashes
        if inputs:
            for row in evaluation["trials"]:
                actual = [c["input_hash"] for c in records[row["directory"]]]
                assert actual == inputs[row["seed"]][: len(actual)]
        parent: Any = load_json(directory / "evaluation.json")
        configs = {}
        for item in trials(
            parse_corpus(parent["corpus"]), parse_evaluation_config(parent["config"])
        ):
            config = config_document(item.config)
            configs[content_hash(config)] = config
        details = read(directory / "audit-details-manifest.json")
        reconstructed = 0
        for name, digest in details["files"].items():
            raw = (directory / name).read_bytes()
            assert sha(raw) == digest
            for item in json.loads(raw)["trials"]:
                header = item["details"]
                assert header is not None
                restored = {
                    **header,
                    "corpus": parent["corpus"],
                    "config": configs[header["config_hash"]],
                    "records": records[item["directory"]],
                }
                assert sha(canonical_bytes(restored)) == item["audit_sha256"]
                reconstructed += 1
        assert reconstructed == details["trials"]
        total["reconstructed"] += reconstructed
        for key in ("trials", "cases", "witnesses", "replayed"):
            total[key] += manifest["counts"][key]
        print(directory.name, manifest["counts"], flush=True)
    for folder, manifest_name in (
        ("checks", "checks-manifest.json"),
        ("installation", "installation-manifest.json"),
    ):
        directory = root / folder
        manifest = read(directory / manifest_name)
        for name, digest in manifest["files"].items():
            assert sha((directory / name).read_bytes()) == digest
        witnesses = read(directory / "witnesses.json")["witnesses"]
        assert len(witnesses) == manifest["witnesses"] == manifest["replayed"]
        with zipfile.ZipFile(directory / "witnesses.zip") as bundle:
            assert set(bundle.namelist()) == {w["entry"] for w in witnesses}
            for witness in witnesses:
                data = bundle.read(witness["entry"])
                assert sha(data) == witness["sha256"]
                value = json.loads(data)
                assert content_hash(value["payload"]) == value["sha256"]
                assert witness["replay"]["status"] == "verified"
        print(folder, len(witnesses), "supplementary witnesses", flush=True)
    assert total == dict(
        trials=6735, cases=47380, witnesses=5535, replayed=5535, reconstructed=6735
    )
    print("Verified primary totals", total, flush=True)


if __name__ == "__main__":
    main()
