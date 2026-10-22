# Maintaining — generating, adding, and removing

How `catalog.json` is built from `seeds/`, the four doors a change can come
through, and the discipline behind removing a host. This is the operator's
reference the README used to carry inline; the README keeps the overview and
points here.

## Generating

`seeds/` is the source of truth (see [`scripts/`](../../scripts/README.md));
`catalog.json` is the build output. Regenerate and validate:

```sh
python3 scripts/catalog/generate.py \
    --categories seeds/categories.json \
    --services   seeds/services.json \
    --out        catalog.json
python3 scripts/catalog/validate.py
```

Do not edit `catalog.json` by hand — edit `seeds/` instead.

To check the committed output is current without writing anything, use `--check`:
`generate.py --check` rebuilds from the seeds and compares with `catalog.json`,
and `build-catalog-docs.py --check` does the same for `docs/reference/CATALOG.md` and the
marked README blocks. Neither needs git; `./test/test.sh` runs both. `--check`
ignores the `generated` field on purpose: it is the date of the build, so it always
differs from a committed copy, while everything else must match exactly.

Run everything — registry, schema, build, validator, docs, licence gate — with:

```sh
./test/test.sh
```

Rules for a generator:

- **Output must use our vocabulary** (see [`FORMAT.md`](../reference/FORMAT.md)). An unknown
  category is not reported by the app — it is silently ignored, so `validate.py`
  fails the build instead.
- **`key` must stay stable.** The app may cache by it; changing a key re-labels data.
- **Deterministic output** (sorted keys) so diffs stay reviewable.
- **Only permitted sources**, enforced in code rather than by convention: every
  source lives in [`sources.json`](../../config/sources.json) with its licence, and
  [`scripts/sources/sources.py`](../../scripts/sources/sources.py) refuses a non-commercial or
  share-alike licence *before* fetching it. See
  [`SOURCES.md`](../reference/SOURCES.md) for the reasoning, and
  [`SECURITY.md`](../../SECURITY.md) for why it is a gate rather than a note.

### Harvesting from an external source

An external list can tell you that a host exists. It cannot tell you what the
host *is*, so it never assigns a category: `harvest.py` proposes hosts and
`rules.json` (or a person) labels them.

```sh
python3 scripts/sources/harvest.py
python3 scripts/sources/merge.py evidence/harvested-categories.json --dry-run
python3 scripts/sources/merge.py evidence/harvested-categories.json
```

For broad imports, run the durable source audits before committing:

```sh
python3 scripts/sources/audit-source-import.py
python3 scripts/sources/review-source-live.py --source adguard-https-exclusions-banks --only weak --limit 200
```

`audit-source-import.py` is offline and runs in the test suite. It catches known
false positives and redundant same-category rows, and warns when one source owns
more than 40% of a category. `review-source-live.py` uses DNS/HTTP and writes
evidence under `evidence/`; use it for spot-checking weak or new source rows.
Source-specific review policies live in `scripts/sources/source-policies.py`; add
new broad-source policies there, then move confirmed mistakes to `rules.json` →
`drop.hosts`. The source-and-category picture is written to
[`COVERAGE.md`](../reference/COVERAGE.md) by `scripts/catalog/build-coverage.py`.

### Adding a host by hand

For a few hosts, editing `seeds/categories.json` directly is the normal path.
Because that door records no author, date or reason on its own, a host you add
by hand also gets a line in [`seeds/hand-added.json`](../../seeds/hand-added.json):

```json
{ "example.com": { "by": "your-handle", "at": "2026-10-18", "reason": "why it belongs" } }
```

`by`, `at` and `reason` are all required, and the host must already be in
`seeds/categories.json` — this file records *who added it*, not a second list of
hosts. [`scripts/catalog/check-hand-added.py`](../../scripts/catalog/check-hand-added.py)
enforces it, and both the test suite and the freshness check run it. See
[`INGEST.md`](INGEST.md) for the three doors a host can enter through.

### Correcting one host by hand

A category that is wrong for a single host is a human decision, not a rule. Put
it in `rules.json` → `drop.override`, which **beats every rule and every source**:

```sh
python3 scripts/catalog/overrides.py set example.com shopping --reason "sells goods, not a bank"
python3 scripts/catalog/overrides.py list
python3 scripts/catalog/overrides.py remove example.com
python3 scripts/catalog/generate.py --categories seeds/categories.json --services seeds/services.json --out catalog.json
```

