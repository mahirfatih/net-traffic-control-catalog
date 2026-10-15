# out

Generated artifacts from the audit in
[`../../../scripts/analysis/`](../../../scripts/analysis/), rebuilt by
`build-matrix.py` and committed so the catalog documentation can reference them.

- `confusion-matrix.png` — counts and row-normalized matrices
- `correlated-terms.md` — chi-squared and LinearSVC model-weight terms per category
- `high-confidence-errors.md` — confident predictions that disagree
- `matrix-data.json` — raw numbers, model comparison, per-host top-3 predictions,
  and high-confidence errors

`matrix-data.json` carries the fields the documents are checked against:
`accuracy` and `balanced_accuracy` (they differ by 29 points, because `finance`
is over half the sample), `classes`, `folds` (3, dropped from 5 to suit the
smallest category), `thin_classes` (under 20 examples, so their per-class
scores are indicative), and `dropped_classes` (categories the audit could not
measure at all — empty when the whole catalog is covered).

Do not edit by hand — rerun the audit.
