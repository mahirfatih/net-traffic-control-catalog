# scripts/catalog

Build and validate the catalog. `generate.py` writes `catalog.json` from the
`seeds/`, `validate.py` checks a `catalog.json` against the format and the
vocabulary, `build-catalog-docs.py` writes `docs/CATALOG.md` and the generated
blocks in `README.md` and its translation `README.tr.md`, `check-overlaps.py`
checks for category distribution and redundant domain overlaps,
`overrides.py` manages the per-host category overrides in `rules.json`,
`probe-dead.py` finds catalog hosts that no longer resolve in DNS, and
`verify-registrations.py` checks that a host is still registered to the same
owner (RDAP, port-43 WHOIS, IP RDAP, traceroute).
`catalog-core.py` is the shared load / normalise / validate / write logic the
others import by path (the hyphen in its name is legal on disk but not in an
`import` statement).

Both writers take `--check`: `generate.py --check` rebuilds from the seeds and
compares the result with the committed `catalog.json`, and
`build-catalog-docs.py --check` does the same for `docs/CATALOG.md` and the
README blocks in both languages. They write nothing, so "is the committed
artifact current?" is answerable without touching it — and without git, which is
what lets `test/test.sh` prove it in a plain checkout.

`README.md` is the source of truth and `README.tr.md` is its Turkish
translation. `build-catalog-docs.py` writes the *same* block content to both, and
`check-docs-fresh.mjs` compares them (`checkTurkishMirror`), so a hand-edit that
changes one language's blocks and not the other's fails the build rather than
shipping two documents that disagree about the catalog.

Every removed host is recorded in `rules.json → drop.hosts` with the reason and
the category it used to carry. That map *is* the ledger; there is deliberately no
second copy to drift from it. `check-docs-fresh.mjs` keeps it honest in both
directions: a host that left the seeds must have a `drop.hosts` entry, and a host
in `drop.hosts` must not also be back in `seeds/categories.json` — that would be
a removal silently undoing itself, and `generate.py` would drop it again without
saying so.

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

## Verifying a host is still the same owner

DNS being alive is not enough: a lapsed name can be re-registered by someone
else and inherit the previous owner's category. `verify-registrations.py` checks
the registration itself, four ways:

1. **RDAP** (RFC 7480-7484) for the domain, via the IANA bootstrap registry
   (RFC 9224), a bundled verified supplement for country-code registries IANA
   omits, and convention probing as a last resort.
2. **Port-43 WHOIS** fallback for registries with no RDAP (DENIC for `.de`,
   TRABIS for `.tr`, and anything IANA refers to).
3. **IP RDAP** for the host's address block (ARIN/RIPE/...), so the network
   owner is on record alongside the name owner.
4. **traceroute** as a reachability diagnostic (bounded, opt-in).

Reference data lives in [`../../reference/rdap/`](../../reference/rdap/) and is
copied from the iOS project's `ReferenceData/RDAP/`. Regenerating it is a
deliberate, reviewed step, not a build-time fetch.

The same discipline as the dead-domain sweep applies: a canary before the run,
two rounds that must agree, and a host is only proposed when every round agrees.
A host is never proposed on a single ambiguous signal (an unknown or
unsupported TLD is reported, not deleted).

### What each verdict means

| verdict | meaning | proposed for removal? |
|---|---|---|
| `gone` | the name is being released — a genuine RDAP "not found", `pendingDelete`, or `redemptionPeriod` | yes |
| `expired` | the registration's expiry date is in the past | yes |
| `review` | registered, but not working, or re-registered recently (`inactive`, `clientHold`, a fresh creation date) | only with `--aggressive` |
| `registered` | a live registration | no |
| `unsupported` | the TLD has no RDAP and no WHOIS this tool can read (`.tr` on policy grounds) | no |
| `unknown` | every source failed or disagreed | no |

Three guards keep the verdicts honest — each one was added after a real
false positive:

- **A `404` only counts as "not registered" when the endpoint actually speaks
  RDAP.** RDAP servers answer a missing name with an `application/rdap+json`
  body (Verisign sends an empty one with that type). Some country registries
  instead run an ordinary web server that returns an HTML error page for *every*
  lookup — `rdap.nic.ms` answers its own `nic.ms` with a Tomcat 404 — which read
  as "available" and would have deleted six live Microsoft `.ms` hosts
  (`aka.ms`, `jwt.ms`, …). A non-RDAP 404 now falls through to WHOIS and then to
  `unknown`, never to `gone`.
- **`inactive` and `clientHold` mean "registered but not delegated", not
  "gone".** They are a `review`, not a removal: the name is still held by its
  owner, it just is not serving. `investbank.com.ua` carries `inactive` and would
  otherwise have been dropped.
- **A name that still resolves in DNS is never `gone`.** If `getaddrinfo`
  answers, the name is in use, whatever a registry status or a half-working
  endpoint suggests.

Standard library only. See [`../README.md`](../README.md).
