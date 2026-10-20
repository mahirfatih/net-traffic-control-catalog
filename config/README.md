# config

Build-time configuration. These files are **not** public API — they are internal
build-time contracts consumed by the generator, validator, and harvest scripts.
The public artifacts are `catalog.json` and `manifest.json` at the repository
root.

| File | Purpose |
| :--- | :--- |
| `schema.json` | JSON Schema for `catalog.json`. Validated by `generate.py` and `validate.py`. Bumped by `bump-version.sh` when the shape changes. |
| `sources.json` | Source registry. Lists every external list the harvest may draw on, with its licence and `allowed` verdict. The licence gate (`scripts/sources/sources.py`) refuses a blocked licence before fetching. |
| `rules.json` | Category rules and overrides. `drop.override` (per-host human decisions) and `drop.hosts` (removal ledger). `harvest.py` applies rules; `overrides.py` manages them. |

These files are **not** shipped to consumers — only `catalog.json` and `manifest.json`
are published. They live here so the build scripts have a single, versioned
location for the contracts they enforce.
