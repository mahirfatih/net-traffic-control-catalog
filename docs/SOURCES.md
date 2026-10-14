# Sources

Every external list this repository has ever drawn on, and the verdict on each.
The machine-readable version is [`../sources.json`](../sources.json); this file
is where the reasoning lives, so a refusal is never a mystery.

## The rule this repository runs on

> No source assigns a category.

An external list can tell you that `plex.tv` exists. It cannot tell you that
Plex is a media server, and a list that claimed to would be wrong often enough
to be useless. So a host's category is always either **a rule in
[`rules.json`](../rules.json)** or **a person who wrote down why**. Harvesting
only ever *proposes hosts*; `merge.py` refuses to overwrite a label somebody
already decided, and refuses any category outside the vocabulary.

## Allowed

| Source | Licence | Why |
| :--- | :--- | :--- |
| `anudeepnd-whitelist` | MIT | 186 hosts that overzealous blocklists catch. A good source for **finding gaps** in a catalog. |
| `anudeepnd-optional` | MIT | 136 hosts after comments. Same maintainer, same purpose. |
| `anudeepnd-referral` | MIT | 50 hosts. Affiliate and referral endpoints, which is most of what a blocklist misfires on. |
| `hotcakex-microsoft-domains` | MIT | Root Microsoft-owned domains. Used as a vendor/service discovery list only; rules split them across `software`, `search`, `gaming`, `social`, `email`, `ads`, `analytics`, `cdn`, `ai`, etc. |
| `hotcakex-microsoft-easm` | MIT | External attack surface inventory. Only exact-root brand/product matches (Activision-Blizzard-King, ZeniMax/Bethesda, GitHub/npm families) enter rules; the remaining ~2,600 defensive TLD variants stay in review evidence. |
| `omaskery-proxy-exceptions` | MIT | Developer-tool proxy exception YAML. Useful for package registries, IDE/update endpoints and other `software` gaps. |
| `goodnessjson-whitelist` | MIT | Community Pi-hole allowlist forked from anudeepND. Mostly overlap; retained as a delta source. |
| `goodnessjson-optional` | MIT | Optional GoodnessJSON entries. Mostly overlap; retained as a delta source. |
| `goodnessjson-referral` | MIT | GoodnessJSON referral/affiliate entries. Mostly overlap; retained as a delta source. |
| `ultimate-hosts-whitelist` | MIT | Mixed-syntax whitelist. The parser ignores `ALL`, `REG`, `RZD`, IPs, local names and sample domains; only rule-matched hosts may enter the catalog. |
| `keloran-pihole-whitelist` | MIT | Small Pi-hole whitelist in the anudeepND style. It currently contributes no new categories: almost all hosts are already covered, with one review item retained for evidence. |
| `itsmingjie-inflight-allowlist` | MIT | Conservative in-flight Wi-Fi captive portal and provider domains. Mostly `travel`; provider roots like `viasat.com` are also `travel` in this context. |
| `jayconius-gaming-whitelist` | MIT (README badge; LICENSE file missing) | Gaming platform whitelist. Contributes new roots for EA, Epic, GOG, Paradox, Unity, 2K; most subdomains are already covered by existing rules. |
| `adguard-https-exclusions-banks` | NOASSERTION (no LICENSE file) | AdGuard HTTPS exclusions for banks and financial services. Used as a finance discovery source; IP rows are ignored, `www.` aliases are normalized, and redundant same-category subdomains are skipped. |

Large imports are guarded by `scripts/sources/audit-source-import.py`, which checks
source-specific false positives, same-category redundant subdomains, and review
signals for weakly evidenced rows.

For a new broad source, use this workflow instead of hand-checking every row:

1. Add the source and conservative rules.
2. Harvest and merge with `--dry-run` first.
3. Add a source policy in `scripts/sources/source-policies.py`.
4. Run `python3 scripts/sources/audit-source-import.py` for offline guardrails.
5. Run `python3 scripts/sources/review-source-live.py --source <id> --only weak`
   for DNS/HTTP evidence. The live review writes JSON and Markdown under
   `evidence/` and never edits catalog data.
