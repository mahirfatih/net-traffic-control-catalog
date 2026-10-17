# scripts/checks

The repository's static checks. `check-docs-fresh.mjs` catches documentation
drift — broken links, renamed scripts, stale counts, a licence verdict that
contradicts itself, any figure quoted from the reliability audit that
`docs/analysis/out/matrix-data.json` does not agree with, and a count in the
README's category treemap that `catalog.json` no longer has. It also checks the
sweep evidence: every seed host must appear in every complete round of
`evidence/dead-domain-sweep.json` and `evidence/live-sweep.json`, because the
sweeps probe the seeds and a host added since the last run leaves the evidence
unable to speak for the catalog. No network, no build. Run it (and
`test/test.sh`) before pushing.

See [`../README.md`](../README.md).
