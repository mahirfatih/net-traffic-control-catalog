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

Two well-known tracking lists are refused for exactly this reason — DuckDuckGo
Tracker Radar and Disconnect.me, both **CC BY-NC-SA 4.0**. They are not in this
repository, and that is deliberate: `NC` forbids use in a commercial app and
`SA` would make the derivative stop being CC0.

The rule applies to **any** source carrying those terms, not to those two by
name. Nothing here needs to name a source for the gate to work — see
[`scripts/sources/sources.py`](scripts/sources/sources.py).

### Where the check lives

`scripts/sources/sources.py` holds the blocking-licence table. `scripts/sources/harvest.py`
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

A source whose **provider's terms** forbid the intended use is refused on the
same grounds, whatever its data licence says: the VirusTotal Public API, for
instance, states it must not be used in commercial products or services.

If you hold an agreement that permits your use, change the record in
[`sources.json`](sources.json) and say so in its `reason` field. Do not edit the
gate to route around it.

## Reporting a problem

Write to **`irtibat@mahirfatih.com`**, or open an issue if it can be public.
Three things are worth raising above the rest:

- a source that should be blocked and is not, or vice versa
- a host labelled with a category it plainly is not
- an entry that could mislead a user about what they are connecting to

A report about conduct rather than data belongs under
[`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md), which has its own reporting route.