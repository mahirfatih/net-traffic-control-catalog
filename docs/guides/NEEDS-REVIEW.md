# Needs review

A source host that **no rule in `rules.json` matched**, is not in
`seeds/categories.json`, and is not in `catalog.json`. A host with no category is
an open question; putting it in `catalog.json` as `other` would convert the
question into a claim, and `other` on screen looks like an answer.

This file is the *investigated* half of that state — the hosts a person actually
looked at, with what was tried and why the question is still open. The full,
un-investigated backlog is machine-recorded in
[`../evidence/pending-source-hosts.json`](../../evidence/pending-source-hosts.json),
so the number of open questions is on the record instead of only in a run's
scrollback.

## How a host gets out of here

Either add a rule to `rules.json` (right category, and a `note` saying why), or
add it to that file's `drop.hosts` map with a reason. Both are reviewed like
anything else.

A host dropped without a reason is indistinguishable from a host somebody
forgot, so `rules.json` asks for one.

## Backlog

`harvest.py` prints the unmatched hosts as it runs, but until now only that
scrollback held them: a source that contributed nothing *this* run left the
thousands it offered with no record at all. That made the catalog look as if
every candidate had been either imported or dismissed.

[`../evidence/pending-source-hosts.json`](../../evidence/pending-source-hosts.json)
is the whole set, recomputed offline from the committed source caches rather than
from a live fetch — **3,611 distinct hosts across 3,618 source mentions** at the
last run. Regenerate and verify it with:

```sh
python3 scripts/sources/pending.py          # rewrite the JSON
python3 scripts/sources/pending.py --check  # fail if the JSON is stale
```

The two counts above are checked: change the backlog and this file must change
with it.

## Current

The entries below are the ones somebody investigated. Regenerate the run's own
list with:

```sh
python3 scripts/sources/harvest.py
```

| Host | Source | Notes |
| :--- | :--- | :--- |
| `api.rlje.net` | `anudeepnd-whitelist` | Resolves to CloudFront addresses (`3.169.107.x`), returns 403 over HTTPS. No documentation, no matching name, no way to establish who operates it. |

### What was tried for `api.rlje.net`

- **DNS** — three A records, all in Amazon CloudFront's range.
- **HTTPS** — 403 from the origin.
- **Naming** — `rlje` matches nothing in any of the three source files, the
  other names in the same list, or the maintainer's repository.

It could be a legitimate API fronted behind CloudFront whose public name is
simply short. **Guessing is worse than leaving it open**, because a wrong label
is authoritative-looking and nobody can tell it was never checked. It stays
here until somebody knows.

If you know what it is, open a pull request with a rule.