6. Move confirmed mistakes to `rules.json` → `drop.hosts`, regenerate, and rerun
   the checks.

## Correcting a single host

When a category is wrong for one host and right for its neighbours, do not
loosen the rule and do not edit the generated `catalog.json`. Record the
decision in `rules.json` → `drop.override`:

```json
"override": {
  "example.com": { "category": "shopping", "reason": "sells goods, not a bank" }
}
```

The precedence is fixed: **`override` > `rules` > harvested source**.
`generate.py` applies overrides after the rules, `merge.py` refuses to overwrite
an overridden host, and the audits count an override as deliberate. A `reason`
is mandatory — an override nobody can explain is indistinguishable from a
mistake, the same rule `drop.hosts` follows.

**On the anudeepND lists.** They are called *allowlists*, and this repository
has no allowlist concept — the app decides a domain is allowed when no
enabled list contains it. The lists are used for the opposite of what their name
suggests: they name hosts that are real, widely used, and easily caught by a
rule meant for something else. That makes them a supply of *catalog gaps*, which
is what `harvest.py` uses them for.

**On the Microsoft list.** Ownership is not a category. The HotCakeX list is a
source of names, not labels: `bing.com` is `search`, `xbox.com` is `gaming`,
`linkedin.com` is `social`, `clarity.ms` is `analytics`, `msads.net` is `ads`,
and broad platform names stay `software`. Anything not covered by an explicit
rule remains in `docs/NEEDS-REVIEW.md`.

## Removing a host that no longer exists

A domain that stops resolving is not harmless dead weight. It can be bought by
somebody else and it would keep the category the previous owner had, so a user
who allows `finance` would be allowing whoever holds that name now. Removing one
is a correctness fix.

The catch is that this network cannot tell *dead* from *unreachable*: a firewall
that drops NXDOMAIN-only names, a captive portal and a dead domain all look the
same from inside a process. Nearly all of the AdGuard banks look unreachable
from here, and 181 real banks were almost dropped on that evidence. So
`scripts/catalog/probe-dead.py` asks the resolvers directly and reads the
response code they return:

    0  NOERROR   the name exists
    3  NXDOMAIN  the name does not exist

It asks Cloudflare and Google about A, AAAA and NS, so a host has six chances
to prove it is alive and has to fail all six to be called dead. Then it has to
do it twice — `--round 2` refuses to run until `--min-gap-minutes` has passed,
because a resolver outage is a snapshot the same way a dead name is.

```sh
python3 scripts/catalog/probe-dead.py --self-test
python3 scripts/catalog/probe-dead.py --round 1      # ~10 minutes
python3 scripts/catalog/probe-dead.py --round 2      # 10 minutes later
python3 scripts/catalog/probe-dead.py --summary
```

Evidence lands in `evidence/dead-domain-sweep.json` and
`evidence/dead-domain-sweep.md`. The summary prints a **proposal**: the hosts
both rounds independently called dead. It is a proposal, not a deletion. Applying
it means adding the host to `rules.json` → `drop.hosts` with a reason that cites
this evidence, then regenerating:

```json
"24banking.md": "NXDOMAIN from cloudflare+google on 2026-10-14 and 2026-10-15"
```

Two verdicts are deliberately never proposed for removal:

- **`nodata`** — the name answers `NOERROR` with no address record. It exists;
  it just has no A record, which is what a mail-only domain looks like.
- **`servfail`** — every resolver says the zone is broken. That is usually a
  name whose registration lapsed, so it is worth a person's attention, but a
  broken zone is not proof of anything. It is reported under "Worth a look".

The script is deliberately absent from `test/test.sh`. It needs the network, and
CI must never depend on a network to tell a real bank it is dead.

## Blocked

