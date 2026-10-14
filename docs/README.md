# docs

Three documents, and the difference between them is who is allowed to write
them.

| Document | Written by | Edit it? |
| :--- | :--- | :--- |
| [`CATALOG.md`](CATALOG.md) | `scripts/catalog/build-catalog-docs.py` | **No.** Regenerate it. |
| [`SOURCES.md`](SOURCES.md) | a person | Yes |
| [`NEEDS-REVIEW.md`](NEEDS-REVIEW.md) | a person | Yes |

## `CATALOG.md` — what is in the data

Counts per category, the `other` list, the service table. Generated from
`catalog.json` because a hand-written copy of a data file is a second copy to
keep in step, and the first harvest would have made it quietly wrong.

```sh
python3 scripts/catalog/build-catalog-docs.py
```

`./test/test.sh` regenerates it and fails if it differs, so a hand edit is
caught rather than tolerated.

## `SOURCES.md` — why each source is allowed or refused

Every external list, its licence, and the verdict on it. The machine-readable
version is [`../sources.json`](../sources.json).

It exists because a refusal nobody can rediscover becomes a rule people work
around — so the refusal is a table keyed on the **licence**, not a list of
source names. The next `NC` list is refused without anybody having to add it
to a list first.

## `NEEDS-REVIEW.md` — what is still open

Hosts a source listed that no rule in [`../rules.json`](../rules.json) matched.
They are in neither the seeds nor `catalog.json`.

That is the point. A host with no category is an open question; writing it as
`other` would turn the question into a claim, and `other` on screen looks like
an answer. Each entry says what was tried, so the next person does not repeat
the work.

A host leaves this file by getting a rule with a reason, an entry in
`drop.override`, or a `drop.hosts` entry with a reason.

## Which one do I want?

| You are asking… | Read |
| :--- | :--- |
| "how many hosts, and in what categories?" | [`CATALOG.md`](CATALOG.md) |
| "why can't we use a CC BY-NC-SA list?" | [`SOURCES.md`](SOURCES.md) |
| "what is `api.rlje.net`?" | [`NEEDS-REVIEW.md`](NEEDS-REVIEW.md) |
| "how do I add a host?" | [`../CONTRIBUTING.md`](../CONTRIBUTING.md) |
| "why is non-commercial data refused?" | [`../SECURITY.md`](../SECURITY.md) |