#!/usr/bin/env bash
#
# scripts/release/bump-version.sh — bump the catalog format version.
#
# `catalog.json` carries a single integer `version`. It is the *format* version:
# it changes only when the file's shape breaks compatibility (a field added,
# removed or renamed that the app must handle). It is NOT a data version — the
# data changes on every regenerate without touching it.
#
# The canonical source is `scripts/catalog/generate.py`, which writes the field;
# `scripts/catalog/catalog-core.py` validates it. This script updates every
# checked-in format contract, then regenerates `catalog.json` *and*
# `manifest.json` so the shipped files match — `manifest.json` mirrors the field
# as `formatVersion` and carries the catalog's sha256, so leaving it stale would
# hand a consumer the previous release's checksum. `docs/FORMAT.md` is
# intentionally not rewritten: its example describes the shape, not a
# version-specific release note.
#
# Usage:
#   ./scripts/release/bump-version.sh           # print the current version
#   ./scripts/release/bump-version.sh 2         # set the format version to 2
#
set -euo pipefail

GENERATE="scripts/catalog/generate.py"
CORE="scripts/catalog/catalog-core.py"
SCHEMA="config/schema.json"
TEST="test/test.sh"
CATALOG="catalog.json"
MANIFEST="manifest.json"
BUILD_MANIFEST="scripts/release/build-manifest.py"

usage() {
  sed -n '3,20p' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-1}"
}

case "${1:-}" in
  -h|--help) usage 0 ;;
esac

for f in "$GENERATE" "$CORE" "$SCHEMA" "$TEST" "$CATALOG" "$BUILD_MANIFEST"; do
  if [[ ! -f "$f" ]]; then
    echo "error: $f not found (run from the repo root)" >&2
    exit 1
  fi
done

current="$(python3 -c "import json;print(json.load(open('$CATALOG'))['version'])")"

if [[ -z "${1:-}" ]]; then
  echo "Current catalog format version: $current"
  echo "Next: $0 <new-version>   (changes only on a breaking shape change)"
  exit 0
fi

new="$1"

if ! [[ "$new" =~ ^[1-9][0-9]*$ ]]; then
  echo "error: version must be a positive integer, got '$new'" >&2
  exit 1
fi

if [[ "$new" -eq "$current" ]]; then
  echo "error: version is already $current" >&2
  exit 1
fi

if [[ "$new" -lt "$current" ]]; then
  echo "error: version cannot move backwards ($current -> $new)" >&2
  exit 1
fi

# Portable in-place sed (BSD/macOS vs GNU).
if sed --version >/dev/null 2>&1; then
  SED_INPLACE=(sed -i)
else
  SED_INPLACE=(sed -i '')
fi

# 1. The writer (canonical source):  "version": 1,
write_exp='s/("version": )[0-9]+,/\1'"${new}"',/'
# 2. The validator:  doc.get("version") != 1   and   "version must be 1"
check_exp='s/("version"\)) != [0-9]+/\1 != '"${new}"'/'
must_exp='s/version must be [0-9]+/version must be '"${new}"'/'
# 3. The JSON Schema and test contract. `test.sh` states the same bare
#    comparison in step 6 (`built.get("version") != 1`), so it takes `check_exp`
#    as well as `test_exp`.
schema_exp='s/("const": )[0-9]+/\1'"${new}"'/'
test_exp='s/(expected )[0-9]+/\1'"${new}"'/; s/("version": )[0-9]+/\1'"${new}"'/g'
# 4. The snake_case version fields in generate.py, catalog-core.py, and test.sh
#    format_version tracks the catalog format version; manifest_version tracks
#    the manifest format version (separate, updated only when manifest format changes).
snake_exp='s/("format_version": )[0-9]+/\1'"${new}"'/g; s/("generated_unix": )[0-9]+/\1'"${new}"'/g'

"${SED_INPLACE[@]}" -E "$write_exp" "$GENERATE"
"${SED_INPLACE[@]}" -E "$check_exp" "$CORE"
"${SED_INPLACE[@]}" -E "$must_exp" "$CORE"
"${SED_INPLACE[@]}" -E "$schema_exp" "$SCHEMA"
"${SED_INPLACE[@]}" -E "$check_exp" "$TEST"
"${SED_INPLACE[@]}" -E "$test_exp" "$TEST"
# snake_case fields (format_version, manifest_version, generated_unix)
"${SED_INPLACE[@]}" -E "$snake_exp" "$GENERATE"
"${SED_INPLACE[@]}" -E "$snake_exp" "$CORE"
"${SED_INPLACE[@]}" -E "$snake_exp" "$TEST"

# 4. Regenerate the shipped file from the seeds.
python3 "$GENERATE" \
  --categories seeds/categories.json \
  --services   seeds/services.json \
  --rules      config/rules.json \
  --out        "$CATALOG"

# 5. Re-derive manifest.json from the new bytes. It mirrors this field as
#    `formatVersion` and carries the catalog's sha256 and byte count, so a
#    stale manifest would hand a consumer the previous release's checksum.
python3 "$BUILD_MANIFEST"

echo "Bumped catalog format version: $current -> $new"
echo "Updated generator, validator, schema, test contract and manifest."
echo "Next: update docs/FORMAT.md if the shape changed, then commit."
