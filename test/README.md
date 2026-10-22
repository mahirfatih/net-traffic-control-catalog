# test

The whole suite. Nothing here needs a network, a build system, or an install
step — Python 3 standard library and Node are the only requirements.

```sh
./test/test.sh          # all twenty-seven steps
./test/test.sh --fast   # skip the byte-compile sweep (26 steps)
```

**Exit code `0` means the shipped data is consistent with its seeds and its
documents.** Any non-zero stops the run at the first failure, because a later
step reporting a problem that an earlier one caused is noise.

## Every step, in order (28 of them)

`./test/test.sh` runs these in exactly this order and stops at the first
failure. `./test/test.sh --fast` runs the same list minus step 11.

| # | Step | What it catches |
| --: | :--- | :--- |
| 1 | Source registry — licences and verdicts | a source marked `allowed` on a licence that blocks it, a blocked source with no reason, a bad URL or id |
| 2 | Seeds parse and use the vocabulary | a category outside the vocabulary, an unsorted seed file, a duplicate service `key` |
| 2b | Every service domain is a category or carries one | a product's domain that resolves to no category — correct grouping, wrong label |
| 3 | Was `catalog.json` hand-edited? | **runs before the build**, because the build would silently repair the mistake |
| 3b | The committed `catalog.json` matches the seeds (`generate.py --check`) | a seed change that was never regenerated, caught without git; `--check` writes nothing |
| 3c | The release manifest describes `catalog.json` | a regenerated catalog whose `manifest.json` still quotes the old bytes — a published checksum that lies about the file beside it; **runs before the build**, for step 3's reason |
| 4 | Build `catalog.json` from the seeds | a seed that fails validation; nothing is written when it does |
| 5 | Validate the built catalog | the format, the vocabulary, and every host's shape |
| 6 | `catalog.json` is what the seeds say it is | the built file differing from the seeds it was built from |
| 6b | The same seeds build byte-identical output (determinism) | a build that is not a pure function of its seeds — same seeds, same SHA-256, with only the date pinned |
| 7 | Regenerate the documentation and confirm it is current | a document that changed when regenerated — i.e. edited by hand |
| 7b | The document writer is deterministic (`build-catalog-docs.py --check`) | a writer that renders the same input two different ways; exercises `--check` on the just-written files |
| 7c | The coverage report is current | `docs/reference/COVERAGE.md` edited by hand or left behind by a regenerate, then the writer's own `--check` |
| 8 | Documentation describes the files that exist | broken links, renamed scripts, stale counts, a licence verdict that contradicts itself, a removal that undid itself, a sweep that no longer covers the catalog, a category treemap that disagrees with `catalog.json`, a stale seeds-provenance file, a stale review backlog, a Turkish README whose blocks diverged from the English one (see the twenty-three sub-checks below) |
| 9 | The licence gate refuses, whatever the registry happens to list | `NC` and `SA` licences refused even when a record claims `allowed` — tested against synthetic records, so it does not depend on a blocked source being present |
| 10 | A malformed host is refused, a valid one accepted | 11 malformed names (`*.example.com`, `exa mple.com`, `exämple.com`, `example.com.`…) the app could never match |
| 10.5 | Catalog overlap and distribution check | one host claimed by two categories, an implausible category split |
| 10.5b | A multi-tenant suffix and a two-service domain are refused | an unexcused `github.io`-style suffix, a whitespace-only reason, one domain under two service keys or a repeated key — plus the committed data being clean of all of them |
| 10.6 | Category consistency guardrails | a category that contradicts the vocabulary or the rules it comes from |
| 10.7 | Source import quality guardrails | an imported source whose records fail the licence or shape rules |
| 10.8 | Category overrides are valid and beat rules | an override outside the vocabulary, an override with no reason, a host in both `drop` and `override` |
| 10.9 | A dead-domain sweep keeps what it cannot prove | a resolver answer that would let a live bank be graded `dead`; a host called dead by only one round |
| 10.10 | A live sweep keeps what it cannot prove | a navigation error mapped to the wrong decision, a real page called parked, a candidate that is not the intersection of both rounds |
| 10.11 | A registration sweep keeps what it cannot prove | an RDAP record parsed wrong, a gone/expired/registered/recently-registered decision flipped, an `inactive`/`clientHold` name called gone, a DNS-resolving host called gone, an HTML 404 mistaken for an RDAP negative, a DENIC/TRABIS whois verdict misread, a candidate that is not the intersection of both rounds |
| 10.12 | A hand-added host records who, when and why | a hand-added record missing `by`/`at`/`reason`, naming a host that is not in the seeds, or carrying a bad date |
| 10.13 | Render output is assembled like plain-HTML output | the browser-rendered path parsing or assembling page text differently from the plain-HTML one |
| 10.14 | The version bumper reaches every contract site | `bump-version.sh` leaving a version literal at the old value, failing to rebuild the catalog, leaving `manifest.json` describing the old bytes, or accepting a backwards, repeated or zero bump |
| 11 | Every script compiles | a script that no longer parses (**skipped by `--fast`**) |

