# out

Generated artifacts from the audit in
[`../../../scripts/analysis/`](../../../scripts/analysis/), rebuilt by
`build-matrix.py` and committed so the catalog documentation can reference them.

- `confusion-matrix.png` — counts and row-normalized matrices
- `correlated-terms.md` — chi-squared and LinearSVC model-weight terms per category
- `high-confidence-errors.md` — confident predictions that disagree
- `matrix-data.json` — raw numbers, model comparison, per-host top-3 predictions,
  and high-confidence errors

Do not edit by hand — rerun the audit.
