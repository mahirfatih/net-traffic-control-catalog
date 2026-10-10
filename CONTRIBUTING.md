# Contributing

The catalog is a data file. Everything here follows from one consequence: **a
wrong label is worse than no label**, because it looks authoritative and
nobody can tell it was never checked.

## Adding a host

```sh
# 1. hand-edit the seed — this is the normal path for a few hosts
$EDITOR seeds/categories.json

# 2. regenerate and check
./test/test.sh
```

`catalog.json` is build output. Never edit it by hand; the next `generate.py`
run overwrites the edit.

A category name outside the vocabulary is **not** an error the app reports — it
is silently ignored on device. `validate.py` is what turns that into a build
failure.

## Bulk work: harvest

For finding hosts that are missing rather than guessing them:

```sh
python3 scripts/sources/harvest.py                 # fetch allowed sources, apply rules
python3 scripts/sources/merge.py evidence/harvested-categories.json --dry-run
python3 scripts/sources/merge.py evidence/harvested-categories.json
```

The pipeline is fetch → parse → drop what the catalog already covers → apply
`rules.json` → report what is left. Read
[`docs/SOURCES.md`](docs/SOURCES.md) before adding a source.

What `harvest.py` will not do, on purpose:

- **Invent a category.** No rule, no label. The host goes to
  [`docs/NEEDS-REVIEW.md`](docs/NEEDS-REVIEW.md) instead.
- **Write `other` by default.** `other` means a person looked and did not know.
- **Overwrite an existing label.** A conflict is printed and the seed wins.
- **Drop a line it does not understand.** A parser that skips silently is how
  a catalog goes quietly wrong.

## Rules

`rules.json` holds one entry per group of related hosts:

```json
{ "match": ["plex.tv", "plexapp.com"], "category": "software", "note": "why" }
```

- `match` entries are matched whole **and by subdomain**, so `plex.tv` already
  covers `proxy.plex.tv` — do not add both.
- `note` is required in practice. It is the answer to "why does this say
  `video`?", asked later by somebody who does not remember deciding it.
- First match wins, so put specific rules above general ones.

## Adding a source

See [`docs/SOURCES.md`](docs/SOURCES.md). In short: append to `sources.json`
with a licence and an `allowed` verdict, then run `python3 scripts/sources/sources.py
--check`.

A blocking licence (`NC`, `SA`) with `allowed: true` is a hard error. That is
the point of the file: this catalog is CC0 and ships inside a commercial app,
and the registry is what keeps it that way.

## Services

One entry per **product**, not per company. Facebook, Instagram, WhatsApp and
Threads are separate because a DNS filter sees domains, not apps, and a product
is what a person recognises.

`services[].key` **must stay stable** — the app may cache by it, so renaming
one re-labels data on somebody's device.

## Before you open a pull request

```sh
./test/test.sh
```

which runs, in order: the source registry check, the schema check, the build,
the validator, the documentation freshness check, and `python3 -m py_compile`
over every script. All of it is Python 3 standard library — no dependencies, no
install step.

If you changed a number that appears in a document, the freshness check will
say so.