Precedence is fixed and enforced by code: **`override` > `rules` > harvested
source**. `generate.py` applies overrides last, `merge.py` never overwrites an
overridden host, and the audits treat an override as deliberate. Every override
needs a `reason`; `scripts/catalog/overrides.py check` (run by the test suite)
refuses one without it, one outside the vocabulary, or one that is also in
`drop.hosts`.

### Removing a host that no longer exists

A domain that stops resolving is not harmless dead weight: it can be bought by
somebody else and keep the category the previous owner had. Removing one is a
correctness fix. The hard part is that *unreachable* and *dead* look identical
from inside this network — a firewall that drops NXDOMAIN-only names, a captive
portal and a lapsed domain all answer the same way. Nearly all of the AdGuard
banks look unreachable from here, and 181 real banks were almost dropped on
that evidence.

So `scripts/catalog/probe-dead.py` asks the resolvers directly and reads the
response code they return, which settles it:

```sh
python3 scripts/catalog/probe-dead.py --self-test
python3 scripts/catalog/probe-dead.py --round 1     # ~11 minutes, 6,731 hosts
python3 scripts/catalog/probe-dead.py --round 2     # 10 minutes later, minimum enforced
python3 scripts/catalog/probe-dead.py --summary
```

Cloudflare, Google and AdGuard are each asked about A, AAAA and NS, so a host
has nine chances to prove it is alive and has to fail all nine to be called
dead — in **both** rounds. Round 2 refuses to run until the minimum gap has
passed, because a resolver outage is a snapshot the same way a dead name is.

The summary prints a **proposal**. It is not a deletion: applying it means adding
the host to `rules.json` → `drop.hosts` with a reason that cites the evidence.
Two verdicts are never proposed for removal, by design:

- **`nodata`** — `NOERROR` with no address record. The name exists; a mail-only
  domain looks exactly like this.
- **`servfail`** — every resolver says the zone is broken, which is two different
  failures wearing the same code: DNSSEC validation failing, or a delegation that
  never worked. The sweep asks once more with checking disabled to tell them
  apart, and reports both — but a broken zone is not proof of anything, so it is
  never proposed.

The script is deliberately absent from `test/test.sh`: it needs the network, and
CI must never depend on a network to tell a real bank it is dead. See
[`SOURCES.md`](../reference/SOURCES.md) for the full workflow, and [`SCHEDULE.md`](SCHEDULE.md)
for how often to run it.

The same probe runs without typing the commands by hand via a **manual GitHub
Actions workflow** (create `.github/workflows/sweep.yml` from the template in
`scripts/catalog/README.md` if you want to run sweeps via GitHub Actions) — it
probes both rounds ten minutes apart and files or updates one tracking issue
with the proposal. Start it from the Actions tab or with `gh workflow run sweeps`.
It runs by hand on purpose — a sweep is a decision, not a clock (see
[`SCHEDULE.md`](SCHEDULE.md)) — and it never edits catalog data.

### Removing a host that still resolves but serves nothing

