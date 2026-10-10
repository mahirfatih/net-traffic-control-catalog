# evidence

What the harvest fetched, and what it concluded — kept so a claim can be
checked without re-downloading anything.

Nothing here is hand-written. `scripts/harvest.py` writes it all.

| File | What it is |
| :--- | :--- |
| `anudeepnd-<id>.txt` | The raw source file exactly as downloaded, comments and all. |
| `harvest-summary.json` | What the last run did: which hosts it categorised, which were already covered, which were dropped **and why**, and which still need a decision. |
| `harvested-categories.json` | The proposed `{host: category}` mapping, ready for `merge.py`. Gitignored — regenerate it with `python3 scripts/harvest.py`. |
| `probes.json` | Optional. Answers from `scripts/probe.py`, if an API key is configured. |

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
python3 scripts/harvest.py --offline
python3 scripts/merge.py evidence/harvested-categories.json --dry-run
```

This is how a change to `rules.json` gets checked without touching the
network, and it is why the cached copies are committed rather than ignored.