# Changelog

All notable changes to this repository are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[semantic versioning](https://semver.org/spec/v2.0.0.html) for the **format**,
not for the data: `version` is bumped only on a breaking format change.

## [Unreleased]

### Added

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

### Changed

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

### Fixed

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