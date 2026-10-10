# scripts

Tooling for this catalog. Python 3 standard library and Node — **no
dependencies, no install step** — for everything under `scripts/`, with one
exception: `scripts/analysis/` is a maintainer audit that needs `scikit-learn`
and `matplotlib`. It is not a check and `test/test.sh` does not run it. A data
repository's checks should be runnable by anybody who opened a pull request.

## Run everything

```sh
./test/test.sh
```

Registry → schema → build → validate → build fidelity → docs → licence gate →
compile. No network, no build system.

## What each script does

### Catalog — [`catalog/`](catalog/)

| Script | What it does |
| :--- | :--- |
| [`generate.py`](catalog/generate.py) | Builds `catalog.json` from the `seeds/` files. Deterministic, and validates **before** writing — a bad seed writes nothing. |
| [`validate.py`](catalog/validate.py) | Checks a `catalog.json` against the format and the category vocabulary. Exits non-zero on any problem. |
| [`build-catalog-docs.py`](catalog/build-catalog-docs.py) | Generates `docs/CATALOG.md` from `catalog.json`, so the counts in the prose cannot drift from the shipped data. |
| [`catalog-core.py`](catalog/catalog-core.py) | Shared load / normalise / validate / write logic. Not run on its own. |

### Sources — [`sources/`](sources/)

| Script | What it does |
| :--- | :--- |
| [`sources.py`](sources/sources.py) | The source registry, and the licence gate. `python3 scripts/sources/sources.py` lists every source and its verdict; `--check` validates the registry; `--allowed` lists only what may be fetched. |
| [`harvest.py`](sources/harvest.py) | Fetches allowed sources, drops hosts the catalog already covers, applies `rules.json`, and reports what no rule matched. |
| [`merge.py`](sources/merge.py) | Applies harvested categories to `seeds/categories.json`. Refuses to overwrite an existing label. |

### Checks — [`checks/`](checks/)

| Script | What it does |
| :--- | :--- |
| [`check-docs-fresh.mjs`](checks/check-docs-fresh.mjs) | Static drift check: broken links, renamed scripts, stale counts, a licence verdict that contradicts itself. |

### Analysis — [`analysis/`](analysis/)

| Script | What it does |
| :--- | :--- |
| [`fetch-pages.py`](analysis/fetch-pages.py) | Audit: fetch each catalog host's homepage and cache its title/meta/headings/body under `analysis/.pages/` (gitignored). Standard library only. |
| [`build-matrix.py`](analysis/build-matrix.py) | Audit: classify the cached pages, cross-validate against the labels, and write the confusion matrix + report to [`docs/analysis/out/`](../docs/analysis/out/). Needs `scikit-learn` and `matplotlib`. |

## Harvest workflow

```sh
python3 scripts/sources/harvest.py                    # fetch, filter, apply rules
python3 scripts/sources/merge.py evidence/harvested-categories.json --dry-run
python3 scripts/sources/merge.py evidence/harvested-categories.json
python3 scripts/catalog/build-catalog-docs.py         # refresh docs/CATALOG.md
./test/test.sh
```

`harvest.py` writes `evidence/harvested-categories.json`, which is gitignored: it is an
intermediate, and the seeds are the source of truth.

### What the harvest will not do

- **Invent a category.** No rule, no label — the host goes to
  `docs/NEEDS-REVIEW.md`.
- **Write `other` automatically.** `other` means a person looked and did not
  know, so only a rule may produce it.
- **Overwrite a label.** Conflicts are printed; the seed wins.
- **Drop a line it does not parse.** Unparsable lines are reported, because a
  parser that skips silently is how a catalog goes quietly wrong.

## Catalog reliability analysis

```sh
cd scripts/analysis
python3 -m venv .venv && .venv/bin/pip install scikit-learn matplotlib
.venv/bin/python fetch-pages.py     # cache each host's homepage (~3 min)
.venv/bin/python build-matrix.py    # ← writes docs/analysis/out/
```

It fetches each host's homepage, extracts the title, meta description/keywords,
headings and body, trains a TF-IDF + LinearSVC classifier on the labels and
cross-validates it (5-fold) — so the confusion matrix, per-class
precision/recall/F1, chi-squared correlated terms and high-confidence errors
land in [`docs/analysis/out/`](../docs/analysis/out/) next to the data they
judge. It measures **self-consistency** (how predictable a label is from its
page), not correctness. It needs `scikit-learn` and `matplotlib` and is **not**
run by `test/test.sh`.

## Fetching

`harvest.py` caches every response in `evidence/`, so `--offline` re-runs the
whole pipeline with no network and produces the same result. Use it to check a
change to `rules.json` without re-downloading.

## Adding a source

See [`../docs/SOURCES.md`](../docs/SOURCES.md). Append to `sources.json`, then
run `python3 scripts/sources/sources.py --check`.

A blocking licence (`NC`, `SA`) with `allowed: true` is a hard error. That is
deliberate: this data is CC0 and ships inside a commercial app.