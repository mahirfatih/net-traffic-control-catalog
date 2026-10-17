# scripts

Tooling for this catalog. Python 3 standard library and Node — **no
dependencies, no install step** — for everything under `scripts/`, with one
exception: `scripts/analysis/` is a maintainer audit that needs `scikit-learn`
and `matplotlib`. It is not a check and `test/test.sh` does not run it. A data
repository's checks should be runnable by anybody who opened a pull request.

## Run everything

```sh
./test/test.sh
```

Registry → schema → build → validate → build fidelity → docs → licence gate →
category overlap → category boundaries → source import quality → overrides →
dead-domain decision table → live-sweep decision table → registration decision
table → compile. No network, no build system.

The scripts that *do* use the network — `review-source-live.py`,
`probe-dead.py`, `sweep-live.py` and `verify-registrations.py` — are deliberately
not here. Their decision tables are still checked offline, at steps 10.9, 10.10
and 10.11, because CI must never depend on a network to tell a real bank it is
dead.

## What each script does

### Catalog — [`catalog/`](catalog/)

| Script | What it does |
| :--- | :--- |
| [`generate.py`](catalog/generate.py) | Builds `catalog.json` from the `seeds/` files. Deterministic, and validates **before** writing — a bad seed writes nothing. Applies `rules.json` → `drop.override` last. `--check` rebuilds in memory and compares with the committed file (ignoring the `generated` date), writing nothing. |
| [`validate.py`](catalog/validate.py) | Checks a `catalog.json` against the format and the category vocabulary. Exits non-zero on any problem. |
| [`build-catalog-docs.py`](catalog/build-catalog-docs.py) | Generates `docs/CATALOG.md` and the marked README blocks from `catalog.json`, so the counts in the prose cannot drift from the shipped data. `--check` verifies they are current without writing. |
| [`overrides.py`](catalog/overrides.py) | Manages `rules.json` → `drop.override`, the per-host decision that beats every rule and every source. `set` / `remove` / `list` / `check`. A reason is mandatory. |
| [`check-overlaps.py`](catalog/check-overlaps.py) | Reports category distribution, deliberate subdomain overrides, and manual overrides. Fails if a subdomain carries the same category as an ancestor, which suffix matching already covers. |
| [`audit-category-consistency.py`](catalog/audit-category-consistency.py) | Category-boundary guardrails: names that must be a certain category, and labels that look wrong for a name. Treats an overridden host as decided. |
| [`probe-dead.py`](catalog/probe-dead.py) | Finds catalog hosts that no longer resolve, for the domain-recycling risk. **Uses the network — not in `test/test.sh`.** |
| [`verify-registrations.py`](catalog/verify-registrations.py) | Checks that a host is still registered to the same owner: RDAP (IANA bootstrap + verified cc supplement + convention probing), port-43 WHOIS fallback (DENIC `.de`, TRABIS `.tr`, IANA referral), IP RDAP for the address block, and bounded traceroute as a reachability diagnostic. **Uses the network — not in `test/test.sh`.** |
| [`catalog-core.py`](catalog/catalog-core.py) | Shared load / normalise / validate / write logic. Not run on its own. |

### Sources — [`sources/`](sources/)

| Script | What it does |
| :--- | :--- |
| [`sources.py`](sources/sources.py) | The source registry, and the licence gate. `python3 scripts/sources/sources.py` lists every source and its verdict; `--check` validates the registry; `--allowed` lists only what may be fetched. |
| [`harvest.py`](sources/harvest.py) | Fetches allowed sources, drops hosts the catalog already covers, applies `rules.json`, and reports what no rule matched. |
| [`merge.py`](sources/merge.py) | Applies harvested categories to `seeds/categories.json`. Refuses to overwrite an existing label, and never overwrites an overridden host. |
| [`harvest-public-institutions.py`](sources/harvest-public-institutions.py) | Fetches curated Turkish public-directory pages and merges closed-suffix hosts: `*.bel.tr` / `*.gov.tr` as `government`, `*.edu.tr` as `education`. Existing labels, explicit overrides and parked exclusions win. |
| [`source-policies.py`](sources/source-policies.py) | Per-source review policy: the expected category, weak-signal patterns, page signals, and known false positives. Not run on its own. |
| [`audit-source-import.py`](sources/audit-source-import.py) | Offline guardrail for broad imports: catches known false positives, same-category redundant rows, and warns on weakly evidenced rows. **In `test/test.sh`.** |
| [`review-source-live.py`](sources/review-source-live.py) | DNS/HTTP evidence for a broad import, using the policy above. Writes JSON and a Markdown triage table under `evidence/`. **Uses the network — not in `test/test.sh`.** |

### Checks — [`checks/`](checks/)

| Script | What it does |
| :--- | :--- |
| [`check-docs-fresh.mjs`](checks/check-docs-fresh.mjs) | Static drift check: broken links, renamed scripts, stale counts, unmeasured durations, a licence verdict that contradicts itself, a removed host that reappeared in the seeds. |

### Analysis — [`analysis/`](analysis/)

