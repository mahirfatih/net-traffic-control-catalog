# Analysis: catalog consistency

This directory holds a one-off analysis that fetches homepage text for the
hosts in `catalog.json`, trains a text classifier (TF-IDF + LinearSVC) on
our labels, and produces a confusion matrix showing how consistently our
labels agree with what a text model can recover.

**Not part of the shipped catalog pipeline.** The catalog repo's `scripts/`
are standard-library-only; this analysis needs `scikit-learn` and
`matplotlib`. It is excluded from `test/test.sh`.

## Usage

```bash
# 1. Install deps (arm64 wheels for Python 3.11+)
pip3 install scikit-learn matplotlib

# 2. Fetch pages (~5 min, cached under pages/)
python3 fetch-pages.py

# 3. Train + render matrix
python3 build-matrix.py
```

Outputs land in `out/`:

- `confusion-matrix.png` — the matrix (rows = catalog label, cols = prediction)
- `matrix-data.json` — raw numbers

## Result

**Accuracy: 65.7%** (518/789, 19 classes, 5-fold CV).

Read this number correctly:

- **It is consistency, not accuracy.** The model learns how well our own
  labels can be recovered from page text. 65.7% means about two-thirds of our
  labels are predictable from the page.
- **Highest:** `government` 92%, `messaging` 85% — categories that separate
  cleanly from page content.
- **Lowest:** `cdn` 35%, `social` 38%, `search` 42%, `transport` 43% — some
  of these are infrastructure (page text is meaningless). But examples like
  `apple.com → cdn` and `booking.com → search` may be real catalog errors.

Per-class accuracy ranges from 35% (`cdn`) to 92% (`government`). The
weakest classes are infrastructure categories whose page text is not
representative of the category. Notable off-diagonal predictions include
`apple.com` (labeled `software`, predicted `cdn`) and `booking.com` (labeled
`travel`, predicted `search`) — these may indicate mislabeled hosts.

## What the matrix does and does not measure

It does **not** measure whether our labels are *correct* — there is no
independent ground truth. It measures **self-consistency**: given the page
text, can a model recover our label? High diagonal = our labels are
predictable from page content. Off-diagonal = our label disagrees with what
the text suggests (either the label is wrong, or the page is not
representative of the category).

Infrastructure hosts (CDNs, analytics, ads) have no meaningful page text,
so they are naturally filtered out by `--min-text`.
