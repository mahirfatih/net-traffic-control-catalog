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

`generate.py --check` asks the same question without git — it rebuilds from the
seeds and compares the result with the committed `catalog.json`, writing nothing
— and `build-catalog-docs.py --check` does it for `docs/CATALOG.md` and the
README blocks. `test/test.sh` runs both, at steps 3b and 7b.

A category name outside the vocabulary is **not** an error the app reports — it
is silently ignored on device. `validate.py` is what turns that into a build
failure.

### Correcting a host you are not adding

When one host is miscategorised but its neighbours are right, do not loosen the
rule — that would move its subdomains too. Record the decision where it will
outlive the next source refresh:

```sh
python3 scripts/catalog/overrides.py set example.com shopping --reason "sells goods"
./test/test.sh
```

Precedence is **`override` > `rules` > source**: `generate.py` applies
overrides last, and `merge.py` refuses to overwrite an overridden host. The
reason is mandatory — an override nobody can explain is indistinguishable from a
mistake, exactly like a `drop.hosts` entry.

## Removing a host

Two different removals, and they are not the same decision.

**It is in the catalog but wrong or worthless** — a confirmed non-finance
false positive, a throwaway host. Add it to `rules.json` → `drop.hosts` with a
reason, and remove it from `seeds/categories.json`. The `drop.hosts` entry is
what stops `harvest.py` importing it again.

**It no longer exists** — do not decide that by hand. From this network *dead*
and *unreachable* look identical, and 181 real banks were almost dropped on that
evidence:

```sh
python3 scripts/catalog/probe-dead.py --round 1     # ~11 minutes
python3 scripts/catalog/probe-dead.py --round 2     # 10 minutes later
python3 scripts/catalog/probe-dead.py --summary     # proposal only, changes nothing
python3 scripts/catalog/probe-dead.py --apply       # only after you read it
```

Read the proposal before applying it. A host is only proposed when all nine DNS
questions in **both** rounds answered `NXDOMAIN`; `nodata` and `servfail` are
reported but never proposed.

**It resolves but serves nothing** — a parked domain, a lapsed site, a host the
owner moved. DNS cannot see this, so visit it with a browser:

```sh
python3 scripts/analysis/sweep-live.py --self-test
python3 scripts/analysis/sweep-live.py --round 1 --aggressive
python3 scripts/analysis/sweep-live.py --round 2 --aggressive
python3 scripts/analysis/sweep-live.py --summary --aggressive   # proposal only
python3 scripts/analysis/sweep-live.py --apply --aggressive     # only after you read it
```

It visits every host with a real browser (agent-browser driving Lightpanda) and
proposes the ones that answer with nothing. Two rounds must agree. A host that
answered with a certificate failure, a timeout, or a resolver miss is printed
for review but **never** proposed — that says this network could not reach it,
not that it is empty. By default only a **parked** host is proposed;
`--aggressive` also adds hosts that answered with no page (an empty 200, a
404/5xx, a refusal), which are common on live infrastructure — `adnxs.com` and
`3dsecure.akbank.com.tr` both answer with nothing and both belong here — so read
the proposal before applying it.

**It resolves and serves a page, but may have changed hands** — a lapsed name
re-registered by someone else inherits the previous owner's category. Check the
registration itself:

```sh
python3 scripts/catalog/verify-registrations.py --self-test
python3 scripts/catalog/verify-registrations.py --round 1
python3 scripts/catalog/verify-registrations.py --round 2     # 10 minutes later
python3 scripts/catalog/verify-registrations.py --summary     # proposal only
python3 scripts/catalog/verify-registrations.py --apply       # only after you read it
```

It checks RDAP (IANA bootstrap + verified cc supplement + convention probing),
port-43 WHOIS (DENIC `.de`, TRABIS `.tr`, IANA referral), IP RDAP for the
address block, and bounded traceroute. A host is only proposed on a strong
signal (`gone`, `expired`); unknown and unsupported TLDs are reported, never
deleted.

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
the `--check` that the committed `catalog.json` and documents match what the
seeds build, the validator, the documentation freshness check, the catalog's own
quality guardrails (overlaps, category boundaries, source-import quality,
override validity, the dead-domain, live-sweep and registration decision
tables), and `python3 -m py_compile` over every script. All of it is Python 3
standard library — no dependencies, no install step.

If you changed a number that appears in a document, the freshness check will
say so.