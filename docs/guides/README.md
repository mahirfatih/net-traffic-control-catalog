# `docs/guides/` — how do I work on it

The operator's documents: how a host enters the catalog, how one leaves, when the
sweeps run, and what is still open. The tasks, with their commands.

- [`MAINTAINING.md`](MAINTAINING.md) — generating, adding, removing.
- [`INGEST.md`](INGEST.md) — how a domain gets a category.
- [`PIPELINE.md`](PIPELINE.md) — how a domain is removed.
- [`SCHEDULE.md`](SCHEDULE.md) — when each sweep runs.
- [`NEEDS-REVIEW.md`](NEEDS-REVIEW.md) — what is still open.

## `MAINTAINING.md` — generating, adding, removing

The operator's half of the README: how `catalog.json` is built from `seeds/`, the
four doors a change comes through (harvest, hand-add, override, removal), and the
two-round discipline behind the sweeps. The tasks, with their commands.

## `INGEST.md` — how a domain gets a category

The three doors a host can enter through — a source list, the public-institution
harvester, and a person's hand — with the flow chart, and what each one does and
does not decide. A source carries names, never categories; the category comes
from a rule or a person. The mirror image of [`PIPELINE.md`](PIPELINE.md).

## `PIPELINE.md` — how a domain is removed

The three independent checks behind the README's pipeline chart: the nine DNS
questions, the live sweep, the registration sweep, every verdict, and the four
guardrails that bound them. The README keeps the story; this page keeps the
machinery.

## `SCHEDULE.md` — when each sweep runs

The three sweeps decay at different rates, so they run at different rates:
weekly DNS, monthly live, quarterly registration. The page sets the cadence and
says why, so "when do we re-check?" has an answer that is not "when someone
remembers".

## `NEEDS-REVIEW.md` — what is still open

Hosts a source listed that no rule in
[`../../config/rules.json`](../../config/rules.json) matched. They are in neither
the seeds nor `catalog.json`.

That is the point. A host with no category is an open question; writing it as
`other` would turn the question into a claim, and `other` on screen looks like an
answer. Each entry says what was tried, so the next person does not repeat the
work.

A host leaves this file by getting a rule with a reason, an entry in
`drop.override`, or a `drop.hosts` entry with a reason.
