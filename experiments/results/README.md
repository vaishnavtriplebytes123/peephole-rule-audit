# Full-study evidence

Each subdirectory represents one terminal command from
[the frozen run manifest](../full-run-manifest.json). The source batches are
all terminal, with every declared trial visited. These are full
study records, separate from the resource pilots and earlier smoke comparisons.

- `evaluation.json`, `trials.csv`, `status.json`: exact original root files.
- `cases.json`: every trial's case records, including zero deltas and partials.
  Held-out uses `trial-NNNNNN-cases.json` to keep each JSON file bounded.
- `heldout-inputs-NNNNNN.json`: exact saved concrete inputs, settings and attempts.
- `replays.json`: every recorded independent replay outcome, including any
  unknown/invalid/not-run states; no outcome filtering.
- `audit-details-NNNN.json`: every original audit-header field and child status,
  excluding only the deduplicated corpus/config/record fields. Original audit
  SHA-256 values allow exact reconstruction using root snapshots, actual configs
  and case rows. `audit-details-manifest.json` binds these bounded chunks.
- `witnesses-NNNN.zip`: every emitted original and reduced witness as plain JSON,
  split at 32 MiB uncompressed per bundle. Entries retain original trial/file names.
- `witnesses.json`: archive/entry mapping, file SHA-256, payload SHA-256, size,
  kind and original replay result for each witness.
- `manifest.json`: hashes of all published files and scope/counts. Its own hash
  is intentionally not self-referential. Counts sum reported case measurements;
  missing trial metrics remain null in the authoritative evaluation file.

The archives were read back and compared byte-for-byte with every original.
Audit details were reconstructed into complete original reports byte-for-byte.
The first three root manifests remain immutable; their audit-detail files have
a separate supplementary manifest. Later root manifests include those files too.
All original CLI directories remain untouched under ignored artifacts. JSON
files are at most 10 MiB. The archive envelope is not an executable rule format;
extract only into a new directory so existing work is preserved.

Example using the first emitted interference witness in trial/file order:

```powershell
.venv/Scripts/python.exe -m zipfile -l experiments/results/interference/witnesses-0001.zip
.venv/Scripts/python.exe -m zipfile -e experiments/results/interference/witnesses-0001.zip artifacts/restored-interference-NEW
.venv/Scripts/python.exe -m ruleaudit replay --witness artifacts/restored-interference-NEW/trial-000011/witness-000001.json --out artifacts/restored-interference-replay-NEW
```

The witness mapping provides the exact entry for any other case. No positive
delta, replay verification or safe-deletion conclusion follows from a missing
file or null denominator. Read actual statuses and the research report.


`summary.json` reports all primary scopes, modes, targets and seeds, distributions,
censoring, uniqueness and resources. `execution.json` preserves terminal driver
events. `checks/` contains the separate suffix, seven reruns, professor demo and
first performance smoke (39 additional emitted witnesses, all verified).
`installation/` contains the isolated wheel journey and same-process-affinity
smoke (27 additional emitted witnesses, all verified), plus archive replay.
These checks are not pooled into primary effect estimates.

After installing the package, verify all distributed file hashes, primary
counters, input prefixes, witness payloads and 6,735 reconstructed audit hashes:

```powershell
.venv/Scripts/python.exe experiments/verify_results.py
```

`evidence-manifest.json` binds every published JSON/CSV/ZIP data file, excluding
itself. This is an integrity check; it reads recorded SMT replay outcomes rather
than claiming a fresh replay of all 5,535 witnesses. Use the replay command on
extracted witnesses for a fresh semantic check. Configured solver/time limits can
produce different inconclusive outcomes on other hosts.
