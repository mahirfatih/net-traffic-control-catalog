# Changelog

All notable changes to this repository are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[semantic versioning](https://semver.org/spec/v2.0.0.html) for the **format**,
not for the data: `version` is bumped only on a breaking format change.

## [Unreleased]

### Added

- **HotCakeX Microsoft EASM list** as a separate MIT source (`hotcakex-microsoft-easm`). 529 exact-root gaming brand variants (Activision-Blizzard-King, ZeniMax/Bethesda, King) and developer-infrastructure hosts (GitHub, npm) were rule-matched and added; the remaining ~2,600 defensive TLD variants stay in harvest evidence as review-only.
- **In-flight Wi-Fi allowlist** (`itsmingjie-inflight-allowlist`, MIT): airline captive-portal and connectivity domains → `travel`.
- **Gaming platform whitelist** (`jayconius-gaming-whitelist`, MIT badge / no LICENSE file): new roots for EA, Epic, GOG, Paradox, Unity, 2K → `gaming`; ~40 subdomains were already covered by existing rules.
- **AdGuard HTTPS exclusions banks list** (`adguard-https-exclusions-banks`, no LICENSE file): 3,810 finance-domain additions after `www.` normalization, IP rejection, redundant subdomain cleanup, and a manual drop for `qantas.com`.
- **Source import quality audit** (`scripts/sources/audit-source-import.py`) wired into `test/test.sh` to keep broad-source imports reviewable and catch known false positives or redundant source rows.
- **Live source review workflow** (`scripts/sources/review-source-live.py` and shared `scripts/sources/source-policies.py`) for DNS/HTTP evidence on broad imports without editing catalog data.
- **Live review of the AdGuard banks import**: 1,565 weak-signal hosts checked over DNS/HTTP. Unreachable hosts are reported as `unresolved` (a blocked network is not evidence a bank is wrong); 5 confirmed non-finance false positives (`apsiyon.com`, `clhs.kiev.ua`, `datev.de`, `difi.no`, `pasientsky.no`) were moved to `rules.json` → `drop.hosts`.
- **Category override layer** (`rules.json` → `drop.override`, managed by `scripts/catalog/overrides.py`): a per-host human decision that beats every rule and every source, with a mandatory reason. `generate.py` applies it last, `merge.py` never overwrites it, and the audits treat it as deliberate. Wired into `test/test.sh` step 10.8.
- **Dead-domain sweep** (`scripts/catalog/probe-dead.py`): finds catalog hosts that
  no longer exist, for the domain-recycling risk — a lapsed domain can be bought
  by somebody else while keeping the old category. It asks Cloudflare and Google
  directly about A/AAAA/NS and reads the response code, so it can tell `NXDOMAIN`
  from "this network cannot reach it", which the system resolver cannot: nearly
  all of the AdGuard banks are unreachable from here and 181 real banks were
  almost dropped on that evidence. Two rounds at least ten minutes apart, six
  questions per host, both rounds in agreement before anything is called dead.
  `nodata` (name exists, no address record) and `servfail` (broken zone) are
  reported but never proposed for removal. Its decision table is checked in
  `test/test.sh` step 10.9; the script itself needs the network and stays out of CI.
- **Turkish public institution domains.** Harvested ~1,060 `gov.tr` / `bel.tr` /
  `edu.tr` domains and categorised them via `rules.json` (`government`,
  `education`). Catalog grows **1,259 → 2,551 categories** (+1,292).
- **Turkish news domains.** ~70 news hosts (`aa.com.tr`, `haber.com.tr`,
  `cnnturk.com`, etc.) added via `rules.json` → `news` category.
- **Catalog reliability audit enhancements** (`scripts/analysis/`):
  - **Model comparison** across TF-IDF + LinearSVC, logistic regression, and
    multinomial naive Bayes before keeping LinearSVC for the detailed audit.
  - **LinearSVC model-weight terms** per category (complements chi-squared).
  - **Calibrated top-3 predictions** per host (in `matrix-data.json` and
    `high-confidence-errors.md`).
  - **Catalog-order class sorting** so output tables match the catalogue
    vocabulary order.
- **`docs/CATALOG.md` "Reliability" section** — auto-generated from
  `matrix-data.json` by `build-catalog-docs.py`, showing accuracy, host count,
  and link to analysis outputs.
- **Confusion matrix PNG** committed to `docs/analysis/out/confusion-matrix.png`
  (was generated locally only).
- **Six MIT-licensed allowlist/discovery sources** added to `sources.json`:
  HotCakeX Microsoft Domains, omaskery proxy exceptions, three GoodnessJSON
  Pi-hole lists, and Ultimate Hosts whitelist.
- **Keloran Pi-hole whitelist** added as a MIT delta source. It currently adds
  no categories: 180 hosts are already covered, 5 are explicitly dropped, and 1
  remains review-only.
- **189 rule-categorised domains** harvested from the new sources while keeping
  the existing 27-category / 22-service vocabulary fixed. Microsoft-owned names
  are split by function (`software`, `search`, `gaming`, `social`, `email`,
  `ads`, `analytics`, `cdn`, `ai`) rather than by owner.
- **88 additional HotCakeX Microsoft Domains entries** added after a second
  focused pass over clear Windows, Office, Azure, developer tooling, Xbox/Zune,
  Bing/MSN and Microsoft Advertising names.
- **Harvest parsers for structured/mixed allowlists**: a small YAML subset parser
  for proxy exception lists and a stricter Ultimate whitelist parser that skips
  `ALL`, `REG`, `RZD`, IP, local and sample-domain rows.

### Changed

- **Catalog size: 1,259 → 2,803 categories** (+1,544). Breakdown of major
  changes:
  - `government`: 60 → 1,106 (+1,046)
  - `education`: 36 → 213 (+177)
  - `news`: 69 → 130 (+61)
  - `software`: 160 → 299 (+139)
  - `gaming`: 43 → 84 (+41)
  - `search`: 28 → 59 (+31)
  - `cdn`: 57 → 67 (+10)
  - `ads`: 63 → 76 (+13)
  - `email`: 24 → 34 (+10)
- **Analysis accuracy: 66% → 84%** (hosts with text 823 → 1,916, filtered
  823 → 1,844) after re-running `fetch-pages.py` against the expanded
  catalogue.
- **Per-class F1 shifts:** `government` 0.80 → 0.97 (support 55 → 883),
  `education` 0.53 → 0.93 (26 → 161), `news` 0.77 → 0.91 (57 → 115).
  Infrastructure classes (`cdn`, `social`, `travel`, `encyclopedia`) remain
  low-F1 due to minimal page text.
- **README counts updated** to 2,803 categories, 22 services.
- **`docs/CATALOG.md` category table regenerated** with new counts.
- **`merge.py` now skips redundant same-category subdomains** when a listed
  ancestor already covers the host.

### Fixed

- **Category boundary corrections for Microsoft-owned domains.** Skype, Lync and
  GroupMe are now `messaging` instead of `email`; Bing Maps surfaces are `maps`
  instead of `search`; HockeyApp is `crash` instead of `analytics`.
- **Category consistency guardrail** added to `test/test.sh` via
  `scripts/catalog/audit-category-consistency.py`, so future vendor-list imports
  cannot quietly collapse ads, analytics, maps, messaging, mail, AI, gaming and
  CDN/product infrastructure into the wrong category.
- **The reliability headline quoted the wrong number of correct hosts.**
  `README.md` and `docs/analysis/README.md` said **1,553/1,844**; the
  confusion matrix diagonal is **1,545/1,844** (83.79% → still 84%). The
  percentage was right, the numerator was not.
- **`build-catalog-docs.py`**: corrected a garbled sentence in the
  auto-generated Reliability section ("page, not / that the label is wrong"
  → "chi-squared terms and the fitted LinearSVC weights").

### Added (checks)

- **`check-docs-fresh.mjs` now verifies the audit figures** against
  `docs/analysis/out/matrix-data.json` instead of trusting the prose: the
  headline accuracy, correct/total, class count, the whole per-class metric
  table, the model-comparison table, and every `` `class` 0.xx `` F1 quoted in
  the Highest/Lowest lists.
  The two wrong numbers above sat through eleven test runs because nothing
  compared them to the data they claimed to summarise. The check is skipped,
  with a note, when no analysis output is present.
- **`check-overlaps.py` catalog quality report** added to `test/test.sh` step
  10.5. It prints category distribution, deliberate category overrides, and
  redundant subdomains that are already covered by a same-category ancestor.

### Added (earlier)

- **A source registry, and a gate that enforces it.** `sources.json` records
  every external list with its licence and a verdict; `scripts/sources/sources.py`
  refuses a non-commercial or share-alike source before it is fetched. The
  README already said not to commit NC data — this makes it true without
  somebody having to remember.
- **`harvest.py`** — fetch an allowed source, drop what the catalog already
  covers, apply `rules.json`, and report what is left. It never invents a
  category, never overwrites an existing label, and never writes `other` on
  its own.
- **`merge.py`** — apply harvested categories to the seeds, refusing to
  overrule a label a person already set and refusing any category outside the
  vocabulary.
- **`probe.py`** (optional) — gather evidence from an external categoriser. Sets
  no category; caches everything it learns in `evidence/probes.json`.
- **`rules.json`** — the categories an external list cannot supply, written down
  with a reason each.
- **`build-catalog-docs.py`** and generated [`docs/CATALOG.md`](docs/CATALOG.md).
- **`check-docs-fresh.mjs`** — catches a renamed file, a stale count, a broken
  link, or a licence verdict that contradicts itself.
- **`test/test.sh`** — the whole suite in one command, no dependencies.
- **Documents** — [`docs/SOURCES.md`](docs/SOURCES.md),
  [`docs/NEEDS-REVIEW.md`](docs/NEEDS-REVIEW.md), [`CONTRIBUTING.md`](CONTRIBUTING.md),
  [`SECURITY.md`](SECURITY.md).
- **A host-shape rule in the validator.** `catalog-core.py`'s `host_problems` refuses a
  wildcard (`*.example.com`), a URL, an IDNA label, a trailing dot, a stray
  space or a bad label — because the app matches a listed host *whole* and its
  subdomains by suffix, with no glob and no IDNA decoding. Such a row would sit
  in the catalog and never match anything. `test/test.sh` step 10 proves each
  refusal, so the rule cannot quietly stop working.
- **A service-domain check in `test/test.sh`.** Step 2b fails when a domain in
  `seeds/services.json` has no category of its own and none from an ancestor.
  That is exactly the state the thirteen above were in: grouped under the right
  product, counted as `"other"`. The check has teeth — remove `threads.com` from
  the seeds and it goes red.

### Changed (earlier)

- **1,272 → 1,259 categories.** Two corrections in one pass:
  - **26 rows went that only repeated their parent.** A row like
    `players.brightcove.net` → `video` adds nothing over `brightcove.net` →
    `video`, because the app already matches every subdomain of a listed name.
    Only rows whose category *equals* their nearest listed ancestor were
    removed; a row that overrides its parent (`mail.google.com` → `email`
    against `google.com` → `search`) stays.
  - **13 service domains got the category they were missing.** `threads.com`,
    `t.co`, `twttr.com`, `fb.gg`, `facebookmail.com`, `googleusercontent.com`,
    `windows.net`, `redditmedia.com`, `spotifycdn.com`, `vodafone.com`,
    `youtube-nocookie.com`, `amazon-adsystem.com` and `cloudflare-dns.com`.
    They were grouped under the right product but counted as `"other"` in the
    category breakdown — a correct name with a wrong label, which is the worst
    of both.

- **1,116 → 1,272 categories (+156).** Harvested from three anudeepND lists
  (MIT). Sources only *propose hosts*: every category is a rule in
  `rules.json`, so all 156 are traceable.
- **Service count unchanged at 22.** Harvest found products worth their own
  entry — Plex, Pluto TV, Brightcove — but `services[].key` must stay stable
  because the app may cache by it, so they are not added here. They are noted
  in `rules.json` and can be added in a release with a migration note.

### Fixed (earlier)

- **The README's precedence chain skipped a step.** It listed *suffix rules →
  name patterns*, but the app decides a name with an **institutional-label**
  rule in between (`ox.ac.uk` is a university, `tokyo.lg.jp` a prefecture) —
  a rule, so it lives in the app, but a reader of this contract could not see
  where it sat. The chain and a note on the override now match the code.
- **`merge.py` no longer corrupts the seed file.** `catalog-core.py`'s `write()`
  normalises a whole catalog document; writing a bare `{host: category}` seed
  through it wrapped the file in `version`/`generated`/`categories` keys and
  made `generate.py` reject it. The seed is now written directly.

### Not changed

- **No existing category was relabelled.** A disagreement between a source and a
  seed is reported, and the seed wins.
- **No new category name.** The vocabulary in `schema.json` is unchanged.
- **The licence.** The data stays CC0.
