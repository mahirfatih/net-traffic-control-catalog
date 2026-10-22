# `docs/diagrams/` — generated diagram output

Every subfolder here holds a **generated** diagram: the interactive HTML plus its
written companion. Both come out of a build, so edit the source outline and
re-run the builder — never hand-edit the HTML.

This repository has **one** diagram set:

- [`architecture/`](architecture) — the click-through diagram of the catalog
  pipeline. Generated from
  [`../architecture/source.json`](../architecture/source.json) by
  [`../../scripts/checks/build-architecture-diagram.mjs`](../../scripts/checks/build-architecture-diagram.mjs),
  which fills the `architecture-diagram` skill template. `./test/test.sh` runs the
  builder's `--check`, so the committed HTML cannot drift from the outline.

The outline is the source of truth and lives in
[`../architecture/`](../architecture/), **not** here — nothing under
`docs/diagrams/` is a diagram spec. There is no Archify set in this repository.
