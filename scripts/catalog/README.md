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
only one absent from `test/test.sh`. It asks Cloudflare, Google and AdGuard
directly about A, AAAA and NS and reads the response code, because the system
resolver cannot tell a dead name from a name this network cannot reach. AdGuard
is queried through its *unfiltered* endpoint on purpose: the default one answers
blocked ad and tracker names with `0.0.0.0`, and this catalog is largely those
names, so a filtering resolver would measure its own blocklist. It needs two
rounds ten minutes apart before it calls a host dead.

The sweep is a snapshot, so `check-docs-fresh.mjs` re-checks it against the
catalog on every run, offline: every seed host must appear in every complete
round (add a host and the evidence is stale by *data*, whatever the date says),
both rounds must have asked the same resolvers, no host both rounds call dead
may still be in the catalog, every host that left the seeds must have a
`drop.hosts` reason, and no reason may end in the `"; ?"` placeholder. That
last rule exists because a bug wrote `"; ?"` for all 432 hosts removed on
2026-10-14 — the category was deleted before the reason that cites it was built.

Rerun both rounds after any catalog growth; the checker will refuse the pair
until you do.

Standard library only. See [`../README.md`](../README.md).
