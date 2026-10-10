# scripts/checks

The repository's static checks. `check-docs-fresh.mjs` catches documentation
drift — broken links, renamed scripts, stale counts, a licence verdict that
contradicts itself, and any figure quoted from the reliability audit that
`docs/analysis/out/matrix-data.json` does not agree with. No network, no
build. Run it (and `test/test.sh`) before pushing.

See [`../README.md`](../README.md).