Nothing is listed here, and that is deliberate. A refusal nobody can rediscover
becomes a rule people work around, so the refusal has to outlive the source
name — which means it lives in a **table keyed on the licence**, not on a list
of sources:

| Licence | Verdict |
| :--- | :--- |
| CC0 / public domain, MIT, BSD, Apache-2.0, ISC | allowed |
| CC BY (no NC, no SA) | allowed |
| CC BY-**NC**-*, CC BY-NC-SA-* | **blocked** — commercial use forbidden |
| CC BY-*-**SA** | **blocked** — the derivative inherits the term and stops being CC0 |
| proprietary API whose terms forbid it | **blocked**, whatever its data licence says |

So the next DuckDuckGo Tracker Radar — or any other `NC` list — is refused by
name appearing nowhere in this repository.
[`../scripts/sources/sources.py`](../scripts/sources/sources.py) is where that table lives, and
`harvest.py` applies it before a byte is fetched.

If you hold an agreement that permits a use the free tier does not, record it
in `sources.json` with a `reason` that says so. Do not edit the gate.

## Adding a source

1. Append a record to `sources.json` with `id`, `name`, `url`, `license`,
   `allowed` and, if not allowed, a `reason`.
2. Run `python3 scripts/sources/sources.py --check`. A blocking licence with
   `allowed: true` is an **error**, not a warning — that is the mistake this
   registry exists to catch.
3. If it is a list rather than a categoriser, add a note in `rules.json` saying
   which hosts it contributes, and be explicit about parked or throwaway
   domains so `harvest.py` can drop them with a reason instead of guessing.
4. Open a pull request. The gate runs there too.

## Turkish public directories

Some sources are not broad blocklists; they are curated public directories whose
hosts are already scoped by closed Turkish public suffixes. Use
[`../scripts/sources/harvest-public-institutions.py`](../scripts/sources/harvest-public-institutions.py)
for those pages:

```sh
python3 scripts/sources/harvest-public-institutions.py --check
python3 scripts/sources/harvest-public-institutions.py --write
```

The harvester reads the Turkey Municipalities Union, e-Şehir, AG Çevre, CCIFT and
YÖK pages that have already fed this catalog. It accepts only:

- `*.bel.tr` and `*.gov.tr` as `government`
- `*.edu.tr` as `education`

It does **not** overwrite existing labels. Explicit human overrides such as
`saglik.gov.tr` → `health`, `tcmb.gov.tr` → `finance`, `tdk.gov.tr` →
`encyclopedia`, and `meb.gov.tr` / `osym.gov.tr` → `education` win over the
suffix. Parked names listed in the iOS `ReferenceData/excluded.csv` are skipped,
because the app's bundle generator rejects them even though suffix rules can
still classify them at runtime.

### Licence verdicts

| Licence | Verdict |
| :--- | :--- |
| CC0 / public domain | allowed |
| MIT, BSD, Apache-2.0, ISC | allowed |
| CC BY (no NC, no SA) | allowed |
| CC BY-**NC**-*, CC BY-NC-SA-* | **blocked** — commercial use forbidden |
| CC BY-*-**SA** | **blocked** — the derivative inherits the share-alike term and stops being CC0 |
| proprietary API | blocked unless the registry record says otherwise, in writing |

The table in `scripts/sources/sources.py` is the enforcement point; this table is the
explanation of it. If the two disagree, the code is right and this file is stale.
The suite checks the codes it can check, so a licence in the table but not in the
code is not caught by a test — it is caught by the next source that tries it.

## What a source is not allowed to do

- **Invent a category.** `harvest.py` has no path that assigns one.
- **Overwrite a label.** A disagreement is printed and the seed is kept.
- **Add `other` by default.** `other` means "a person looked and did not know",
  so only a rule may produce it. Hosts with no rule go to
  [`NEEDS-REVIEW.md`](NEEDS-REVIEW.md) instead.
- **Silently lose hosts.** A line the parser does not understand is reported,
  not dropped.
