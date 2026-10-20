# seeds

**The source of truth.** `../catalog.json` is the build output and must never
be edited by hand — the next `generate.py` run overwrites the edit.

The build reads two plain-JSON files, both with one command:

```sh
python3 scripts/catalog/generate.py \
    --categories seeds/categories.json \
    --services   seeds/services.json \
    --out        catalog.json
python3 scripts/catalog/validate.py
```

## `categories.json`

A flat `{host: category}` object. Sorted by host — `generate.py` sorts it, and
`validate.py` fails if it is not, so the diff of a change stays small.

```json
{
  "akbank.com": "finance",
  "plex.tv": "software",
  "doubleclick.net": "ads"
}
```

Category names must come from the vocabulary in
[`../config/schema.json`](../config/schema.json) (`scripts/catalog/catalog-core.py` holds the same
list for the validator). **A name outside it is not reported by the app — it is
ignored on device.** `validate.py` turns that silent no-op into a build failure,
which is the only reason the vocabulary is enforced here rather than there.

A host matches itself and every subdomain, so `facebook.com` covers
`graph.facebook.com`. Never list both: the child row can never disagree with
the parent, and it only lengthens the diff.

## `services.json`

An array of products. One entry per **product**, not per company — Facebook,
Instagram, WhatsApp and Threads are separate because a DNS filter sees domains,
not apps, and a product is what a person recognises.

```json
[{ "key": "plex", "name": "Plex", "domains": ["plex.tv", "plexapp.com"] }]
```

| Field | Rule |
| :--- | :--- |
| `key` | **Stable.** The app may cache by it, so renaming one re-labels data on somebody's device. Never renumber or reuse. |
| `name` | A product, not a company. |
| `domains` | Registrable domains; subdomains come with them. |

A **role** (`api.`, `vpn.`, `dns.`) is not a service and does not belong here —
the app derives roles from the hostname and shows them as badges, so a role
would split one product across two groups.

## `public-suffix-exceptions.json`

Multi-tenant suffixes that are **deliberately** listed as a product or platform
(`github.io`, `amazonaws.com`, `cloudfront.net`, `wordpress.com`, …). A bare
suffix like `github.io` also covers every `*.github.io`, so listing one is a
choice, not a default, and each entry needs a reason. If a host in
`categories.json` or a `services.json` domain is a multi-tenant suffix, it must
be named here with a reason — `scripts/catalog/check-overlaps.py` fails
otherwise. The rule and the current set are in
[`../docs/FORMAT.md`](../docs/FORMAT.md), "Matching".

## Editing by hand

The normal path for a handful of hosts. `./test/test.sh` afterwards; it will
tell you if a host cannot be matched or a category is not in the vocabulary.

For a bulk change, do not paste a list in — see
[`../CONTRIBUTING.md`](../CONTRIBUTING.md) § Bulk work, which routes it through
`harvest.py` so every host ends up traceable to a rule rather than to a paste.

Editing by hand is one of three doors a host can enter through. The other two —
a source list and the public-institution harvester — and what sets the category
in each case are in [`../docs/INGEST.md`](../docs/INGEST.md).