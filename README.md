# Net Traffic Control — Catalog

Category and service data for **Net Traffic Control**.

The app loads this file as a **Category Data source** (Settings → Category Data → Add
source). It maps host names to a **category** and to the **service/product** they
belong to, so the Live Traffic and Allowed Sites screens group and label domains
correctly.

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

- `categories` — maps a host to one category. A host matches itself and all its
  subdomains (`facebook.com` covers `*.facebook.com`).
- `services` — one entry per **product**, not per company. Facebook, Instagram and
  WhatsApp are separate entries on purpose: the app groups by the product a domain
  belongs to, because a DNS filter sees domains, not apps.

## Category vocabulary

```
analytics, ads, social, messaging, cdn, crash, streaming, gaming, shopping,
search, news, email, encyclopedia, software, ai, finance, government, health,
transport, telecom, travel, education, sports, other
```

Category names outside this list are ignored by the app.

## Precedence in the app

```
user correction  >  imported / remote data (this file)  >  bundled catalog
                 >  suffix rules  >  name patterns  >  "other"
```

A failed or invalid download never replaces the last working data.

## Raw URL

```
https://raw.githubusercontent.com/mahirfatih/net-traffic-control-catalog/main/catalog.json
```

## Generating

`catalog.json` is either maintained by hand or generated from a permitted source by
a script. A generator lives **outside the app**, so that unshippable sources never
reach this repository's shipped output.

Example:

```sh
python3 tools/generate.py --source <permitted-source> --out catalog.json
```

Rules for a generator:

- **Output must use our vocabulary** (see above). Unknown categories are dropped.
- **`key` must stay stable.** The app may cache by it; changing a key re-labels data.
- **Only permitted sources.** If a source is NonCommercial, it must not be committed here.
- **Deterministic output** (sorted keys) so diffs are reviewable and reviewable.

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
