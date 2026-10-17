# evidence

What the harvest fetched, and what it concluded — kept so a claim can be
checked without re-downloading anything.

Nothing here is hand-written. `scripts/sources/harvest.py`,
`scripts/catalog/probe-dead.py`, `scripts/catalog/verify-registrations.py`,
`scripts/analysis/sweep-live.py`,
`scripts/analysis/classify-unmeasured.py` and
`scripts/sources/review-source-live.py` each write their own files.

| File | What it is |
| :--- | :--- |
| `anudeepnd-<id>.txt` | The raw source file exactly as downloaded, comments and all. |
| `harvest-summary.json` | What the last run did: which hosts it categorised, which were already covered, which were dropped **and why**, and which still need a decision. |
| `harvested-categories.json` | The proposed `{host: category}` mapping, ready for `merge.py`. Gitignored — regenerate it with `python3 scripts/sources/harvest.py`. |
| `dead-domain-sweep.json` / `.md` | The DNS sweep's per-host verdicts (two rounds, nine questions each) and the proposal it produced. Written by `scripts/catalog/probe-dead.py`. |
| `live-sweep.json` / `.md` | The browser sweep's per-host verdicts — the status, final URL, title and text length a real browser saw, and the proposal when two rounds agree. Written by `scripts/analysis/sweep-live.py`. |
| `registration-verify.json` / `.md` | The registration-ownership sweep's per-host **verdict** (`"registered"`, `"gone"`, …), one per round, and the proposal when two rounds agree. The RDAP/WHOIS/IP-RDAP bodies behind a verdict are not kept — a verdict is what a review reads, and the raw records ran to tens of megabytes. Written by `scripts/catalog/verify-registrations.py`; re-run a round to see a host's record again. |
| `unmeasured-hosts.json` / `.md` | Why each host the reliability audit could not measure was unmeasurable. Written by `scripts/analysis/classify-unmeasured.py`. |
| `adguard-https-exclusions-banks-live-review.json` / `.md` | DNS/HTTP evidence for one broad source import, for triage. Written by `scripts/sources/review-source-live.py`. |


## Why the raw files are committed

Two reasons, and the second is the one that matters.

**A review can check a decision without trusting the tool.** "Why is
`brightcove.net` `video`?" is answerable by reading `harvest-summary.json` and
the rule that matched it — not by re-running something and trusting the output.

**The upstream lists change.** They are third-party files that can be edited or
disappear. Without a committed copy, a rule written from what a source said
last month cannot be justified next year, because nobody can see what it said.
See [`../docs/SOURCES.md`](../docs/SOURCES.md) on why a published figure is
only valid together with the source it was measured against.

## Offline

Every fetch is cached here, so the whole pipeline re-runs with no network and
the same result:

```sh
python3 scripts/sources/harvest.py --offline
python3 scripts/sources/merge.py evidence/harvested-categories.json --dry-run
```

This is how a change to `rules.json` gets checked without touching the
network, and it is why the cached copies are committed rather than ignored.