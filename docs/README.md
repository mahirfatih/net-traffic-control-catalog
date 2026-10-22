# docs

A map of the documents in this repository. The top-level
[`README.md`](../README.md) is the quick tour; start here when you want the
detail behind a number, a rule or a decision. Each folder answers one question —
read the one that matches what you are doing.

## How the folders are organised

| Folder | The question it answers | Written or generated |
| :--- | :--- | :--- |
| [`overview/`](overview) | What this catalog is | written |
| [`guides/`](guides) | How do I work on it | written |
| [`reference/`](reference) | What is in it right now | mostly **generated** |
| [`security/`](security) | What the review found | written |
| [`architecture/`](architecture) | The diagram's input | the source of a generated pair |
| [`diagrams/`](diagrams) · [`analysis/`](analysis) | Assets and generated artifacts | **generated** or imported |

A file marked **generated** is an output: editing it by hand is lost on the next
run, and each one is named with the script that rebuilds it. `./test/test.sh`
regenerates them and fails if they differ, so a hand edit is caught rather than
tolerated.

## Overview — what this catalog is

- [`overview/FOUNDING.md`](overview/FOUNDING.md) — the hosts that came from no source.

## Guides — how do I work on it

- [`guides/MAINTAINING.md`](guides/MAINTAINING.md) — generating, adding and removing hosts, with the commands.
- [`guides/INGEST.md`](guides/INGEST.md) — the three doors a domain enters through; how a domain gets a category.
- [`guides/PIPELINE.md`](guides/PIPELINE.md) — how a domain is removed: the DNS, live and registration sweeps.
- [`guides/SCHEDULE.md`](guides/SCHEDULE.md) — when each sweep runs, and why at that cadence.
- [`guides/NEEDS-REVIEW.md`](guides/NEEDS-REVIEW.md) — the hosts a source listed that no rule matched; what is still open.

## Reference — what is in it right now

- [`reference/CATALOG.md`](reference/CATALOG.md) — every host by category and the service table. **Generated** by `scripts/catalog/build-catalog-docs.py`.
- [`reference/COVERAGE.md`](reference/COVERAGE.md) — how much of the catalog is measured, and from where. **Generated** by `scripts/catalog/build-coverage.py`.
- [`reference/FORMAT.md`](reference/FORMAT.md) — the schema, matching rules and vocabulary the app reads.
- [`reference/INTEGRATION.md`](reference/INTEGRATION.md) — reading the file from another application: tag URLs, the manifest, the SHA-256 check.
- [`reference/IPADDRESS.md`](reference/IPADDRESS.md) — why a bare address is never a host.
- [`reference/SOURCES.md`](reference/SOURCES.md) — why each external source is allowed or refused.

## Security

- [`security/audit.md`](security/audit.md) — what the review found, each finding tied to the file that proves it.

## Analysis — how reliable are the labels

- [`analysis/README.md`](analysis/README.md) — the reliability audit: how consistently each host's own page recovers its label.
- [`analysis/out/README.md`](analysis/out/README.md) — the **generated** audit artifacts (matrix, term lists, error list).

## Diagrams — the catalog pipeline

- [`architecture/source.json`](architecture/source.json) — the outline the diagram is built from.
- [`diagrams/architecture/architecture.html`](diagrams/architecture/architecture.html) — the interactive diagram. **Generated** by `scripts/checks/build-architecture-diagram.mjs`.
- [`diagrams/architecture/architecture.md`](diagrams/architecture/architecture.md) — the written companion.

## Which one do I want?

| You are asking… | Read |
| :--- | :--- |
| "how many hosts, and in what categories?" | [`reference/CATALOG.md`](reference/CATALOG.md) |
| "how much is measured, and from where?" | [`reference/COVERAGE.md`](reference/COVERAGE.md) |
| "what does the file look like, and how does matching work?" | [`reference/FORMAT.md`](reference/FORMAT.md) |
| "how do I consume this from another app?" | [`reference/INTEGRATION.md`](reference/INTEGRATION.md) |
| "how does a domain get a category?" | [`guides/INGEST.md`](guides/INGEST.md) |
| "why can't we use a CC BY-NC-SA list?" | [`reference/SOURCES.md`](reference/SOURCES.md) |
| "did every host come from a source?" | [`overview/FOUNDING.md`](overview/FOUNDING.md) |
| "what is `api.rlje.net`?" | [`guides/NEEDS-REVIEW.md`](guides/NEEDS-REVIEW.md) |
| "why isn't `1.1.1.1` in the catalog?" | [`reference/IPADDRESS.md`](reference/IPADDRESS.md) |
| "how exactly is a dead domain removed?" | [`guides/PIPELINE.md`](guides/PIPELINE.md) |
| "how often do we re-check?" | [`guides/SCHEDULE.md`](guides/SCHEDULE.md) |
| "how do I add or remove a host?" | [`guides/MAINTAINING.md`](guides/MAINTAINING.md) |
| "what is open right now?" | [`security/audit.md`](security/audit.md) |
| "how do I add a host?" | [`../CONTRIBUTING.md`](../CONTRIBUTING.md) |
| "why is non-commercial data refused?" | [`../SECURITY.md`](../SECURITY.md) |

## Elsewhere in the repository

- [`../README.md`](../README.md) — the project overview and the quick tour.
- [`../CONTRIBUTING.md`](../CONTRIBUTING.md) — how to contribute, and how to add a host.
- [`../SECURITY.md`](../SECURITY.md) — the security posture, and why non-commercial data is refused.
- [`../test/README.md`](../test/README.md) — the test folder's index: the runner and what each step proves.
- [`../scripts/README.md`](../scripts/README.md) — the script reference: what every helper does and how to run it.
