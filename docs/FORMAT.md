# Format — the file the app reads

The shape of `catalog.json`, how a host is matched, what the vocabulary means,
and the order in which a label is decided. This is the reference the README used
to carry inline; the README keeps the overview and points here. The raw URL is
the one thing on this page the app itself cites.

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
- **Longest suffix wins.** If `example.com` → `software` and
  `analytics.example.com` → `analytics` are both listed, `analytics.example.com`
  resolves to `analytics`: the more specific record always beats the parent, for
  a category and for a service alike.
- **A public suffix is not a product.** A record for `co.uk`, or a multi-tenant
  suffix such as `github.io`, `blogspot.com`, `amazonaws.com`, `cloudfront.net`
  or `herokuapp.com`, does **not** swallow unrelated subdomains. Listing one is
  refused by default; it takes an explicit exception and a reason, because
  otherwise it mislabels every tenant on that suffix.
- **Conflicts are reported, never silently resolved.** A host listed in two
  `services`, or carrying two categories, is flagged by
  [`scripts/catalog/check-overlaps.py`](../scripts/catalog/check-overlaps.py) and
  must be resolved before merge. Two records of *equal* specificity are a tie,
  and a tie must be broken deterministically (specificity, then host, then
  service key) — never by order of appearance.
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

Three names are in the vocabulary but deliberately absent from the catalog:
`dating`, `adult` and `gambling`. They are the highest-value categories for a
traffic-control app, and a host that belongs in one is best labelled from a
person's judgement about that host, not extrapolated from a broad list. The app
still understands the names, so a contributor may add them when there is
evidence — but a list alone is not evidence.

`ipAddress` is also a category, but it is **not** a hostname category — it is what
the app files a literal address under, so it does not belong in this file. Why it
is still in the vocabulary, and why addresses are never listed here, is spelled
out in [`IPADDRESS.md`](IPADDRESS.md).

## Services

One entry per **product**, not per company: **Facebook**, **Instagram**,
**WhatsApp** and **Threads** are separate entries on purpose. The app groups by the
product a domain belongs to, because a DNS filter sees domains, not apps — and a
product is what a person recognizes.

**Scope.** 22 services cover the catalog today. That is deliberate, not an
oversight: the gap is measured, not guessed — only 2 of the 3,571 `finance` hosts
carry a service, because almost none of them are a product you would name. The
growth target is the first ~100 widely-recognised services, and a candidate is
added when it is a product people name, not when it merely shares a parent
company with one already listed.

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

To change what is in the file, see [`MAINTAINING.md`](MAINTAINING.md).
