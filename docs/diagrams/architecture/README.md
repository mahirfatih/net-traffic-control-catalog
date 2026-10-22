# `docs/diagrams/architecture/`

The generated architecture diagram for the catalog pipeline.

- [`architecture.html`](architecture.html) — the interactive, click-through
  diagram. **Generated** by `scripts/checks/build-architecture-diagram.mjs`.
- [`architecture.md`](architecture.md) — the written companion: what every node
  and flow is, in prose.

The outline the HTML is built from is
[`../../architecture/source.json`](../../architecture/source.json). Edit that,
then run the build; never hand-edit the HTML.

```sh
node scripts/checks/build-architecture-diagram.mjs           # regenerate
node scripts/checks/build-architecture-diagram.mjs --check   # fail if stale
```