| Script | What it does |
| :--- | :--- |
| [`fetch-pages.py`](analysis/fetch-pages.py) | Audit: fetch each catalog host's homepage and cache its title/meta/headings/body under `analysis/.pages/` (gitignored). `--retry-empty` re-fetches hosts whose page came back empty, trying `www.` too; `--retry-thin 100` also re-fetches the ones under the audit's character floor. Standard library only. |
| [`build-matrix.py`](analysis/build-matrix.py) | Audit: classify the cached pages, cross-validate against the labels, and write the confusion matrix + report to [`docs/analysis/out/`](../docs/analysis/out/). `--min-class` keeps every category by default; the fold count drops to suit the smallest one. Needs `scikit-learn` and `matplotlib`. |
| [`classify-unmeasured.py`](analysis/classify-unmeasured.py) | Audit: explain *why* the hosts the matrix could not measure were unmeasurable — nothing answers, it answers with something that is not a page, or its HTML needs JavaScript. Writes `evidence/unmeasured-hosts.json`. Standard library only, network required. |
| [`sweep-live.py`](analysis/sweep-live.py) | Visits every catalog host with a real browser — [agent-browser](https://github.com/vercel-labs/agent-browser) driving [Lightpanda](https://lightpanda.io) (`--engine lightpanda`) — and records what it served. Finds the "empty" hosts: a name that still resolves but no longer serves a page (parked, an empty shell, a 404). Two rounds must agree before anything is proposed, and a failure is only believed after a canary proves the engine still works. By default it proposes only a parked host; `--aggressive` widens it to hosts that answered with nothing. Writes `evidence/live-sweep.json` / `.md`. **Uses the network — not in `test/test.sh`.** |

## Harvest workflow

```sh
python3 scripts/sources/harvest.py                    # fetch, filter, apply rules
python3 scripts/sources/merge.py evidence/harvested-categories.json --dry-run
python3 scripts/sources/merge.py evidence/harvested-categories.json
python3 scripts/catalog/build-catalog-docs.py         # refresh docs/CATALOG.md
./test/test.sh
```

`harvest.py` writes `evidence/harvested-categories.json`, which is gitignored: it is an
intermediate, and the seeds are the source of truth.

Public-institution directories are a narrower, curated path:

```sh
python3 scripts/sources/harvest-public-institutions.py --check # report only
python3 scripts/sources/harvest-public-institutions.py --write # merge into seeds/categories.json
python3 scripts/catalog/generate.py --categories seeds/categories.json --services seeds/services.json --out catalog.json
python3 scripts/catalog/build-catalog-docs.py
./test/test.sh
```

That script only trusts closed Turkish public suffixes. It never overwrites a
seeded label, preserves explicit overrides such as `saglik.gov.tr` → `health`,
and skips parked names that the iOS catalog builder rejects via `excluded.csv`.

### What the harvest will not do

- **Invent a category.** No rule, no label — the host goes to
  `docs/NEEDS-REVIEW.md`.
- **Write `other` automatically.** `other` means a person looked and did not
  know, so only a rule may produce it.
- **Overwrite a label.** Conflicts are printed; the seed wins.
- **Overwrite an override.** A host in `drop.override` is a decision somebody
  wrote down; a source has no standing against it.
- **Drop a line it does not parse.** Unparsable lines are reported, because a
  parser that skips silently is how a catalog goes quietly wrong.

## Correcting one host

A category that is wrong for a single host, and right for its neighbours, is a
person's decision rather than a rule. Loosening the rule would move its
subdomains too, so it goes in `rules.json` → `drop.override`:

```sh
python3 scripts/catalog/overrides.py set example.com shopping --reason "sells goods"
python3 scripts/catalog/overrides.py list
python3 scripts/catalog/overrides.py remove example.com
```

Precedence is fixed: **`override` > `rules` > harvested source**. `check` runs
in `test/test.sh` and refuses an override with no reason, one outside the
vocabulary, or one that is also in `drop.hosts`.

## Removing a host that no longer exists

A lapsed domain can be bought by somebody else and keep the previous owner's
category, so removing one is a correctness fix. But this network cannot tell
*dead* from *unreachable* — nearly all of the AdGuard banks are unreachable
from here, and 181 real banks were almost dropped on that evidence.

`probe-dead.py` asks Cloudflare, Google and AdGuard directly and reads the
response code
(`0` NOERROR, `3` NXDOMAIN), about A, AAAA and NS, twice, ten minutes apart:

```sh
python3 scripts/catalog/probe-dead.py --self-test
python3 scripts/catalog/probe-dead.py --round 1     # ~11 minutes
python3 scripts/catalog/probe-dead.py --round 2     # 10 minutes later, minimum enforced
python3 scripts/catalog/probe-dead.py --summary     # prints the proposal, changes nothing
python3 scripts/catalog/probe-dead.py --apply       # remove it from the seeds, record it
```

`--summary` and a bare run are a preview. Only `--apply` writes: the host leaves
`seeds/categories.json` (so `generate.py` stops emitting it) and lands in
`rules.json` → `drop.hosts` with the evidence that removed it, which stops
`harvest.py` importing it again. `nodata` and `servfail` are reported but never
proposed for removal.

## Removing a host that serves nothing

A name can keep resolving and stop serving a page — a lapsed site, a parked
domain, a host the owner moved. `probe-dead.py` cannot see that: the name
exists, so DNS is happy. `sweep-live.py` visits every host with a real browser —
[agent-browser](https://github.com/vercel-labs/agent-browser) driving
[Lightpanda](https://lightpanda.io) (`--engine lightpanda`) — so it sees what a
browser sees, and proposes the ones that answer with nothing:

```sh
python3 scripts/analysis/sweep-live.py --self-test
python3 scripts/analysis/sweep-live.py --round 1 --aggressive
python3 scripts/analysis/sweep-live.py --round 2 --aggressive
python3 scripts/analysis/sweep-live.py --summary --aggressive   # proposal only
python3 scripts/analysis/sweep-live.py --apply --aggressive     # only after you read it
```

Two rounds must agree, and the proposal cross-checks
`evidence/dead-domain-sweep.json`, so a host that served a page in either round
is never proposed. Four verdicts stay out of the proposal on purpose: `ok` and
`blocked` (a live site behind Cloudflare is not empty), and `tls-error` /
`timeout` / `dns-error`, which say *this network could not reach it*, not that
it serves nothing — `youtube-nocookie.com` and `jsdelivr.net` land there on a
bad afternoon. Those are printed for a person to read; `--include-flaky`
proposes them too, but only after you have read them.

By default only a **parked** host is proposed — a page that says the domain is
for sale is the one signal that cannot be misread. `--aggressive` widens it to
hosts that answered with no page (an empty 200, a 404/5xx, a refusal), and those
are common on live infrastructure: `adnxs.com` and `3dsecure.akbank.com.tr` both
answer with nothing and both belong here. So `--aggressive` is read, not applied
blind.

## Verifying a host is still the same owner

DNS and a browser can both say a name is "alive" while it has changed hands: a
lapsed domain is re-registered by someone else and inherits the previous owner's
category. `verify-registrations.py` checks the registration itself:

1. **RDAP** for the domain (IANA bootstrap + verified cc supplement + convention
   probing), with the same three-layer resolution and redirect-following as the
   iOS client it is ported from.
2. **Port-43 WHOIS** fallback for registries with no RDAP — DENIC `.de`
   (`Status: free` / `connect`), TRABIS `.tr` (`Domain Status`), and anything
   IANA refers to.
3. **IP RDAP** for the host's address block (ARIN/RIPE/...), longest-prefix
   match, so the network owner is on record.
4. **traceroute** as a bounded reachability diagnostic (unprivileged on macOS).

Reference data lives in [`../reference/rdap/`](../reference/rdap/). The same
discipline as the sweeps applies: a canary before the run (retried once, so a
transient blip does not void a round), two rounds that must agree, and a host is
only proposed on a *strong* signal (`gone`, `expired`). Unknown and unsupported
TLDs are reported, never deleted.

Three guards keep a `404` or a status from over-reading as "gone" — a non-RDAP
`404` (the `.ms` registry answers its own name with an HTML error page), an
`inactive`/`clientHold` status (registered but not delegated), and a host that
still resolves in DNS. See
[`catalog/README.md`](catalog/README.md#what-each-verdict-means).

```sh
python3 scripts/catalog/verify-registrations.py --self-test
python3 scripts/catalog/verify-registrations.py --round 1
python3 scripts/catalog/verify-registrations.py --round 2     # 10 minutes later
python3 scripts/catalog/verify-registrations.py --summary
python3 scripts/catalog/verify-registrations.py --apply       # only after reading it
```

## Catalog reliability analysis

```sh
cd scripts/analysis
python3 -m venv .venv && .venv/bin/pip install scikit-learn matplotlib
.venv/bin/python fetch-pages.py                 # cache each host's homepage (~16 min)
.venv/bin/python fetch-pages.py --retry-empty   # re-fetch the ones that came back empty
.venv/bin/python fetch-pages.py --retry-thin 100  # and the ones under the audit's floor
.venv/bin/python build-matrix.py                # ← writes docs/analysis/out/
python3 classify-unmeasured.py                  # say why the rest were unmeasurable
```

It fetches each host's homepage, extracts the title, meta description/keywords,
headings and body, trains a TF-IDF + LinearSVC classifier on the labels and
cross-validates it — so the confusion matrix, per-class
precision/recall/F1, chi-squared correlated terms and high-confidence errors
land in [`docs/analysis/out/`](../docs/analysis/out/) next to the data they
judge. It measures **self-consistency** (how predictable a label is from its
page), not correctness. It needs `scikit-learn` and `matplotlib` and is **not**
run by `test/test.sh`.

## Fetching

`harvest.py` caches every response in `evidence/`, so `--offline` re-runs the
whole pipeline with no network and produces the same result. Use it to check a
change to `rules.json` without re-downloading.

## Adding a source

See [`../docs/SOURCES.md`](../docs/SOURCES.md). Append to `sources.json`, then
run `python3 scripts/sources/sources.py --check`.

A blocking licence (`NC`, `SA`) with `allowed: true` is a hard error. That is
deliberate: this data is CC0 and ships inside a commercial app.
