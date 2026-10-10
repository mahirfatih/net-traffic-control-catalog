# scripts/sources

Bring hosts in from external lists. `sources.py` is the source registry and the
licence gate, `harvest.py` fetches the allowed sources and applies `rules.json`,
and `merge.py` applies harvested categories to the seeds. The seeds stay the
source of truth; a harvest proposes, a rule or a person labels.

Standard library only. See [`../README.md`](../README.md) and
[`../../docs/SOURCES.md`](../../docs/SOURCES.md).
