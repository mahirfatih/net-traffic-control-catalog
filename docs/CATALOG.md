# Catalog

Generated from `catalog.json` by `scripts/catalog/build-catalog-docs.py`. **Do not
edit by hand** — edit `seeds/` and regenerate, or this file and the shipped
data will disagree, which is the one thing a data file must never do.

## Totals

**2,390 names** across **27 categories**, plus **22 services**.

The app loads `catalog.json` as a Category Data source and matches a host
whole, so `facebook.com` covers `graph.facebook.com` without listing it.

## By category

| Category | Hosts | What it means |
| :--- | --: | :--- |
| `software` | 160 | a tool, a platform, a developer utility |
| `shopping` | 101 | a store, a marketplace, a payment provider |
| `video` | 88 | streaming, live TV, a broadcaster |
| `finance` | 80 | banks, cards, trading, markets |
| `news` | 69 | press, and the reporting it depends on |
| `health` | 67 | hospitals, pharmacies, health apps |
| `ai` | 65 | model providers and the products built on them |
| `ads` | 63 | ad networks, affiliate platforms, retargeting |
| `government` | 1106 | ministries, municipalities, agencies |
| `cdn` | 57 | delivery networks carrying somebody else's bytes |
| `social` | 58 | where people talk to each other |
| `travel` | 46 | airlines, booking, ground transport |
| `gaming` | 43 | stores, launchers, and the games |
| `transport` | 42 | shipping, driving, ride and rail |
| `encyclopedia` | 40 | reference, metadata, documentation |
| `education` | 121 | schools, universities, courses |
| `analytics` | 33 | measurement, crash reporting, experimentation |
| `search` | 28 | search engines and search portals |
| `messaging` | 27 | chat, mail, messaging |
| `email` | 24 | mailbox providers |
| `telecom` | 16 | carriers and network operators |
| `other` | 14 | deliberately a last resort, not a fallback |
| `crash` | 12 | crash and error reporting |
| `crypto` | 10 | exchanges, wallets, chains |
| `music` | 10 | streaming and audio |
| `sports` | 7 | leagues, scores, fixtures |
| `maps` | 3 | map tiles and geocoding |

### `other` is a decision

14 hosts sit in `other`: 8 URL shorteners and 6 curated by hand.

The shorteners are `adf.ly`, `bit.ly`, `goo.gl`, `ow.ly`, `redirect.at`, `t.ly`, `tawk.to`, `tinyurl.com`.
A shortener is not a thing a person uses on purpose, so there is no honest
category for it.

The remainder were labelled `other` by hand — `demiroren.com.tr`, `ismarliyo.com`, `koc.com.tr`, `sikayetvar.com`, `yemek.com`, `yerli.com`.

`harvest.py` will not write `other` on its own. Only a rule in `rules.json`
may, because `other` has to be a decision rather than a shrug.

## By service

22 products, one entry each in `seeds/services.json`:

| Service | Domains |
| :--- | --: |
| Akbank (`akbank`) | 1 |
| Amazon (`amazon`) | 7 |
| Apple (`apple`) | 5 |
| ByteDance (`bytedance`) | 8 |
| Cloudflare (`cloudflare`) | 4 |
| Discord (`discord`) | 4 |
| Facebook (`facebook`) | 6 |
| Garanti BBVA (`garantibbva`) | 1 |
| Google (`google`) | 12 |
| Instagram (`instagram`) | 2 |
| Microsoft (`microsoft`) | 9 |
| Netflix (`netflix`) | 5 |
| Reddit (`reddit`) | 4 |
| Spotify (`spotify`) | 3 |
| Telegram (`telegram`) | 3 |
| Threads (`threads`) | 2 |
| Turkcell (`turkcell`) | 1 |
| Twitter / X (`twitter`) | 5 |
| Vodafone (`vodafone`) | 2 |
| WhatsApp (`whatsapp`) | 2 |
| Yandex (`yandex`) | 4 |
| YouTube (`youtube`) | 5 |

One entry per **product**, not per company — Facebook, Instagram, WhatsApp
and Threads are separate on purpose, because a DNS filter sees domains, not
apps, and a product is what a person recognises.

## Where a name came from

| Source | Licence | What it means |
| :--- | :--- | :--- |
| the seeds, curated here | CC0 | a person decided this label |
| `anudeepND` (3 lists) | MIT | hosts commonly caught by overzealous blocklists, used only to *find* hosts that are missing |

Every source, and every source refused, is in [`SOURCES.md`](SOURCES.md).
External sources propose hosts; **no source assigns a category**. A category
is either a rule in `rules.json` or a person with a reason.

Hosts still missing a label are in [`NEEDS-REVIEW.md`](NEEDS-REVIEW.md).
