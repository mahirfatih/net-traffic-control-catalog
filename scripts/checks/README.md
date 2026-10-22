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
`README.md` and the same heading and diagram counts, so the Turkish translation
cannot drift from the English source. And it checks the seeds provenance:
`evidence/seeds-only.json` must be current
(`scripts/catalog/seeds-provenance.py --check`), and the counts `docs/guides/INGEST.md`
and `docs/overview/FOUNDING.md` quote must be the ones it holds. And it checks the review
backlog: `evidence/pending-source-hosts.json` must be current
(`scripts/sources/pending.py --check`), and `docs/guides/NEEDS-REVIEW.md` must quote the
counts it holds.
No network, no build. Run it (and `test/test.sh`) before pushing.

`build-architecture-diagram.mjs` is the one writer here: it regenerates
`docs/diagrams/architecture/architecture.html` from the `architecture-diagram`
skill template and the outline in `docs/architecture/source.json`. Add `--check`
to fail when the committed HTML is stale; `./test/test.sh` runs that check, so
the diagram cannot drift from its outline. Never hand-edit the HTML — the next
build overwrites it.

The template is not part of this repository. The script looks for a vendored
`architecture-diagram-template.html` here, then the installed skill under
`~/.config/opencode/skills/architecture-diagram/`, and honours
`ARCHITECTURE_DIAGRAM_TEMPLATE` as an override. When none is present, `--check`
skips with a note instead of failing, so a run does not depend on a file the
repository does not carry; set the environment variable to enable it.

See [`../README.md`](../README.md).
