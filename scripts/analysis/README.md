# scripts/analysis

The catalog reliability audit — a maintainer tool, not a check. It fetches each
catalog host's homepage, extracts the title, meta description/keywords, headings
and body, compares nine text classifiers (eight TF-IDF heads and one multilingual
sentence-embedding head), keeps LinearSVC for the detailed audit,
and cross-validates it. It then writes the model comparison, confusion matrix,
per-class metrics, **chi-squared correlated terms**, **LinearSVC model-weight
terms**, **calibrated top-3 predictions per host**, and high-confidence errors to
[`docs/analysis/out/`](../../docs/analysis/out/).

It measures **every category in the catalog**, not only the large ones. Two
things make that work: `fetch-pages.py --retry-empty` re-fetches hosts whose
first attempt came back empty (a category used to drop out of the matrix
whenever its first fetch happened to fail), and `build-matrix.py` keeps
categories down to two examples, lowering the fold count to suit the smallest
one. Categories under 20 examples are recorded as `thin_classes`, and their
per-class scores should be read as indicative rather than measured.

`accuracy` and `balanced_accuracy` are both written for a reason: `finance` is
53% of the catalog, so accuracy mostly reports how well the model predicts
`finance`, and balanced accuracy weights every category equally. The second is
the one that describes the labels as a whole.

This is the one directory under `scripts/` that needs an install step:
`scikit-learn`, `matplotlib` and `sentence-transformers` (which pulls in
`torch`). `test/test.sh` does not run it, and it is not part of the catalog
pipeline.

[`classify-unmeasured.py`](classify-unmeasured.py) explains the other side of
that gap. The audit counts the hosts it could not measure; this says *why* each
one was unmeasurable — nothing answers, it answers with something that is not a
page, or it answers with HTML whose words need JavaScript. Only the first is a
dead end; the other two name what a different signal would need. Standard
library only, and it needs the network, so it too stays out of `test/test.sh`.

## Live sweep — what each host still serves

[`sweep-live.py`](sweep-live.py) is the other half of the picture. The audit
above asks how well a label is *predictable* from a page; this asks whether the
host still serves a page at all, so a name that resolves but has gone dark can
be removed before somebody else registers it and inherits the category.

It drives a real browser through
[agent-browser](https://github.com/vercel-labs/agent-browser) with
[Lightpanda](https://lightpanda.io) as the engine
([why a browser](https://lightpanda.io/blog/posts/using-lightpanda-with-agent-browser),
[how to install it](https://lightpanda.io/docs/open-source/installation)),
rather than a plain fetch, because a fetch that does not run JavaScript sees an
empty shell where a modern page lives. Lightpanda is headless-only and has no
rendering pipeline, so screenshots are placeholders and very heavy single-page
apps may render blank — that shows up in the evidence as `empty`, never as a
silent success.

One browser call per host (`network requests --clear`, then `open`, then an
`eval` that returns the title, URL and text length, then `network requests`),
run across a handful of sessions. Every navigation failure is re-checked with a
canary before it is believed: a long sweep is far more likely to lose its engine
than to meet thousands of genuinely dead hosts, and a poisoned run would hand a
person a list of live sites to delete. A host is only proposed when two
independent rounds agree, and the proposal is cross-checked against the DNS
sweep. Standard library only — it shells out to the browser — but it needs the
network and a `lightpanda` binary, so it stays out of `test/test.sh`; its
decision table is checked there offline, at step 10.10.

```sh
agent-browser --version   # 0.39.1 at the last run
lightpanda version        # 1.0.1 at the last run
python3 scripts/analysis/sweep-live.py --self-test
python3 scripts/analysis/sweep-live.py --round 1 --aggressive
```

The full workflow is in [`../README.md`](../README.md).

### Which checks this passes

The sweep touches the network, so it never runs inside `test/test.sh`. Almost
everything about it is still checked, offline, and the run checks itself while it
goes:

- **`--self-test`** opens a host that certainly serves content and fails the run
  if the browser cannot read it, before any catalog host is visited.
- **A canary on every failure.** A host is never recorded as unresponsive until
  the same session has just proved it can still read a known-good page. If the
  canary also fails, the host is filed `harness-error` and can never be proposed
  — a run that lost its engine must not read as a catalog of dead sites.
- **Two rounds must agree.** `build_proposal` intersects the candidates of every
  *complete* round; one round is a snapshot, and a host judged `harness-error` in
  any round is dropped rather than guessed at.
- **`test/test.sh` step 10.10** — the offline decision table. It checks the
  error-string mapping, the `content`/`parked`/`blocked`/`empty`/`error`
  classification (including the regression that a real page containing a parking
  phrase is *not* parked), the most-alive-attempt rule, and the candidate policy:
  a parked page is proposed by default, a 404/empty host only under
  `--aggressive`, a flaky environment failure only under `--include-flaky`.
- **`scripts/checks/check-docs-fresh.mjs` → `checkLiveSweepEvidence`** — reads
  the evidence offline: at least two complete rounds, each produced by
  `engine: lightpanda`, every seed host covered by every round, the counts adding
  up, and every host that left the seeds carrying a `rules.json` → `drop.hosts`
  reason.
- **`scripts/checks/check-docs-fresh.mjs` → `checkCategoryTreemap`** — reads the
  category treemap back out of `README.md` and compares it, category by
  category, with `catalog.json`.

Run the offline half yourself with `./test/test.sh`; step 8 is the docs check and
step 10.10 is the sweep's decision table.

See [`../../docs/analysis/README.md`](../../docs/analysis/README.md) for the
methodology and the current result.
