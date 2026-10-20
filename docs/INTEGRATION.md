# Integration — for an application that reads this file

The catalog is one JSON file. [`FORMAT.md`](FORMAT.md) says what is *in* it;
this page is the contract for anything that is **not** the iOS app — an Android
app, an extension, a router, a service — covering what to fetch, how to prove the
bytes are intact, and what is guaranteed not to move under you.

## Two addresses

The same file, two different promises:

| You want | URL | Changes? |
| :--- | :--- | :--- |
| Always current | `https://raw.githubusercontent.com/mahirfatih/net-traffic-control-catalog/main/catalog.json` | **Yes** — `main` moves on every regenerate |
| A version you can rely on | `https://raw.githubusercontent.com/mahirfatih/net-traffic-control-catalog/v0.0.1/catalog.json` | **No** — a tag is immutable |

Pin a tag if the consumer must be able to reproduce yesterday's behaviour. Track
`main` if it only ever wants the latest data. Every tag also becomes a GitHub
Release carrying the same `catalog.json`, its `manifest.json` and a
`catalog.json.sha256`.

The file is shipped **plain**: no gzip, no wrapper, no envelope. What you fetch
is exactly what is in the repository.

## The cheap probe: `manifest.json`

Before pulling 232 KB, pull [`manifest.json`](../manifest.json) — about a
kilobyte, sitting next to the catalog at the same address base:

```
https://raw.githubusercontent.com/mahirfatih/net-traffic-control-catalog/main/manifest.json
```

| Field | Type | Meaning |
| :--- | :--- | :--- |
| `manifest_version` | integer | Version of *this* file's shape. Bumped only on a breaking change. |
| `catalog` | string | The file described. Resolved against the address you fetched from. |
| `format_version` | integer | The catalog's `version`. Skip the download if you do not know it. |
| `generated` | string | When the catalog was rebuilt. Informational. |
| `generated_unix` | integer | Unix timestamp of `generated`. |
| `bytes` | integer | Exact size of the catalog, so you can check `Content-Length` too. |
| `sha256` | string | 64 hex characters: the catalog's SHA-256. |
| `hosts` | integer | Entries in `categories`. |
| `services` | integer | Entries in `services`. |

The intended loop:

```text
fetch manifest.json ──► sha256 == last applied? ──► yes ──► done, nothing to do
        │                        │
        │                        no
        ▼                        ▼
  format_version known?      fetch catalog.json
        │                        │
       no ──► refuse, keep       ▼
        └──────────────► sha256 matches? ──► no ──► refuse, keep last good
                                 │
                                yes
                                 ▼
                          validate, then apply
```

A failed or corrupt download must never replace working data. The iOS app
already behaves this way — follow it.

## Prove the bytes

```sh
sha256sum -c catalog.json.sha256      # GNU
shasum -a 256 -c catalog.json.sha256  # macOS
```

Or in one line, from `manifest.json`:

```python
import hashlib, json, urllib.request

manifest = json.load(urllib.request.urlopen(MANIFEST_URL))
payload = urllib.request.urlopen(CATALOG_URL).read()
assert hashlib.sha256(payload).hexdigest() == manifest["sha256"]
assert len(payload) == manifest["bytes"]
```

## What is guaranteed

- **`version` changes only on a breaking shape change.** A field added, removed
  or renamed that a reader must handle — nothing else. It is not a data version:
  the data changes on every regenerate without touching it.
- **`services[].key` is never renumbered or reused.** Cache by it.
- **A category name outside the vocabulary is ignored, not an error.** A reader
  that knows the vocabulary in [`FORMAT.md`](FORMAT.md) can treat an unknown name
  as `other` rather than failing the parse.
- **A host matches by longest suffix**, with the refusal and tie rules in
  [`FORMAT.md`](FORMAT.md). Those rules do not change to suit one consumer.
- **`schema.json`** describes the shipped shape and is kept in step with the
  format version by [`../scripts/release/bump-version.sh`](../scripts/release/bump-version.sh).

## What is not guaranteed

- **Counts and `generated`.** Hosts, services and the category split move on
  every regenerate. That is the data, not the contract — read them from
  `manifest.json` rather than hard-coding them.
- **`main` is a moving target.** Two fetches of the `main` URL can be two
  different datasets. Pin a tag if that matters.
- **Category proportions.** The distribution is a property of what has been
  collected so far; see [`COVERAGE.md`](COVERAGE.md) for how concentrated it is.

## Keeping it honest

`manifest.json` is generated, never edited:

```sh
python3 scripts/release/build-manifest.py           # write it
python3 scripts/release/build-manifest.py --check   # prove it is current
```

`./test/test.sh` runs `--check` as **step 3c**, before the build, so a catalog
regenerated without its manifest fails the suite rather than shipping a
checksum that lies. The release workflow rebuilds the checksum file from the
manifest and publishes both.

To cut a version, see [`MAINTAINING.md`](MAINTAINING.md) and the changelog:
[`../CHANGELOG.md`](../CHANGELOG.md).
