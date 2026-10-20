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
# checked-in format contract, then regenerates `catalog.json` so the shipped
# file matches. `docs/FORMAT.md` is intentionally not rewritten: its example
# describes the shape, not a version-specific release note.
#
# Usage:
#   ./scripts/release/bump-version.sh           # print the current version
#   ./scripts/release/bump-version.sh 2         # set the format version to 2
#
set -euo pipefail

GENERATE="scripts/catalog/generate.py"
CORE="scripts/catalog/catalog-core.py"
SCHEMA="schema.json"
TEST="test/test.sh"
CATALOG="catalog.json"

usage() {
  sed -n '3,20p' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-1}"
}

case "${1:-}" in
  -h|--help) usage 0 ;;
esac

for f in "$GENERATE" "$CORE" "$SCHEMA" "$TEST" "$CATALOG"; do
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
# 3. The JSON Schema and test contract.
schema_exp='s/("const": )[0-9]+/\1'"${new}"'/'
test_exp='s/(expected )[0-9]+/\1'"${new}"'/; s/("version": )[0-9]+/\1'"${new}"'/g'

"${SED_INPLACE[@]}" -E "$write_exp" "$GENERATE"
"${SED_INPLACE[@]}" -E "$check_exp" "$CORE"
"${SED_INPLACE[@]}" -E "$must_exp" "$CORE"
"${SED_INPLACE[@]}" -E "$schema_exp" "$SCHEMA"
"${SED_INPLACE[@]}" -E "$test_exp" "$TEST"

# 4. Regenerate the shipped file from the seeds.
python3 "$GENERATE" \
  --categories seeds/categories.json \
  --services   seeds/services.json \
  --rules      rules.json \
  --out        "$CATALOG"

echo "Bumped catalog format version: $current -> $new"
echo "Updated generator, validator, schema and test contract."
echo "Next: update docs/FORMAT.md if the shape changed, then commit."
