# test

The whole suite. Nothing here needs a network, a build system, or an install
step — Python 3 standard library and Node are the only requirements.

```sh
./test/test.sh          # all eleven steps
./test/test.sh --fast   # skip the byte-compile sweep
```

**Exit code `0` means the shipped data is consistent with its seeds and its
documents.** Any non-zero stops the run at the first failure, because a later
step reporting a problem that an earlier one caused is noise.

## What each step proves

| # | Step | What it catches |
| --: | :--- | :--- |
| 1 | Source registry | a source marked `allowed` on a licence that blocks it, a blocked source with no reason, a bad URL or id |
| 2 | Seeds parse | a category outside the vocabulary, an unsorted seed file, a duplicate service `key` |
| 2b | Service domains labelled | a product's domain that resolves to no category — correct grouping, wrong label |
| 3 | `catalog.json` hand-edited | **runs before the build**, because the build would silently repair the mistake |
| 4 | Build | a seed that fails validation; nothing is written when it does |
| 5 | Validator | the format, the vocabulary, and every host's shape |
| 6 | Build fidelity | `catalog.json` differing from the seeds it was built from |
| 7 | Docs current | a document that changed when regenerated — i.e. edited by hand |
| 8 | Docs describe reality | broken links, renamed scripts, stale counts, a licence verdict that contradicts itself |
| 9 | Licence gate | `NC` and `SA` licences refused even when a record claims `allowed` — tested against synthetic records, so it does not depend on a blocked source being present |
| 10 | Host shape | 11 malformed names (`*.example.com`, `exa mple.com`, `exämple.com`, `example.com.`…) the app could never match |
| 11 | Byte-compile | a script that no longer parses |

## Why step 3 is where it is

`generate.py` overwrites `catalog.json`. If that check ran after the build, a
hand edit would be repaired and reported as clean — the one failure mode this
repository cannot afford, because the output is what the app ships.

## Running one check

There is no per-step flag on purpose: the steps are fast enough that selecting
among them costs more than running them. To run one script directly:

```sh
python3 scripts/catalog/validate.py
python3 scripts/sources/sources.py --check
node scripts/checks/check-docs-fresh.mjs
```

## Where output goes

Nowhere. Every check prints to stdout and reports through its exit code, so
the suite is usable from a pre-push hook or a CI step without redirection.