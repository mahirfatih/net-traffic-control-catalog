# scripts

Tooling for this catalog. Python 3 standard library and Node — **no
dependencies, no install step**. A data repository's checks should be runnable
by anybody who opened a pull request.

## Run everything

```sh
./test/test.sh
```

Registry → schema → build → validate → build fidelity → docs → licence gate →
compile. No network, no build system.

## What each script does

| Script | What it does |
| :--- | :--- |
| [`generate.py`](generate.py) | Builds `catalog.json` from the `seeds/` files. Deterministic, and validates **before** writing — a bad seed writes nothing. |
| [`validate.py`](validate.py) | Checks a `catalog.json` against the format and the category vocabulary. Exits non-zero on any problem. |
| [`build-catalog-docs.py`](build-catalog-docs.py) | Generates `docs/CATALOG.md` from `catalog.json`, so the counts in the prose cannot drift from the shipped data. |
| [`check-docs-fresh.mjs`](check-docs-fresh.mjs) | Static drift check: broken links, renamed scripts, stale counts, a licence verdict that contradicts itself. |
| [`catalog-core.py`](catalog-core.py) | Shared load / normalise / validate / write logic. Not run on its own. |
| [`sources.py`](sources.py) | The source registry, and the licence gate. `python3 scripts/sources.py` lists every source and its verdict; `--check` validates the registry; `--allowed` lists only what may be fetched. |
| [`harvest.py`](harvest.py) | Fetches allowed sources, drops hosts the catalog already covers, applies `rules.json`, and reports what no rule matched. |
| [`merge.py`](merge.py) | Applies harvested categories to `seeds/categories.json`. Refuses to overwrite an existing label. |
| [`probe.py`](probe.py) | Optional. Asks an external categoriser for evidence and caches it. Sets no category. |

## Harvest workflow

```sh
python3 scripts/harvest.py                    # fetch, filter, apply rules
python3 scripts/merge.py evidence/harvested-categories.json --dry-run
python3 scripts/merge.py evidence/harvested-categories.json
python3 scripts/build-catalog-docs.py         # refresh docs/CATALOG.md
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

## Fetching

`harvest.py` caches every response in `evidence/`, so `--offline` re-runs the
whole pipeline with no network and produces the same result. Use it to check a
change to `rules.json` without re-downloading.

## Adding a source

See [`../docs/SOURCES.md`](../docs/SOURCES.md). Append to `sources.json`, then
run `python3 scripts/sources.py --check`.

A blocking licence (`NC`, `SA`) with `allowed: true` is a hard error. That is
deliberate: this data is CC0 and ships inside a commercial app.