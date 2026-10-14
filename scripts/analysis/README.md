# scripts/analysis

The catalog reliability audit — a maintainer tool, not a check. It fetches each
catalog host's homepage, extracts the title, meta description/keywords, headings
and body, compares TF-IDF classifiers, keeps LinearSVC for the detailed audit,
and cross-validates it. It then writes the model comparison, confusion matrix,
per-class metrics, **chi-squared correlated terms**, **LinearSVC model-weight
terms**, **calibrated top-3 predictions per host**, and high-confidence errors to
[`docs/analysis/out/`](../../docs/analysis/out/).

It measures **every category in the catalog**, not only the large ones. Two
things make that work: `fetch-pages.py --retry-empty` re-fetches hosts whose
first attempt came back empty (a category used to drop out of the matrix
whenever its first fetch happened to fail), and `build-matrix.py` keeps
categories down to two examples, lowering the fold count to suit the smallest
one. Categories under 20 examples are recorded as `thin_classes`, and their
per-class scores should be read as indicative rather than measured.

`accuracy` and `balanced_accuracy` are both written for a reason: `finance` is
53% of the catalog, so accuracy mostly reports how well the model predicts
`finance`, and balanced accuracy weights every category equally. The second is
the one that describes the labels as a whole.

This is the one directory under `scripts/` that needs an install step:
`scikit-learn` and `matplotlib`. `test/test.sh` does not run it, and it is not
part of the catalog pipeline.

See [`../../docs/analysis/README.md`](../../docs/analysis/README.md) for the
methodology and the current result.