### Step 8 runs twenty-three sub-checks

`node scripts/checks/check-docs-fresh.mjs` is one step but twenty-three checks, run in
this order:

1. `checkLinks` — every relative link in the docs points at a file that exists.
2. `checkScriptNames` — every script named in the docs exists, and is listed.
3. `checkSourceIds` — every source id cited in the docs is in the registry.
4. `checkGeneratedDocs` — `docs/reference/CATALOG.md`'s host and service totals match `catalog.json`.
5. `checkCategoryTable` — `docs/reference/CATALOG.md`'s category table matches the seeds.
6. `checkCoverageDoc` — `docs/reference/COVERAGE.md`'s host total and its `finance` row match `catalog.json`.
7. `checkLicenseGate` — no doc advertises a licence the gate refuses.
8. `checkDirectoryReadmes` — every directory with content has a README.
9. `checkAnalysisFigures` — the analysis numbers match `matrix-data.json`.
10. `checkMeasuredRuntimes` — quoted probe runtimes match the recorded ones.
11. `checkSweepEvidence` — the dead-domain evidence covers the catalog.
12. `checkDropListSeparation` — a host in `rules.json → drop.hosts` is not also back in `seeds/categories.json` (a removal silently undoing itself).
13. `checkLiveSweepEvidence` — the live-sweep evidence has ≥2 complete rounds on the Lightpanda engine and covers every seed host.
14. `checkRegistrationEvidence` — the registration evidence has ≥2 complete rounds and covers every seed host.
15. `checkCategoryTreemap` — the README mermaid treemap's counts and colours match `catalog.json` and `reference/category-colors.json`.
16. `checkCategoryColors` — `reference/category-colors.json` gives a valid tint for every category in the catalog.
17. `checkCategoryPie` — the README pie's slices, folded tail and colours match `catalog.json` and `reference/category-colors.json`.
18. `checkCatalogBadges` — the README badges' headline numbers match `catalog.json`.
19. `checkVerificationStatus` — the README verification chart matches the DNS sweep's last round.
20. `checkTurkishMirror` — `README.tr.md` exists and carries the same generated blocks as `README.md`, and the same number of headings and diagrams, so the Turkish translation cannot drift from the English source.
21. `checkSeedsProvenance` — `evidence/seeds-only.json` is current (`scripts/catalog/seeds-provenance.py --check`), and the counts `docs/guides/INGEST.md` and `docs/overview/FOUNDING.md` quote are the ones it holds.
22. `checkHandAdded` — every host in `seeds/hand-added.json` records who, when and why, and names a host that is actually in the seeds.
23. `checkPendingBacklog` — `evidence/pending-source-hosts.json` is current (`scripts/sources/pending.py --check`), and the counts `docs/guides/NEEDS-REVIEW.md` quotes are the ones it holds.

## Why step 3 is where it is

`generate.py` overwrites `catalog.json`. If that check ran after the build, a
hand edit would be repaired and reported as clean — the one failure mode this
repository cannot afford, because the output is what the app ships. Step **3b**
then asks the stronger question — do the seeds still build this exact file? — via
`generate.py --check`, which writes nothing and needs no git.

## The sweeps, checked without the network

Three tools visit real hosts — `probe-dead.py` (DNS), `sweep-live.py` (a real
browser through agent-browser + Lightpanda) and `verify-registrations.py`
(RDAP/WHOIS) — and all need the network, so none runs here. Their *decisions* are
still proven offline: step 10.9 exercises the dead-domain table, step 10.10 the
live-sweep table, and step 10.11 the registration table, so a change that would
let a live bank be called dead fails the suite instead of a run against the real
internet.

## Running one check

There is no per-step flag on purpose: the steps are fast enough that selecting
among them costs more than running them. To run one script directly:

```sh
python3 scripts/catalog/validate.py
python3 scripts/sources/sources.py --check
node scripts/checks/check-docs-fresh.mjs
```

## Where output goes

Nowhere. Every check prints to stdout and reports through its exit code, so
the suite is usable from a pre-push hook or a CI step without redirection.