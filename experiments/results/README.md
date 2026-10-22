# Full-study evidence

Each subdirectory represents one terminal command from
[the frozen run manifest](../full-run-manifest.json). The source batches are
still executing; their directories will be added when terminal. These are full
study records, separate from the resource pilots and earlier smoke comparisons.

- `evaluation.json`, `trials.csv`, `status.json`: exact original root files.
- `cases.json`: every trial's case records, including zero deltas and partials.
  Held-out uses `trial-NNNNNN-cases.json` to keep each JSON file bounded.
- `heldout-inputs-NNNNNN.json`: exact saved concrete inputs, settings and attempts.
- `replays.json`: every recorded independent replay outcome, including any
  unknown/invalid/not-run states; no outcome filtering.
- `witnesses-NNNN.zip`: every emitted original and reduced witness as plain JSON,
  split at 32 MiB uncompressed per bundle. Entries retain original trial/file names.
- `witnesses.json`: archive/entry mapping, file SHA-256, payload SHA-256, size,
  kind and original replay result for each witness.
- `manifest.json`: hashes of all published files and scope/counts. Its own hash
  is intentionally not self-referential. Counts sum reported case measurements;
  missing trial metrics remain null in the authoritative evaluation file.

The archives were read back and compared byte-for-byte with every original.
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
