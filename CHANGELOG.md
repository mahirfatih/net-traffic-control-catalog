# Changelog

All notable changes to this repository are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[semantic versioning](https://semver.org/spec/v2.0.0.html) for the **format**,
not for the data: `version` is bumped only on a breaking format change.

## [Unreleased]

### Added

- **The ingest flow** (`docs/INGEST.md`): how a domain gets a category, as the
  mirror of `PIPELINE.md`'s removal flow. It names the **three doors** a host can
  enter through — a `harvest.py` source, the public-institution harvester, and a
  person editing `seeds/categories.json` by hand — each with its own flow chart,
  and repeats the point that a source carries names, never categories. `README.md`
  and `README.tr.md` grow the entry branch in their pipeline chart and link it;
  `docs/README.md`, `CONTRIBUTING.md`, `seeds/README.md` and `docs/SOURCES.md`
  point at it too.
- **Seeds provenance** (`scripts/catalog/seeds-provenance.py`,
  `docs/FOUNDING.md`): names the hosts in `catalog.json` that **neither a rule
  nor a source accounts for** — the founding layer. Of 6,731 hosts, 4,451 come
  from a rule, 126 from a source, 1,233 from the Turkish public-institution
  harvester, and **921 were typed in by hand**; the full list of the 2,154
  unattributed hosts is committed as `evidence/seeds-only.json`. The file holds
  no timestamp, so the same inputs render the same bytes; `check-docs-fresh.mjs`
  runs `--check` and compares the counts the page quotes against it.
- **Expanded model comparison** (`scripts/analysis/build-matrix.py`): the audit's
  model table grows from three TF-IDF classifiers to nine — the original three
  plus `RidgeClassifier`, `SGDClassifier`, `DecisionTreeClassifier`,
  `RandomForestClassifier` and `KNeighborsClassifier` on the TF-IDF features, and
  a `MultilingualEmbeddingLogReg` head over
  [`paraphrase-multilingual-mpnet-base-v2`](https://huggingface.co/sentence-transformers/paraphrase-multilingual-mpnet-base-v2)
  sentence embeddings, cached under `.embeddings.npz` and installed with
  `sentence-transformers`. The table is descriptive, not a leaderboard: LinearSVC
  stays the witness (highest macro-F1 of the nine), while the embedding model wins
  balanced accuracy (0.666 vs 0.605) because it maps the non-English categories
  into one space where bag-of-words keeps them apart. `README.md`,
  `README.tr.md`, `docs/analysis/README.md` and the generated `Reliability`
  section carry the new figures, which `check-docs-fresh.mjs` recomputes.
- **Turkish README** (`README.tr.md`): a full translation of `README.md`,
  section for section, with a language link at the top of both. `README.md` is
  the source of truth; the Turkish file mirrors it. The generated blocks
  (badges, category treemap and pie, and the verification chart) are
  written into both files by `build-catalog-docs.py`, so the two languages
  cannot disagree about the catalog, and `check-docs-fresh.mjs` fails the build
  if a hand-edit changes one file's blocks and not the other's
  (`checkTurkishMirror`, `test/test.sh` step 8).
- **Category palette** (`reference/category-colors.json`): the app's category
  colours — each category's `tint`, a darkened `tintText`, and its colour
  `family` — copied from the iOS project's `DomainCategoryStyle.swift` so a
  colour lives in one place instead of being re-derived from the app each time.
  The README treemap colours every leaf from it (a `classDef` per category) and
  the pie tints its slices in order through `themeVariables.pieN`.
  `build-catalog-docs.py` refuses to run if a category has no colour, and
  `check-docs-fresh.mjs` reads the colours back out and compares them with the
  file (`checkCategoryColors`, plus the treemap and pie checks), so the diagrams
  cannot silently drift from the palette.
- **Host pipeline flowchart in `README.md`**: a Mermaid `flowchart` of how a name
  travels from a trusted source list, through the DNS, registration and browser
  checks, to a kept catalog entry — drawn in plain language ("is it still
  online?", "keep it" / "remove it") rather than by script name, with the two
  points that are easy to confuse kept apart: the category is a decision, and
  reading a host's page is only a check, never the labeler.
- **Pipeline detail** (`docs/PIPELINE.md`): the machinery behind the README's
  pipeline chart — the three independent checks (the DNS sweep's nine questions,
  the live sweep's real-browser visit, the registration sweep's RDAP → WHOIS → IP
  RDAP chain), every verdict and whether it removes a host, and the four
  guardrails (canary, two rounds, intersection, logged removal). Linked from both
  READMEs' Pipeline sections and from `docs/README.md`.
- **Live sweep** (`scripts/analysis/sweep-live.py`): finds catalog hosts that
  still resolve but no longer serve a page — a parked domain, a lapsed site, a
  host the owner moved — the same domain-recycling risk the dead-domain sweep
  covers, one layer further out. It visits every host with a real browser
  ([agent-browser](https://github.com/vercel-labs/agent-browser) driving
  [Lightpanda](https://lightpanda.io)) because a fetch that does not run
  JavaScript sees an empty shell where a modern page lives, and records the
  status, final URL, title and text length it saw. A navigation failure is only
  believed after a canary proves the engine still works, two rounds must agree,
  and the proposal is cross-checked against `evidence/dead-domain-sweep.json`.
  A verdict this network produced but did not trust — `tls-error`, `timeout`,
  `dns-error` (`youtube-nocookie.com` and `jsdelivr.net` land there on a bad
  afternoon) — is reported for review and never proposed unless
  `--include-flaky` says otherwise. By default only a **parked** page is
  proposed, because a 404 or an empty 200 is common on live infrastructure
  (`adnxs.com`, `3dsecure.akbank.com.tr`); `--aggressive` widens the proposal to
  hosts that answered with nothing.
  Its decision table is checked in `test/test.sh` step 10.10; the script needs
  the network and stays out of CI.
- **Category treemap in `README.md`**: the catalog by category, generated from
  `catalog.json` by `build-catalog-docs.py` between markers, coloured per
  category from `reference/category-colors.json`, and checked
  count-by-count and colour-by-colour by `check-docs-fresh.mjs` so the diagram
  cannot drift.
- **Registration-ownership sweep** (`scripts/catalog/verify-registrations.py`):
  checks that a host is still registered to the same owner — RDAP (IANA
  bootstrap + verified cc supplement + convention probing), port-43 WHOIS
  fallback (DENIC `.de`, TRABIS `.tr`, IANA referral), IP RDAP for the
  address block, and bounded traceroute. Finds the recycling case the DNS and
  browser sweeps cannot see: a lapsed name re-registered by someone else that
  inherits the previous owner's category. Two rounds must agree; a host is only
  proposed on a strong signal (`gone`, `expired`); unknown and unsupported TLDs
  are reported, never deleted. Reference data shipped under `reference/rdap/`.
  Its decision table is checked in `test/test.sh` step 10.11.
- **`--check` on the generators** (`scripts/catalog/generate.py --check`,
  `scripts/catalog/build-catalog-docs.py --check`): rebuild in memory and compare
  with the committed `catalog.json`, `docs/CATALOG.md` and the README blocks,
  writing nothing. The comparison ignores only the `generated` date stamp, so it
  answers "is the committed artifact current?" without git and is not fooled by a
  re-dated file. `test/test.sh` runs `generate.py --check` at step 3b, before the
  build, so a seed change that was never regenerated fails there.
- **Two-way removal ledger** (`check-docs-fresh.mjs`): `rules.json → drop.hosts`
  is the single record of every host removed and why. The check now holds it in
  both directions — a host that left the seeds must have an entry, and a host
  with an entry must not be back in `seeds/categories.json`, because that is a
  removal quietly undoing itself while `generate.py` drops it without a word.
  Runs in `test/test.sh` step 8.
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

### Removed

- **The `xychart-beta` bar chart in both READMEs.** Mermaid colours a bar series
  as a whole, not bar by bar, so it could not be drawn in the category palette
  the treemap and pie now use, and leaving it would have shown one chart in the
  wrong colours. The same figures remain in the treemap (by area) and the pie
  (by share), both per-category coloured. `checkCategoryBar` is gone with it.

### Changed

- **The model comparison is a table in both READMEs.** `README.md` and
  `README.tr.md` now show the three text classifiers as a markdown table
  (accuracy / balanced accuracy / macro-F1 / weighted-F1) instead of a one-line
  quote, and `checkAnalysisFigures` validates every cell, in both languages,
  against `docs/analysis/out/matrix-data.json`.
- **Registration evidence keeps the verdict, not the record.**
  `evidence/registration-verify.json` now stores one decision per host per round
  (`"registered"`, `"gone"`, …) instead of the full RDAP/WHOIS/IP-RDAP bodies and
  a duplicated `_norm` copy, dropping the file from ~54 MB to ~0.5 MB. The
  verdict is what a review and `check-docs-fresh.mjs` read; the underlying record
  is a re-run away.
- **Catalog size: 6,742 → 6,731 categories** (−11). 11 hosts the live sweep
  found serving only a parking page were removed: `apeksbank.com.ua`, `bcr.md`,
  `bubblewitch.com`, `canakkale-bld.gov.tr`, `dunyagazetesi.com.tr`,
  `ibank.ekp.lv`, `online.ptclick.com.ua`, `online.unicombank.com.ua`,
  `ssk-felsberg.de`, `visecaone.ch` and `wideup.net`. Each was re-fetched
  individually and confirmed to serve a registrar parking page ("Buy this
  domain", HugeDomains, "Domain Parked"). The aggressive proposal was **not**
  applied: it contains live sites (`youtube.com`, `whatsapp.com`,
  `washingtonpost.com`) that render empty to a non-JavaScript browser. Every
  removed host is in `rules.json` → `drop.hosts`; evidence in
  `evidence/live-sweep.md`.
- **The reliability figures now say what they cover.** The audit measures 4,565
  of the catalog's 6,745 hosts — 68%. The remaining 2,180 serve no usable page
  text: 1,721 answer nothing at all and 459 return under 100 characters. The
  failures are not spread evenly: `gaming` is measured on 69 hosts
  of 360 (19%) and `software` on 168 of 476 (35%), while `government` (87%) and
  `news` (88%) are nearly complete, because canvas/JS-heavy domains render no
  HTML text and static ones do. A per-class F1 describes the hosts that produced
  text, not the category, and the two were previously confused. `coverage` is
  now recorded per category in `matrix-data.json`, printed by `build-matrix.py`,
  tabulated in `docs/analysis/README.md`, and checked by `check-docs-fresh.mjs`
  so the table cannot drift from the data. The reason breakdown (`unmeasured`)
  is recorded alongside it and the parts are checked to add up, because the
  first version of this paragraph quoted a **byte** count against a character
  threshold: 445 where the answer is 459, leaving 14 hosts unaccounted for
  between the parts and the total.
- **Catalog size: 7,177 → 6,745 categories** (−432). 432 hosts that no longer
  resolve were removed by the dead-domain sweep: two rounds ten minutes apart,
  Cloudflare and Google both answering `NXDOMAIN` for A, AAAA and NS every time.
  304 were stale bank domains from the AdGuard HTTPS exclusions list, 72 were
  defensive TLD variants (`candycrush.club`, `bubblewitch.jp`) that were never
  live, 41 were Turkish public-institution domains. Every removed host is in
  `rules.json` → `drop.hosts` with the evidence that removed it. Full evidence
  in `evidence/dead-domain-sweep.md`.
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

- **The registration sweep would have deleted live hosts, so it now reads a
  `404` before it trusts one.** `rdap.nic.ms` runs an ordinary web server that
  answers *every* lookup — including its own `nic.ms` — with a Tomcat HTML 404,
  not an RDAP `application/rdap+json` body. The tool read that as "not
  registered" and proposed six live Microsoft `.ms` hosts (`aka.ms`, `jwt.ms`,
  `appcenter.ms`, …) for removal, twice, consistently. A `404` now counts as a
  negative only when the endpoint actually speaks RDAP (the RDAP media type, or
  a parseable RDAP error body); anything else falls through to WHOIS and then to
  `unknown`. Two related guards landed with it: `inactive` and `clientHold` are
  **registered-but-not-delegated** and are now a `review` rather than `gone`
  (`investbank.com.ua`), and a host that still resolves in DNS is never `gone`
  whatever the registry says. The offline decision table in `test/test.sh` step
  10.11 covers all three.

- **The audit was not reproducible: `LinearSVC` ran unseeded.** `random_state`
  was `None`, so liblinear shuffled its dual coordinate descent from OS entropy
  and two runs on identical input produced coefficient tables differing around
  the sixth digit — 277 changed lines in a committed artifact, none of them a
  finding, and no way for a reader to tell noise from a change. All four
  `LinearSVC` instantiations now take the same seed; two full runs produce
  byte-identical `matrix-data.json`, verified by diffing them.
- **Nine of the catalog's 27 categories were never measured, and the cause was
  a bug, not their size.** `fetch-pages.py` wrote an empty cache file the first
  time a host returned nothing and never tried again, so a category was dropped
  from the matrix whenever its first fetch attempt failed. `--retry-empty`
  re-fetches those hosts and tries `www.` as well; it recovered 310 hosts
  overall and took the previously unmeasurable categories from 90/168 to 157/168.
  `sports` went from 0 examples to 7, `crash` from 2 to 11, `maps` from 1 to 3.
- **All 27 categories are now in the matrix.** `--min-class` dropped from 20 to
  2 and the fold count adapts to the smallest category, so `maps` with 3
  examples forces a 3-fold matrix instead of being excluded from it. Eight
  categories rest on under 20 examples and are recorded as `thin_classes` so
  their F1 reads as indicative rather than measured. Accuracy falls from 0.902
  to 0.886 and balanced accuracy from 0.672 to 0.595 — the task is harder now
  that infrastructure categories are included, and that is the honest number.
- **The reliability headline was measuring one category and calling it the
  catalog.** `finance` is 53% of the catalog, so accuracy (0.902) and balanced
  accuracy (0.672) differ by 23 points, and only the first was reported.
  `build-matrix.py` now records balanced accuracy, every document quotes it
  beside accuracy, and `check-docs-fresh.mjs` fails if a document drops it —
  the gap is the finding, so a document that quotes accuracy alone is repeating
  the error.
- **The model comparison was not a fair comparison.** LinearSVC and
  LogisticRegression were evaluated with `class_weight="balanced"` while
  MultinomialNB got no reweighting at all, so two models were being judged on a
  2,359-example class and the third was left to guess it. Naive Bayes rejects
  the string `"balanced"` and accepts only an array, so the inverse-frequency
  prior is now computed as sklearn documents it. The effect is the honest one:
  naive Bayes' accuracy fell 0.792 → 0.734 while its macro F1 rose
  0.197 → 0.259 — a model doing no better than the dominant class, shown
  directly instead of inferred.
- **Nine categories were silently unmeasured.** `maps` (2 examples), `music` (6),
  `sports` (7), `crypto` (8), `other` (9), `telecom` (10), `crash` (11),
  `email` (18) and `cdn` (19) fall below the 20-example class floor. The audit
  reported none of it: `cdn` had already left the matrix once with nothing in
  the output to explain it. Dropped classes are now printed, stored as
  `dropped_classes`, and listed in `docs/CATALOG.md`.
- **The documents quoted a sweep duration nobody had measured.** README, SOURCES,
  CONTRIBUTING and `scripts/README.md` all said the dead-domain sweep takes
  "~30 minutes". It takes about ten: 605 s and 583 s for the two real runs.
  Nothing invalidates a guessed duration, so the three-fold error survived until
  somebody read it. `probe-dead.py` now records `elapsed_seconds` in its
  evidence, and `check-docs-fresh.mjs` compares every duration and host-count
  claim a document makes about the sweep against that record, so the number a
  reader plans around is the number the run actually took.
- **`check-overlaps.py` silently discarded the manual override list.** A dead
  `manual = []` line ran after the overrides were loaded from `rules.json`, so
  the "Manual Overrides" section always reported zero — and the report looked
  correct while the override map was populated. It went unnoticed because the
  map was empty at the time it shipped.
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
