# Net Traffic Control — Catalog

Category and service data for **Net Traffic Control**.

The app loads this file as a **Category Data source** (Settings → Category Data → Add
source). It maps host names to a **category** (what a name is) and to the
**service/product** it belongs to (whose it is), so the Live Traffic and Allowed
Sites screens group and label domains correctly.

## Contents

- **1,259 categories** — `host → category`.
- **22 services** — `product → hosts`.

See [`docs/CATALOG.md`](docs/CATALOG.md) for the breakdown by category.

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
                 >  public-suffix rules  >  institutional label  >  name patterns
                 >  "other"
```

The **institutional-label** rule is the one between the suffix rules and the
patterns: it reads the label in front of a real country-code domain and calls
`ox.ac.uk` a university and `tokyo.lg.jp` a prefecture. It is a rule, not
content, so it lives in the app — but it sits in the chain, and a name that has
no row anywhere is decided by it before `"other"`.

A **user correction** outranks everything, including this file: the user looked
at the name and said otherwise, and the app treats that as a label, not a rule.

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

Do not edit `catalog.json` by hand — edit `seeds/` instead.

Run everything — registry, schema, build, validator, docs, licence gate — with:

```sh
./test/test.sh
```

### Harvesting from an external source

An external list can tell you that a host exists. It cannot tell you what the
host *is*, so it never assigns a category: `harvest.py` proposes hosts and
`rules.json` (or a person) labels them.

```sh
python3 scripts/harvest.py
python3 scripts/merge.py evidence/harvested-categories.json --dry-run
python3 scripts/merge.py evidence/harvested-categories.json
```

Rules for a generator:

- **Output must use our vocabulary** (see above). An unknown category is not
  reported by the app — it is silently ignored, so `validate.py` fails the
  build instead.
- **`key` must stay stable.** The app may cache by it; changing a key re-labels data.
- **Deterministic output** (sorted keys) so diffs stay reviewable.
- **Only permitted sources**, enforced in code rather than by convention: every
  source lives in [`sources.json`](sources.json) with its licence, and
  [`scripts/sources.py`](scripts/sources.py) refuses a non-commercial or
  share-alike licence *before* fetching it. See
  [`docs/SOURCES.md`](docs/SOURCES.md) for the reasoning, and
  [`SECURITY.md`](SECURITY.md) for why it is a gate rather than a note.

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
  [`sources.json`](sources.json) records the licence of every source and
  [`scripts/sources.py`](scripts/sources.py) refuses the blocked ones before
  fetching, and `./test/test.sh` fails if a record claims otherwise.

Full guide: [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Versioning

- The app reads `version`; it accepts the versions it knows and ignores the rest.
- Unknown fields and unknown category names are ignored, never fatal.
- `version` is bumped only on a breaking format change.

## Catalog Consistency Analysis

A one-off analysis ([`docs/analysis/`](docs/analysis/)) fetches homepage text
for catalog hosts, trains a TF-IDF + LinearSVC classifier on our labels, and
renders a confusion matrix showing how consistently our labels agree with what
a text model can recover.

![Confusion matrix](docs/analysis/out/confusion-matrix.png)

**Accuracy: 66%** (543/823, 19 classes, 5-fold CV). This measures
*self-consistency*, not correctness — it shows whether our labels are
predictable from page content. Low diagonal = label disagrees with the page
(either the label is wrong, or the page is not representative).

- **Highest F1:** `ai`, `finance`, `government`, `health`, `messaging` — all
  0.80. These categories have strong, distinctive page signals.
- **Lowest F1:** `travel` 0.41, `cdn` 0.43, `social` 0.44 — some of these
  are infrastructure (page text is meaningless). But correlated terms reveal
  potential miscategorizations (e.g. `search` correlates with "gmail
  rseller" — Google services, not search engines).
- **High-confidence errors:** only 1 host (`googlesyndication.com`, labeled
  `ads` but predicted `search` at 77% confidence — Google's ad infra,
  debatable label).

See [`docs/analysis/README.md`](docs/analysis/README.md) for full methodology,
per-class metrics, correlated terms, and the error list.

## License

The data in this repository is dedicated to the public domain under **CC0 1.0
Universal**. See [LICENSE](LICENSE).
