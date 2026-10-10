# seeds

**The source of truth.** `../catalog.json` is the build output and must never
be edited by hand — the next `generate.py` run overwrites the edit.

Two files, both plain JSON, both read by one command:

```sh
python3 scripts/generate.py \
    --categories seeds/categories.json \
    --services   seeds/services.json \
    --out        catalog.json
python3 scripts/validate.py
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
[`../schema.json`](../schema.json) (`scripts/catalog-core.py` holds the same
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

## Editing by hand

The normal path for a handful of hosts. `./test/test.sh` afterwards; it will
tell you if a host cannot be matched or a category is not in the vocabulary.

For a bulk change, do not paste a list in — see
[`../CONTRIBUTING.md`](../CONTRIBUTING.md) § Bulk work, which routes it through
`harvest.py` so every host ends up traceable to a rule rather than to a paste.