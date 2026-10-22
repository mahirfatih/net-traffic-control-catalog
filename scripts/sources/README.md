# scripts/sources

Bring hosts in from external lists. `sources.py` is the source registry and the
licence gate, `harvest.py` fetches the allowed sources and applies `rules.json`,
and `merge.py` applies harvested categories to the seeds. The public-institution
harvester is narrower: it reads curated Turkish public-directory pages and uses
only closed suffixes (`bel.tr`, `gov.tr`, `edu.tr`) to propose `government` or
`education` entries. The seeds stay the source of truth; a harvest proposes, a
rule or a person labels.

```sh
python3 scripts/sources/harvest-public-institutions.py --check
python3 scripts/sources/harvest-public-institutions.py --write
```

It refuses to overwrite an existing label, keeps explicit overrides such as
`saglik.gov.tr` → `health`, and skips parked names that the iOS builder excludes
from vendored catalog data.

Standard library only. See [`../README.md`](../README.md) and
[`../../docs/reference/SOURCES.md`](../../docs/reference/SOURCES.md).
