# `docs/architecture/` — the architecture diagram's source

This folder holds **one file**: [`source.json`](source.json), the outline that
produces [`../diagrams/architecture/architecture.html`](../diagrams/architecture/architecture.html).

```sh
node scripts/checks/build-architecture-diagram.mjs           # regenerate the HTML
node scripts/checks/build-architecture-diagram.mjs --check   # fail if stale
```

Edit `source.json`, then run the build. The HTML is a generated artifact — never
hand-edit it, because the next build overwrites it. The prose companion is
[`../diagrams/architecture/architecture.md`](../diagrams/architecture/architecture.md),
and `./test/test.sh` runs the `--check` above so the diagram cannot drift from
its outline.
