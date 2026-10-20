# docs

Thirteen documents, and the difference between them is who is allowed to write
them.

| Document | Written by | Edit it? |
| :--- | :--- | :--- |
| [`CATALOG.md`](CATALOG.md) | `scripts/catalog/build-catalog-docs.py` | **No.** Regenerate it. |
| [`COVERAGE.md`](COVERAGE.md) | `scripts/catalog/build-coverage.py` | **No.** Regenerate it. |
| [`FORMAT.md`](FORMAT.md) | a person | Yes |
| [`FOUNDING.md`](FOUNDING.md) | a person; the counts come from `evidence/seeds-only.json` | Yes |
| [`INGEST.md`](INGEST.md) | a person | Yes |
| [`INTEGRATION.md`](INTEGRATION.md) | a person | Yes |
| [`IPADDRESS.md`](IPADDRESS.md) | a person | Yes |
| [`MAINTAINING.md`](MAINTAINING.md) | a person | Yes |
| [`NEEDS-REVIEW.md`](NEEDS-REVIEW.md) | a person | Yes |
| [`PIPELINE.md`](PIPELINE.md) | a person | Yes |
| [`SCHEDULE.md`](SCHEDULE.md) | a person | Yes |
| [`SOURCES.md`](SOURCES.md) | a person | Yes |
| [`audit.md`](audit.md) | a person; each finding cites the file that proves it | Yes |

## `CATALOG.md` — what is in the data

Counts per category, the `other` list, the service table. Generated from
`catalog.json` because a hand-written copy of a data file is a second copy to
keep in step, and the first harvest would have made it quietly wrong.

```sh
python3 scripts/catalog/build-catalog-docs.py
```

`./test/test.sh` regenerates it and fails if it differs, so a hand edit is
caught rather than tolerated.

## `COVERAGE.md` — how much is measured, and from where

The other half of `CATALOG.md`: the size of each category is one question, how
much of each one the analysis could actually read — and which single source is
carrying it — is another. Generated from the catalog, the rules, the harvest
summary and the analysis output.

```sh
python3 scripts/catalog/build-coverage.py
```

It is where the catalog's central fact is stated plainly: `finance` is over half
the rows, and 98% of it comes from one bank list. Both are warnings to a reader,
not bugs — which is exactly why they belong in a generated file that cannot
quietly fall out of step.

## `FORMAT.md` — the file the app reads

The schema, the matching rules (longest suffix, public-suffix refusal, ties), the
category vocabulary, the service shape, the precedence order and the raw URL.
Reference material, split out of the README when it grew past an overview.

## `INGEST.md` — how a domain gets a category

The three doors a host can enter through — a source list, the public-institution
harvester, and a person's hand — with the flow chart, and what each one does and
does not decide. A source carries names, never categories; the category comes
from a rule or a person. The mirror image of `PIPELINE.md`.

## `INTEGRATION.md` — reading the file from another application

The distribution contract for anything that is not the iOS app: the pinned tag
URL beside the moving `main` one, the kilobyte `manifest.json` that says whether
the catalog changed before the whole file is pulled, the SHA-256 check, and the
line between what is guaranteed (`version`, `services[].key`) and what moves on
every regenerate (counts, the date). The file ships plain — no gzip.

## `PIPELINE.md` — how a domain is removed

The three independent checks behind the README's pipeline chart: the nine DNS
questions, the live sweep, the registration sweep, every verdict, and the four
guardrails that bound them. The README keeps the story; this page keeps the
machinery.

## `FOUNDING.md` — the hosts that came from no source

The provenance of the hosts that neither a rule nor a source accounts for: the
founding layer. Its numbers are read from
[`evidence/seeds-only.json`](../evidence/seeds-only.json), which
`scripts/catalog/seeds-provenance.py` keeps current. The JSON holds the full host
list; this page explains what it means.

## `SOURCES.md` — why each source is allowed or refused

Every external list, its licence, and the verdict on it. The machine-readable
version is [`../config/sources.json`](../config/sources.json).

It exists because a refusal nobody can rediscover becomes a rule people work
around — so the refusal is a table keyed on the **licence**, not a list of
source names. The next `NC` list is refused without anybody having to add it
to a list first.

## `NEEDS-REVIEW.md` — what is still open

Hosts a source listed that no rule in [`../config/rules.json`](../config/rules.json) matched.
They are in neither the seeds nor `catalog.json`.

That is the point. A host with no category is an open question; writing it as
`other` would turn the question into a claim, and `other` on screen looks like
an answer. Each entry says what was tried, so the next person does not repeat
the work.

A host leaves this file by getting a rule with a reason, an entry in
`drop.override`, or a `drop.hosts` entry with a reason.

## `IPADDRESS.md` — why an address is never a host

A bare IP is not a name, and a catalog keyed on names cannot hold one. The page
records why the distinction is load-bearing — an address changes owner silently
and a name does not — so the rule is not rediscovered as a bug.

## `SCHEDULE.md` — when each sweep runs

The three sweeps decay at different rates, so they run at different rates:
weekly DNS, monthly live, quarterly registration. The page sets the cadence and
says why, so "when do we re-check?" has an answer that is not "when someone
remembers".

## `MAINTAINING.md` — generating, adding, removing

The operator's half of the README: how `catalog.json` is built from `seeds/`, the
four doors a change comes through (harvest, hand-add, override, removal), and the
two-round discipline behind the sweeps. The tasks, with their commands.

## `audit.md` — what the review found

The health report: category imbalance and source concentration, a concrete
mislabel, the unmatched backlog, the seeds-provenance gap, the JS-coverage limit,
and a side effect of `generate.py` stamping today's date — each finding tied to
the file that proves it. A report rather than a routine doc: it lists the open
problems, and a finding that gets closed is folded back into the doc that now
explains it.

## Which one do I want?

| You are asking… | Read |
| :--- | :--- |
| "how many hosts, and in what categories?" | [`CATALOG.md`](CATALOG.md) |
| "how much is measured, and from where?" | [`COVERAGE.md`](COVERAGE.md) |
| "what does the file look like, and how does matching work?" | [`FORMAT.md`](FORMAT.md) |
| "how do I consume this from another app?" | [`INTEGRATION.md`](INTEGRATION.md) |
| "how does a domain get a category?" | [`INGEST.md`](INGEST.md) |
| "why can't we use a CC BY-NC-SA list?" | [`SOURCES.md`](SOURCES.md) |
| "did every host come from a source?" | [`FOUNDING.md`](FOUNDING.md) |
| "what is `api.rlje.net`?" | [`NEEDS-REVIEW.md`](NEEDS-REVIEW.md) |
| "why isn't `1.1.1.1` in the catalog?" | [`IPADDRESS.md`](IPADDRESS.md) |
| "how exactly is a dead domain removed?" | [`PIPELINE.md`](PIPELINE.md) |
| "how often do we re-check?" | [`SCHEDULE.md`](SCHEDULE.md) |
| "how do I add or remove a host?" | [`MAINTAINING.md`](MAINTAINING.md) |
| "what is open right now?" | [`audit.md`](audit.md) |
| "how do I add a host?" | [`../CONTRIBUTING.md`](../CONTRIBUTING.md) |
| "why is non-commercial data refused?" | [`../SECURITY.md`](../SECURITY.md) |