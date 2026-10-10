# Sources

Every external list this repository has ever drawn on, and the verdict on each.
The machine-readable version is [`../sources.json`](../sources.json); this file
is where the reasoning lives, so a refusal is never a mystery.

## The rule this repository runs on

> No source assigns a category.

An external list can tell you that `plex.tv` exists. It cannot tell you that
Plex is a media server, and a list that claimed to would be wrong often enough
to be useless. So a host's category is always either **a rule in
[`rules.json`](../rules.json)** or **a person who wrote down why**. Harvesting
only ever *proposes hosts*; `merge.py` refuses to overwrite a label somebody
already decided, and refuses any category outside the vocabulary.

## Allowed

| Source | Licence | Why |
| :--- | :--- | :--- |
| `anudeepnd-whitelist` | MIT | 186 hosts that overzealous blocklists catch. A good source for **finding gaps** in a catalog. |
| `anudeepnd-optional` | MIT | 136 hosts after comments. Same maintainer, same purpose. |
| `anudeepnd-referral` | MIT | 50 hosts. Affiliate and referral endpoints, which is most of what a blocklist misfires on. |
| `umbrella-categorization` | Cisco terms | Evidence only, never a category. See the note below. |

**On the anudeepND lists.** They are called *allowlists*, and this repository
has no allowlist concept — the app decides a domain is allowed when no
enabled list contains it. The lists are used for the opposite of what their name
suggests: they name hosts that are real, widely used, and easily caught by a
rule meant for something else. That makes them a supply of *catalog gaps*, which
is what `harvest.py` uses them for.

## Blocked

| Source | Licence | Why not |
| :--- | :--- | :--- |
| `ddg-tracker-radar` | CC BY-NC-SA 4.0 | **NC** — a commercial app may not use it. **SA** — the derivative would stop being CC0. |
| `disconnect-me` | CC BY-NC-SA 4.0 | Identical reasoning. |
| `virustotal-categories` | proprietary API | Not a licence: the VT Public API must not be used in commercial products or services. |

These are **listed rather than absent**, on purpose. A refusal nobody can
rediscover becomes a rule people work around; a refusal with the reason next to
it can be argued with.

### If you hold a VirusTotal Premium agreement

The `NC`-style restriction above is about the *free* tier. A Premium agreement
may permit your use. Then change `allowed` to `true` in `sources.json` and say
so in the `reason` field — do not edit `scripts/probe.py` to work around the
gate.

### Umbrella is on a clock

Cisco announced **end of sale for Umbrella SIG / DNS on 1 September 2026**: last
order 31 January 2027, support to 31 January 2029.

`probe.py` therefore writes its answers to `evidence/probes.json` and never
re-fetches a host it has already asked about. The cache is the artefact; the
service is not. A rule written from cached evidence stays defensible after the
service is gone — a rule written from a live dependency does not.

## Adding a source

1. Append a record to `sources.json` with `id`, `name`, `url`, `license`,
   `allowed` and, if not allowed, a `reason`.
2. Run `python3 scripts/sources.py --check`. A blocking licence with
   `allowed: true` is an **error**, not a warning — that is the mistake this
   registry exists to catch.
3. If it is a list rather than a categoriser, add a note in `rules.json` saying
   which hosts it contributes, and be explicit about parked or throwaway
   domains so `harvest.py` can drop them with a reason instead of guessing.
4. Open a pull request. The gate runs there too.

### Licence verdicts

| Licence | Verdict |
| :--- | :--- |
| CC0 / public domain | allowed |
| MIT, BSD, Apache-2.0, ISC | allowed |
| CC BY (no NC, no SA) | allowed |
| CC BY-**NC**-*, CC BY-NC-SA-* | **blocked** — commercial use forbidden |
| CC BY-*-**SA** | **blocked** — the derivative inherits the share-alike term and stops being CC0 |
| proprietary API | blocked unless the registry record says otherwise, in writing |

The table in `scripts/sources.py` is the enforcement point; this table is the
explanation of it. If the two disagree, the code is right and this file is stale.

## What a source is not allowed to do

- **Invent a category.** `harvest.py` has no path that assigns one.
- **Overwrite a label.** A disagreement is printed and the seed is kept.
- **Add `other` by default.** `other` means "a person looked and did not know",
  so only a rule may produce it. Hosts with no rule go to
  [`NEEDS-REVIEW.md`](NEEDS-REVIEW.md) instead.
- **Silently lose hosts.** A line the parser does not understand is reported,
  not dropped.