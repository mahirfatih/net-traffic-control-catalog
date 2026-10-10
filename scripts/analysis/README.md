# scripts/analysis

The catalog reliability audit — a maintainer tool, not a check. It fetches each
catalog host's homepage, extracts the title, meta description/keywords, headings
and body, trains a TF-IDF + LinearSVC classifier on the labels and
cross-validates it, then writes the confusion matrix, per-class metrics,
**chi-squared correlated terms**, **LinearSVC model-weight terms**, **calibrated
top-3 predictions per host**, and high-confidence errors to
[`docs/analysis/out/`](../../docs/analysis/out/).

This is the one directory under `scripts/` that needs an install step:
`scikit-learn` and `matplotlib`. `test/test.sh` does not run it, and it is not
part of the catalog pipeline.

See [`../../docs/analysis/README.md`](../../docs/analysis/README.md) for the
methodology and the current result.
