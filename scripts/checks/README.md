# scripts/checks

The repository's static checks. `check-docs-fresh.mjs` catches documentation
drift — broken links, renamed scripts, stale counts, a licence verdict that
contradicts itself, any figure quoted from the reliability audit that
`docs/analysis/out/matrix-data.json` does not agree with, and a count in the
README's category treemap that `catalog.json` no longer has. It also compares the
treemap and pie colours with `reference/category-colors.json` and insists every
catalog category has a colour there. It also checks the
two-way removal ledger: a host that left the seeds must have a
`rules.json → drop.hosts` reason, and a host carrying such a reason must not be
back in `seeds/categories.json`, which would mean a removal undoing itself. And
it checks the
sweep evidence: every seed host must appear in every complete round of
`evidence/dead-domain-sweep.json`, `evidence/live-sweep.json` and
`evidence/registration-verify.json`, because the sweeps probe the seeds and a
host added since the last run leaves the evidence unable to speak for the
catalog. And it checks that `README.tr.md` carries the same generated blocks as
`README.md`, so the Turkish translation cannot drift from the English source.
No network, no build. Run it (and `test/test.sh`) before pushing.

See [`../README.md`](../README.md).
