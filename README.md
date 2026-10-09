# Net Traffic Control — Catalog

Category and service data for **Net Traffic Control**.

The app loads this file as a **Category Data source** (Settings → Category Data → Add
source). It maps host names to a **category** (what a name is) and to the
**service/product** it belongs to (whose it is), so the Live Traffic and Allowed
Sites screens group and label domains correctly.

## Contents

- **1,116 categories** — `host → category`.
- **22 services** — `product → hosts`.

## Format (v1)

```json
{
  "version": 1,
  "generated": "YYYY-MM-DD",
  "categories": { "<host>": "<category>" },
  "services": [
    { "key": "<id>", "name": "<Display Name>", "domains": ["<host>", "..."] }
  ]
}
```

### Fields

| Field | Type | Meaning |
| :--- | :--- | :--- |
| `version` | integer | Format version. Bumped only on a breaking change. |
| `generated` | string | Date the file was produced. Informational. |
| `categories` | object | `host → category` (a name from the vocabulary below). |
| `services` | array | One object per product; see below. |
| `services[].key` | string | Stable id the app may cache by. **Never renumber or reuse.** |
| `services[].name` | string | Display name (a product, not a company). |
| `services[].domains` | array | The hosts that belong to this product. |

### Matching

- A `categories` host matches itself **and every subdomain** — `facebook.com`
  covers `*.facebook.com`, so listing the registrable domain is enough.
- A `services` domain matches the same way — `microsoft.com` already covers
  `teams.microsoft.com`, and you do not list it again.
- Matching is case-insensitive.

## Categories

The vocabulary the app understands. A name outside this list is **ignored**.

```
analytics, ads, social, messaging, cdn, crash, video, music, gaming, shopping,
search, news, email, encyclopedia, software, ai, finance, government, health,
transport, telecom, travel, education, sports, crypto, dating, maps, adult,
gambling, other
```

`ipAddress` is also a category, but it is **not** a hostname category — it is what
the app files a literal address under, so it does not belong in this file.

## Services

One entry per **product**, not per company: **Facebook**, **Instagram**,
**WhatsApp** and **Threads** are separate entries on purpose. The app groups by the
product a domain belongs to, because a DNS filter sees domains, not apps — and a
product is what a person recognizes.

Example:

```json
{ "key": "twitter", "name": "Twitter / X",
  "domains": ["twitter.com", "x.com", "t.co", "twimg.com", "twttr.com"] }
```

A **role** (`api.`, `vpn.`, `dns.`) is *not* a service and does not belong here —
the app derives roles from the hostname and shows them as badges, so a role never
splits a product across groups.

## Precedence in the app

```
user correction  >  imported / remote data (this file)  >  bundled catalog
                 >  suffix rules  >  name patterns  >  "other"
```

## Validation

- The app **tests a URL before adding it**: it fetches the file and runs the same
  validation the store uses, then reports **Valid · N entries** or the exact reason
  (not JSON, bad schema, empty, too large, 404, 5xx, no network).
- A failed or invalid download **never replaces the last working data**.

## Raw URL

```
https://raw.githubusercontent.com/mahirfatih/net-traffic-control-catalog/main/catalog.json
```

## Generating

`seeds/` is the source of truth (see [`scripts/`](scripts/README.md)); `catalog.json`
is the build output. Regenerate and validate:

```sh
python3 scripts/generate.py \
    --categories seeds/categories.json \
    --services   seeds/services.json \
    --out        catalog.json
python3 scripts/validate.py
```

Do not edit `catalog.json` by hand — edit `seeds/` instead. A generator that pulls a
permitted **external** source belongs outside the app, so that unshippable sources
never reach this repository's shipped output.

Rules for a generator:

- **Output must use our vocabulary** (see above). Unknown categories are dropped.
- **`key` must stay stable.** The app may cache by it; changing a key re-labels data.
- **Only permitted sources.** If a source is NonCommercial, it must not be committed here.
- **Deterministic output** (sorted keys) so diffs stay reviewable.

## Contributing

- Add entries by hand, or with a generator.
- Every entry should be **traceable to a source** — a wrong label is worse than no
  label, because it looks authoritative.
- Category names must be from the vocabulary; anything else is ignored by the app.
- Keep `services` at the **product** level (Facebook, Instagram, WhatsApp are
  separate), not the parent company.
- Do **not** commit NonCommercial data. This includes DuckDuckGo Tracker Radar and
  Disconnect.me, both licensed **CC BY-NC-SA 4.0**. Their `NC` and `ShareAlike`
  terms are incompatible with shipping this catalog in a commercial/proprietary app.
- Keep the file sorted by host so diffs stay small.

## Versioning

- The app reads `version`; it accepts the versions it knows and ignores the rest.
- Unknown fields and unknown category names are ignored, never fatal.
- `version` is bumped only on a breaking format change.

## License

The data in this repository is dedicated to the public domain under **CC0 1.0
Universal**. See [LICENSE](LICENSE).
