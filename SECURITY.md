# Security

The data in this repository ships inside a commercial iOS app. Two things
follow from that, and this file exists to make both auditable.

## Licensing is enforced, not requested

> **No non-commercial or share-alike data may enter `catalog.json`.**

`CC BY-NC-SA` is **NC** (NonCommercial) and **SA** (ShareAlike). Either one
breaks this repository:

- **NC** — a commercial app may not use it.
- **SA** — the derivative inherits the share-alike term and stops being CC0,
  which is what the [`LICENSE`](LICENSE) promises everyone who takes the data.

Two well-known tracking lists are refused for exactly this reason —
DuckDuckGo Tracker Radar and Disconnect.me. They are **recorded as blocked**
rather than omitted, in [`sources.json`](sources.json), with the reasoning next
to the verdict, so the decision can be argued with instead of rediscovered.

### Where the check lives

`scripts/sources.py` holds the blocking-licence table. `scripts/harvest.py`
refuses a blocked source **before it fetches a byte**, and `test/test.sh` step 1
fails the build if a record claims `allowed: true` on a blocking licence.

That check exists because this repository is open to pull requests. A rule in
a README protects the data only as long as everybody who adds data reads it. A
gate protects it regardless, and it is what keeps the CC0 promise true after
somebody else's commit.

### What this does *not* cover

The gate checks the **licence**, not the **content**. A permissively licensed
list could still be wrong, out of date, or malicious — a poisoned host mapped to
a category that misleads a user. That is a data-quality problem; it is handled
by review and by [`rules.json`](rules.json), not by this file.

## API terms

An API that forbids the intended use is refused even though its data might be
freely licensed:

| Source | Verdict |
| :--- | :--- |
| VirusTotal Public API | **blocked** — must not be used in commercial products or services |
| Cisco Umbrella Investigate | allowed for **evidence only**, never a category |

If you hold a VirusTotal Premium agreement that permits your use, change the
record in `sources.json` and say so in its `reason` field. Do not edit
`scripts/probe.py` to route around the gate.

## A dependency with a clock

Cisco announced **end of sale for Umbrella SIG / DNS on 1 September 2026** (last
order 31 January 2027, support to 31 January 2029).

`scripts/probe.py` caches every answer in `evidence/probes.json` and never
re-asks. The cache is the artefact; the service is not. A rule justified by
cached evidence stays defensible after the service disappears — one justified
by a live dependency does not.

## Reporting a problem

Open an issue, or a pull request if it has a fix. Three things are worth
raising above the rest:

- a source that should be blocked and is not, or vice versa
- a host labelled with a category it plainly is not
- an entry that could mislead a user about what they are connecting to

There is no security contact for this repository beyond its issue tracker.