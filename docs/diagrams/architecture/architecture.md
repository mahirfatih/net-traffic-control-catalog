# Catalog pipeline — architecture

This diagram is a didactic walkthrough of how the catalog is built and shipped:
how a host enters, how its category is decided, how the shipped file is produced
from the seeds, and how a release is verified. Every node is a real script or
file in the repository.

- **Interactive version:** [`architecture.html`](architecture.html) — toggle the
  two modes (`offline` / `online`) and step through each flow.
- **Source of truth:** [`../../architecture/source.json`](../../architecture/source.json).
  The HTML is generated from it by
  `scripts/checks/build-architecture-diagram.mjs`. Do not hand-edit the HTML.

## Modes

- **offline — seeds only.** Everything runs from the committed seeds and the
  cached analysis output. This is what CI does, and it is deterministic: the
  same seeds build the same bytes.
- **online — network · browser.** The same pipeline with the parts that reach
  out turned on: harvesting a source list, and reading host pages for the
  reliability audit. Nothing here runs in `./test/test.sh`.

## Nodes

| Node | Role | What it is |
| :--- | :--- | :--- |
| **Maintainer · CI** | actor | A person or CI invoking the scripts. The only actor; nothing runs on its own behalf. |
| **sources/harvest.py** | compute | Fetches a cleared source list. Sends no key, no cookie and no account. |
| **config/ · rules.json** | coordinator | The licence gate (`config/sources.json`) and the overrides (`config/rules.json`). Refuses a non-commercial source before a name is stored. |
| **The three sweeps** | compute | `probe-dead.py`, `sweep-live.py`, `verify-registrations.py` — independent checks that a host is still online and still the same owner. |
| **seeds/** | storage | The source of truth: `categories.json`, `services.json`, `hand-added.json`. Every change lands here first. |
| **guides/NEEDS-REVIEW.md** | deliverable | Hosts a source listed that no rule matched. An open question, not a shipped row. |
| **analysis/build-matrix.py** | compute | Reads each host's page and recovers its label with a text model. Measures labels; never writes them. |
| **catalog/generate.py** | coordinator | Builds `catalog.json` from the seeds and rules. Validates before it writes. |
| **test/test.sh** | gate | The single definition of "green": registry, seeds, build, validation and documentation freshness. |
| **catalog.json** | storage | The shipped artifact: every kept host's category and the service table (~232 KB). |
| **GitHub Release** | deliverable | The tagged distribution. `main` moves; a tag never does. |

## Flows

### 1. Ingest — how a host gets a label

A source carries names, never categories; a rule or a person decides the label.

1. **Pull a trusted list** — `sources/harvest.py` fetches a list already cleared
   in the registry. No credentials travel with the request.
2. **The licence gate** — `sources.py` refuses a non-commercial or blocked
   licence before a name is stored. The refusal is keyed on the *licence*, not on
   a list of names.
3. **A person labels it** — the category is either a rule in `rules.json` or a
   person who wrote down a reason. The page is never asked to invent one.
4. **The seeds are the source of truth** — the change lands in `seeds/`, and
   `catalog.json` is rebuilt from it, so a reviewer reads a seed diff.

See [`../../guides/INGEST.md`](../../guides/INGEST.md) for the three doors a host
can enter through.

### 2. Verify — is the host still real?

Three independent checks, two rounds, and an intersection. One signal never
removes a host.

1. **Three independent checks** — nine DNS questions, a live page read, and a
   registration lookup.
2. **Agreement, not a single signal** — two rounds must agree before anything is
   proposed; unsure keeps the host.
3. **A removal is written down** — the removal becomes a `rules.json →
   drop.hosts` entry with a reason and a date.
4. **Nothing returns quietly** — a check proves the dropped host is absent from
   the seeds.
5. **Unlabelled stays unlabelled** — a host no rule matches becomes an open
   question in `NEEDS-REVIEW.md`, not a row.

See [`../../guides/PIPELINE.md`](../../guides/PIPELINE.md) for the machinery and
[`../../guides/SCHEDULE.md`](../../guides/SCHEDULE.md) for the cadence.

### 3. Build — from seeds to shipped file

`catalog.json` is a pure function of the seeds: regenerate, and the diff is empty
unless something really changed.

1. **Rebuild from the seeds** — `generate.py` reads the seeds and rules and
   writes `catalog.json`, validating first so a bad seed writes nothing.
2. **Deterministic by construction** — hosts and services are sorted, the indent
   is fixed; the same seeds build the same bytes.
3. **catalog.json** — the one file a consumer reads.
4. **Measure the labels** — the reliability audit reads each page and recovers
   the label; it measures, it never writes.
5. **A checksum travels with it** — `manifest.json` records the SHA-256 and size,
   so a consumer pulls the kilobyte manifest before the whole catalog.

See [`../../reference/FORMAT.md`](../../reference/FORMAT.md) and
[`../../reference/COVERAGE.md`](../../reference/COVERAGE.md).

### 4. Verify & ship — nothing leaves red

A release is a tag, and every gate has already passed on the same bytes.

1. **Every gate runs** — one command, the whole suite.
2. **Docs cannot drift** — generated documents are rebuilt and compared byte for
   byte; a hand edit fails the run.
3. **The file validates** — the built catalog is checked against its schema.
4. **A tag publishes the bytes** — the release workflow attaches the catalog and
   its manifest.
5. **Consumers verify before they pull** — read the manifest, compare the hash,
   then fetch the catalog.

See [`../../reference/INTEGRATION.md`](../../reference/INTEGRATION.md) for the
distribution contract.
