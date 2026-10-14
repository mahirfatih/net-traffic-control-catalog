# scripts/catalog

Build and validate the catalog. `generate.py` writes `catalog.json` from the
`seeds/`, `validate.py` checks a `catalog.json` against the format and the
vocabulary, `build-catalog-docs.py` writes `docs/CATALOG.md`, `check-overlaps.py`
checks for category distribution and redundant domain overlaps,
`overrides.py` manages the per-host category overrides in `rules.json`, and
`probe-dead.py` finds catalog hosts that no longer resolve in DNS.
`catalog-core.py` is the shared load / normalise / validate / write logic the
others import by path (the hyphen in its name is legal on disk but not in an
`import` statement).

`probe-dead.py` is the only script here that uses the network, so it is the
only one absent from `test/test.sh`. It asks Cloudflare and Google directly
about A, AAAA and NS and reads the response code, because the system resolver
cannot tell a dead name from a name this network cannot reach. It needs two
rounds ten minutes apart before it calls a host dead.

Standard library only. See [`../README.md`](../README.md).
