# release

How the catalog is shipped — the tag a consumer pins to, and the manifest and
checksum that prove they got the tagged bytes. Each folder answers one question;
this one answers "how do I ship it".

The catalog and its format version move separately: `version` changes only on a
breaking shape, the data on every regenerate. A tag freezes both.

## The release path

Releases are **manual**. Nothing runs on a push or a tag; a maintainer starts
[`../../.github/workflows/release.yml`](../../.github/workflows/release.yml) from
the Actions tab, gives it a tag name, and leaves `publish` false to rehearse the
whole path — checks, restore, manifest, notes — before setting it true to create
the tag and the release. The workflow attaches:

- `catalog.json` — the plain JSON, no gzip;
- `manifest.json` — the counts, size and SHA-256 of those bytes;
- `catalog.json.sha256` — the checksum `sha256sum -c` verifies.

The steps that build those files by hand are in
[`../../scripts/release/README.md`](../../scripts/release/README.md); the format
they freeze is [`../reference/FORMAT.md`](../reference/FORMAT.md) and the contract
a consumer reads is [`../reference/INTEGRATION.md`](../reference/INTEGRATION.md).

## Regenerating the version

The version is derived, not edited:
[`../../scripts/release/bump-version.sh`](../../scripts/release/bump-version.sh)
rejects zero and backwards bumps. Regenerating `catalog.json` without
[`../../scripts/release/build-manifest.py`](../../scripts/release/build-manifest.py)
fails `./test/test.sh` at step 3c — a manifest that no longer quotes the bytes
beside it is the one thing an integrating application is told to trust.

## What changed, and when

[`../../CHANGELOG.md`](../../CHANGELOG.md) carries the entry that goes with each
release. The full procedure — including the checks that run before a tag is cut —
is in [`../guides/MAINTAINING.md`](../guides/MAINTAINING.md).
