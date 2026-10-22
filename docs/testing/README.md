# testing

How this catalog is verified — what proves a change is safe, and what is proven
without touching the network. Each folder answers one question; this one answers
"how do I verify it".

The whole suite is [`../../test/test.sh`](../../test/test.sh): twenty-eight steps,
Python 3 standard library and Node only, no build step and no network. It is the
gate a change passes before it ships, and [`../../test/README.md`](../../test/README.md)
lists every step and what it catches. This folder is about how to think about
verification, not a second copy of that table.

## What runs where

| Layer | Entry point | Needs the network |
| :--- | :--- | :--- |
| The whole suite | [`../../test/test.sh`](../../test/test.sh) | no |
| Documentation drift | [`../../scripts/checks/check-docs-fresh.mjs`](../../scripts/checks/check-docs-fresh.mjs) | no |
| The diagram's shape | [`../architecture/source.json`](../architecture/source.json) | no |

The suite is self-verifying: it regenerates the documents and the catalog and
fails if the committed bytes differ, so a hand edit to a **generated** file is
caught rather than tolerated.

## The sweeps, without the network

Three tools visit real hosts — the DNS probe, the live browser sweep and the
registration check — and all three need the network, so none runs here. Their
decisions are proven offline with synthetic records instead, so a change that
would let a live bank be graded dead fails the suite rather than a run against
the real internet. What each sweep does and when it runs is in
[`../guides/PIPELINE.md`](../guides/PIPELINE.md) and
[`../guides/SCHEDULE.md`](../guides/SCHEDULE.md).

## The reliability audit

The classifier's precision and recall are measured, not asserted:
[`../analysis/README.md`](../analysis/README.md) holds the method and the numbers,
and [`../analysis/out/README.md`](../analysis/out/README.md) the generated
artifacts they come from.

## Where a change is gated

Before you open a pull request run [`../../test/test.sh`](../../test/test.sh) and
make it green — [`../../CONTRIBUTING.md`](../../CONTRIBUTING.md) covers the commit
format and the documentation rules that go with it. The same suite runs on demand
from the Actions tab ([`../../.github/workflows/ci.yml`](../../.github/workflows/ci.yml)).