DNS is not the whole story: a name can keep resolving after its site has gone.
`scripts/analysis/sweep-live.py` visits every host with a real browser
([agent-browser](https://github.com/vercel-labs/agent-browser) driving
[Lightpanda](https://lightpanda.io) with `--engine lightpanda`) and proposes the
hosts that answer with nothing — a parked page, an empty shell, a 404:

```sh
python3 scripts/analysis/sweep-live.py --self-test
python3 scripts/analysis/sweep-live.py --round 1 --aggressive
python3 scripts/analysis/sweep-live.py --round 2 --aggressive
python3 scripts/analysis/sweep-live.py --summary --aggressive   # proposal only
python3 scripts/analysis/sweep-live.py --apply --aggressive     # only after you read it
```

Two rounds must agree, the proposal is cross-checked against the DNS sweep above,
and a failure is only believed after a canary proves the browser still works —
because a long sweep is far more likely to lose its engine than to meet thousands
of dead hosts. A host that answered with a certificate failure or a timeout is
reported for review, never proposed: that says this network could not reach it,
not that the host is empty. By default only a **parked** host is proposed;
`--aggressive` widens that to hosts that answered with no page at all, which is
common on live infrastructure — so the proposal is meant to be read, not applied
blind. Infrastructure that answers with nothing on purpose (`adnxs.com`, an ad
network; `3dsecure.akbank.com.tr`, a bank's 3-D Secure endpoint) is kept on an
`INFRASTRUCTURE_ALLOWLIST` and is never proposed, even under `--aggressive`: a
real endpoint that serves no human-facing page is not a dead site. The script
needs the network and a
`lightpanda` binary, so it stays out of `test/test.sh`, like the DNS sweep.
Method and tools: [`scripts/analysis/`](../../scripts/analysis/README.md).

### Verifying a host is still the same owner

DNS and a browser can both say a name is "alive" while it has changed hands: a
lapsed domain is re-registered by someone else and inherits the previous owner's
category. `scripts/catalog/verify-registrations.py` checks the registration
itself:

1. **RDAP** for the domain (IANA bootstrap + verified cc supplement + convention
   probing).
2. **Port-43 WHOIS** fallback for registries with no RDAP (DENIC `.de`,
   TRABIS `.tr`, and anything IANA refers to).
3. **IP RDAP** for the host's address block (ARIN/RIPE/...), so the network
   owner is on record.
4. **traceroute** as a bounded reachability diagnostic (unprivileged on macOS).

```sh
python3 scripts/catalog/verify-registrations.py --self-test
python3 scripts/catalog/verify-registrations.py --round 1
python3 scripts/catalog/verify-registrations.py --round 2     # 10 minutes later
python3 scripts/catalog/verify-registrations.py --summary
```

The same discipline applies: a canary before the run, two rounds that must agree,
and a host is only proposed on a strong signal (`gone`, `expired`). Unknown and
unsupported TLDs are reported, never deleted. Reference data:
[`reference/rdap/`](../../reference/rdap/README.md). Method and tools:
[`scripts/catalog/`](../../scripts/catalog/README.md).

## Contributing

- Add entries by hand, or with a generator.
- Every entry should be **traceable to a source** — a wrong label is worse than no
  label, because it looks authoritative.
- Category names must be from the vocabulary; anything else is ignored by the app.
- Keep `services` at the **product** level (Facebook, Instagram, WhatsApp are
  separate), not the parent company.
- Keep the file sorted by host so diffs stay small.
- **Do not commit NonCommercial or share-alike data.** `NC` forbids use in a
  commercial app and `SA` would stop the derivative being CC0 — the two terms in
  `CC BY-NC-SA 4.0`. This is no longer a convention:
  [`sources.json`](../../config/sources.json) records the licence of every source and
  [`scripts/sources/sources.py`](../../scripts/sources/sources.py) refuses the blocked ones before
  fetching, and `./test/test.sh` fails if a record claims otherwise.

Full guide: [`CONTRIBUTING.md`](../../CONTRIBUTING.md).

## Versioning

- The app reads `version`; it accepts the versions it knows and ignores the rest.
- Unknown fields and unknown category names are ignored, never fatal.
- `version` is bumped only on a breaking format change. `scripts/release/bump-version.sh`
  does it: it updates the writer (`scripts/catalog/generate.py`), validator
  (`scripts/catalog/catalog-core.py`), schema (`schema.json`) and test contract,
  then regenerates `catalog.json` **and `manifest.json`** — the manifest mirrors
  the field as `format_version` and carries the catalog's sha256, so it is
  re-derived rather than edited. It rejects zero and backwards bumps.

### Cutting a release

The format and the data move separately: `version` only on a breaking shape
change, the data on every regenerate. A **tag** freezes both for a consumer that
must reproduce a state.

Releases are **manual** — nothing runs on a push or a tag. Start
[`.github/workflows/release.yml`](../../.github/workflows/release.yml) from the
Actions tab with the tag name you want and `publish` left false; it runs the
checks, restores the committed bytes over the rebuild's re-stamped `generated`
date, and prints the notes and assets it would attach. Set `publish` true to
create the tag and the GitHub Release carrying `catalog.json`, `manifest.json`
and `catalog.json.sha256`. The file ships plain — no gzip; the recipe is in
[`../release/README.md`](../release/README.md).

Regenerating `catalog.json` without `scripts/release/build-manifest.py` fails
`./test/test.sh` at **step 3c**: a manifest that no longer quotes the bytes it
sits next to is the one thing an integrating application is told to trust. The
contract those consumers read is [`INTEGRATION.md`](../reference/INTEGRATION.md).

> **Note:** The release workflow ([`.github/workflows/release.yml`](../../.github/workflows/release.yml))
> uses `format_version` (snake_case) in the generated notes, matching the
> `manifest.json` schema.
