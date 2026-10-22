# `docs/reference/` — what is in it right now

The shape of the data and the current contents. Two files are **generated** —
regenerate them, never edit them by hand.

- [`CATALOG.md`](CATALOG.md) — every host by category, and the service table. **Generated** by `scripts/catalog/build-catalog-docs.py`.
- [`COVERAGE.md`](COVERAGE.md) — how much is measured, and from where. **Generated** by `scripts/catalog/build-coverage.py`.
- [`FORMAT.md`](FORMAT.md) — the schema, matching rules and vocabulary the app reads.
- [`INTEGRATION.md`](INTEGRATION.md) — reading the file from another application.
- [`IPADDRESS.md`](IPADDRESS.md) — why an address is never a host.
- [`SOURCES.md`](SOURCES.md) — why each source is allowed or refused.

## `CATALOG.md` — what is in the data

Counts per category, the `other` list, the service table. Generated from
`catalog.json` because a hand-written copy of a data file is a second copy to
keep in step, and the first harvest would have made it quietly wrong.

```sh
python3 scripts/catalog/build-catalog-docs.py
```

`./test/test.sh` regenerates it and fails if it differs, so a hand edit is caught
rather than tolerated.

## `COVERAGE.md` — how much is measured, and from where

The other half of [`CATALOG.md`](CATALOG.md): the size of each category is one
question, how much of each one the analysis could actually read — and which
single source is carrying it — is another. Generated from the catalog, the rules,
the harvest summary and the analysis output.

```sh
python3 scripts/catalog/build-coverage.py
```

It is where the catalog's central fact is stated plainly: `finance` is over half
the rows, and 98% of it comes from one bank list. Both are warnings to a reader,
not bugs — which is exactly why they belong in a generated file that cannot
quietly fall out of step.

## `FORMAT.md` — the file the app reads

The schema, the matching rules (longest suffix, public-suffix refusal, ties), the
category vocabulary, the service shape, the precedence order and the raw URL.
Reference material, split out of the README when it grew past an overview.

## `INTEGRATION.md` — reading the file from another application

The distribution contract for anything that is not the iOS app: the pinned tag
URL beside the moving `main` one, the kilobyte `manifest.json` that says whether
the catalog changed before the whole file is pulled, the SHA-256 check, and the
line between what is guaranteed (`version`, `services[].key`) and what moves on
every regenerate (counts, the date). The file ships plain — no gzip.

## `IPADDRESS.md` — why an address is never a host

A bare IP is not a name, and a catalog keyed on names cannot hold one. The page
records why the distinction is load-bearing — an address changes owner silently
and a name does not — so the rule is not rediscovered as a bug.

## `SOURCES.md` — why each source is allowed or refused

Every external list, its licence, and the verdict on it. The machine-readable
version is [`../../config/sources.json`](../../config/sources.json).

It exists because a refusal nobody can rediscover becomes a rule people work
around — so the refusal is a table keyed on the **licence**, not a list of
source names. The next `NC` list is refused without anybody having to add it to a
list first.
