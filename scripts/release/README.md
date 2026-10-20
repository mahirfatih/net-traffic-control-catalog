# scripts/release

Release chores for the catalog.

`bump-version.sh` bumps the catalog **format version** — the integer `version`
field in `catalog.json`. That field is the *format* version: it changes only
when the file's shape breaks compatibility (a field added, removed or renamed
that the app must handle). It is not a data version — the data changes on every
regenerate without touching it.

The canonical source is [`../catalog/generate.py`](../catalog/generate.py), which
writes the field, and [`../catalog/catalog-core.py`](../catalog/catalog-core.py),
which validates it. The script updates both, [`../../schema.json`](../../schema.json)
and the version fixtures in [`../../test/test.sh`](../../test/test.sh), then
regenerates `catalog.json` from the seeds so the shipped file matches:

    ./scripts/release/bump-version.sh          # print the current version
    ./scripts/release/bump-version.sh 2        # set the format version to 2

One place is left to a person, because a format change is exactly when it needs
a second look: [`../../docs/FORMAT.md`](../../docs/FORMAT.md) shows the shape by
hand. Update that document when the JSON shape changes.

Standard library only. See [`../README.md`](../README.md).
