# scripts/catalog

Build and validate the catalog. `generate.py` writes `catalog.json` from the
`seeds/`, `validate.py` checks a `catalog.json` against the format and the
vocabulary, `build-catalog-docs.py` writes `docs/CATALOG.md`, and
`catalog-core.py` is the shared load / normalise / validate / write logic the
other three import by path (the hyphen in its name is legal on disk but not in
an `import` statement).

Standard library only. See [`../README.md`](../README.md).
