# scripts/release

Release chores for the catalog.

`bump-version.sh` bumps the catalog **format version** — the integer `version`
field in `catalog.json`. That field is the *format* version: it changes only
when the file's shape breaks compatibility (a field added, removed or renamed
that the app must handle). It is not a data version — the data changes on every
regenerate without touching it.

The canonical source is [`../catalog/generate.py`](../catalog/generate.py), which
writes the field, and [`../catalog/catalog-core.py`](../catalog/catalog-core.py),
which validates it. The script updates both, [`../../config/schema.json`](../../config/schema.json)
and the version fixtures in [`../../test/test.sh`](../../test/test.sh), then
regenerates `catalog.json` from the seeds so the shipped file matches, and
re-derives [`../../manifest.json`](../../manifest.json) from the new bytes — it
mirrors this field as `format_version` and carries the catalog's sha256, so
leaving it behind would hand a consumer the previous release's checksum:

    ./scripts/release/bump-version.sh          # print the current version
    ./scripts/release/bump-version.sh 2        # set the format version to 2

One place is left to a person, because a format change is exactly when it needs
a second look: [`../../docs/FORMAT.md`](../../docs/FORMAT.md) shows the shape by
hand. Update that document when the JSON shape changes.

## `build-manifest.py`

`build-manifest.py` writes [`../../manifest.json`](../../manifest.json) — the
SHA-256, byte count, format version and totals an application reads **before** it
downloads the catalog. Everything comes from `catalog.json`'s bytes alone: no
clock, no git, so the same file always yields the same manifest.

    python3 scripts/release/build-manifest.py          # write manifest.json
    python3 scripts/release/build-manifest.py --check  # prove it is current

`--check` runs as step 3c of [`../../test/test.sh`](../../test/test.sh), before
the build, because the build re-stamps `generated` while the manifest records the
hash of the bytes as shipped.

## Publishing

Pushing a `v*` tag runs
[`.github/workflows/release.yml`](../../.github/workflows/release.yml): the
checks, the tagged bytes restored over the rebuild's re-stamped date, the
checksum rebuilt from the manifest, then a GitHub Release carrying `catalog.json`,
`manifest.json` and `catalog.json.sha256`. The file ships **plain** — no gzip.
The contract an integrating application reads is
[`../../docs/INTEGRATION.md`](../../docs/INTEGRATION.md).

Standard library only. See [`../README.md`](../README.md).
