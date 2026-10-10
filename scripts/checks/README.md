# scripts/checks

The repository's static checks. `check-docs-fresh.mjs` catches documentation
drift — broken links, renamed scripts, stale counts, a licence verdict that
contradicts itself. No network, no build. Run it (and `test/test.sh`) before
pushing.

See [`../README.md`](../README.md).
