# `docs/diagrams/` — diagrams rendered from JSON specs

Each subfolder holds a diagram and nothing else. The HTML is **generated** from
the `architecture-diagram` skill template plus a JSON outline; the outline lives
in [`../architecture/`](../architecture/). Edit the outline, then run the build —
never hand-edit the HTML.

- [`architecture/`](architecture) — the click-through diagram of the catalog
  pipeline. **Generated** by
  [`../../scripts/checks/build-architecture-diagram.mjs`](../../scripts/checks/build-architecture-diagram.mjs),
  and checked by `./test/test.sh` with `--check`.
