#!/usr/bin/env bash
#
# Every check this repository has. Nothing here needs a network or a build.
#
#     ./test/test.sh              # everything
#     ./test/test.sh --fast       # skip py_compile over all scripts
#
# The suite is deliberately plain: Python 3 standard library and Node, no
# install step. A data repository's checks should be runnable by anybody who
# opened a pull request.

set -euo pipefail

cd "$(dirname "$0")/.."

FAST=0
for arg in "$@"; do
    case "$arg" in
        --fast) FAST=1 ;;
        -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
        *) echo "unknown option: $arg" >&2; exit 2 ;;
    esac
done

step() { printf '\n\033[1m== %s\033[0m\n' "$1"; }

step "1. Source registry — licences and verdicts"
python3 scripts/sources/sources.py --check

step "2. Seeds parse and use the vocabulary"
python3 - <<'PY'
import importlib.util, os, sys

# The hyphen in the filename is legal on disk but not in an `import` statement.
_spec = importlib.util.spec_from_file_location(
    "catalog_core", "scripts/catalog/catalog-core.py"
)
catalog_core = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(catalog_core)

categories = catalog_core.load("seeds/categories.json")
services = catalog_core.load("seeds/services.json")

bad = {c for c in categories.values() if c not in catalog_core.VOCABULARY}
if bad:
    print("✗ category outside the vocabulary:", ", ".join(sorted(bad)), file=sys.stderr)
    raise SystemExit(1)
bad_hosts = [(h, catalog_core.host_problems(h)) for h in categories]
bad_hosts = [(h, why) for h, why in bad_hosts if why]
if bad_hosts:
    for host, why in bad_hosts:
        print(f"✗ host {host!r} {why}", file=sys.stderr)
    raise SystemExit(1)
if list(categories) != sorted(categories):
    print("✗ seeds/categories.json is not sorted by host", file=sys.stderr)
    raise SystemExit(1)
if os.path.exists("seeds/services.json"):
    keys = [s["key"] for s in services]
    if len(keys) != len(set(keys)):
        print("✗ duplicate service key in seeds/services.json", file=sys.stderr)
        raise SystemExit(1)
print(f"✓ {len(categories)} categories, {len(services)} services, vocabulary clean")
PY

step "2b. Every service domain is a category or carries one"
python3 - <<'PY'
import importlib.util, sys

# The hyphen in the filename is legal on disk but not in an `import` statement.
_spec = importlib.util.spec_from_file_location(
    "catalog_core", "scripts/catalog/catalog-core.py"
)
catalog_core = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(catalog_core)

categories = catalog_core.load("seeds/categories.json")
services = catalog_core.load("seeds/services.json")


def explained(host):
    """The listed name that gives this host its category, or None."""
    parts = host.split(".")
    for index in range(len(parts) - 1):
        ancestor = ".".join(parts[index:])
        if ancestor in categories:
            return ancestor
    return None


orphans = [(d, s["key"]) for s in services for d in s["domains"] if not explained(d)]
if orphans:
    for domain, key in orphans:
        print(f"✗ {domain!r} is in service {key!r} but has no category anywhere",
              file=sys.stderr)
    print("\nThe app would group it under the right product and label it 'other'.",
          file=sys.stderr)
    raise SystemExit(1)
print(f"✓ {sum(len(s['domains']) for s in services)} service domain(s), none unlabelled")
PY

step "3. Was catalog.json hand-edited?"
# This runs *before* the build, because the build overwrites the file and would
# silently repair a hand edit — which is exactly the mistake it should report.
if command -v git >/dev/null 2>&1 && git rev-parse --git-dir >/dev/null 2>&1; then
    if ! git diff --quiet -- catalog.json; then
        echo "✗ catalog.json differs from the committed build output." >&2
        echo "  It is generated. Edit seeds/ and run scripts/catalog/generate.py instead:" >&2
        git --no-pager diff --stat -- catalog.json >&2
        exit 1
    fi
    echo "✓ catalog.json matches the committed build output"
else
    echo "· not a git checkout; skipping"
fi

step "4. Build catalog.json from the seeds"
python3 scripts/catalog/generate.py \
    --categories seeds/categories.json \
    --services seeds/services.json \
    --out catalog.json

step "5. Validate the built catalog"
python3 scripts/catalog/validate.py

step "6. catalog.json is what the seeds say it is"
python3 - <<'PY'
import json, sys

built = json.load(open("catalog.json"))
categories = json.load(open("seeds/categories.json"))
services = json.load(open("seeds/services.json"))

problems = []
if built.get("categories") != categories:
    problems.append("catalog.json categories differ from seeds/categories.json")
if {s["key"]: s["domains"] for s in built.get("services", [])} != \
   {s["key"]: s["domains"] for s in services}:
    problems.append("catalog.json services differ from seeds/services.json")
if built.get("version") != 1:
    problems.append(f"version is {built.get('version')!r}, expected 1")

for problem in problems:
    print(f"✗ {problem}", file=sys.stderr)
if problems:
    raise SystemExit(1)
print("✓ the built file matches its seeds — nobody hand-edited the output")
PY

step "7. Regenerate the documentation and confirm it is current"
python3 scripts/catalog/build-catalog-docs.py
if command -v git >/dev/null 2>&1 && git rev-parse --git-dir >/dev/null 2>&1; then
    if ! git diff --quiet -- docs/CATALOG.md; then
        echo "✗ docs/CATALOG.md changed when regenerated — it was edited by hand" >&2
        git --no-pager diff -- docs/CATALOG.md | head -40
        exit 1
    fi
    echo "✓ docs/CATALOG.md is current"
else
    echo "· not a git checkout; skipping the staleness comparison"
fi

step "8. Documentation describes the files that exist"
node scripts/checks/check-docs-fresh.mjs

step "9. The licence gate refuses, whatever the registry happens to list"
python3 - <<'PY'
import sys
sys.path.insert(0, "scripts/sources")
import sources as registry

# Tested against synthetic records rather than against whatever the registry
# happens to contain: every source in it may one day be allowed, and the gate
# must still hold when that happens. A test that needs a real blocked source
# to exist quietly stops proving anything once they are all gone.
for licence in ("CC-BY-NC-SA-4.0", "CC-BY-NC-4.0", "CC-BY-SA-4.0"):
    claimed = {"id": "synthetic", "license": licence, "allowed": True}
    ok, reason = registry.verdict(claimed)
    assert not ok, f"{licence} must be refused even when claimed allowed"
    assert reason.strip(), f"{licence} was refused with no reason"

permitted = {"id": "synthetic", "license": "MIT", "allowed": True}
assert registry.verdict(permitted)[0], "MIT must be allowed"

for source in registry.load()["sources"]:
    ok, reason = registry.verdict(source)
    if not ok:
        assert reason.strip(), f"{source['id']} is blocked with no reason"
print("✓ 3 blocking licences refused, MIT allowed — the gate does not depend "
      "on a source being present")
PY

step "10. A malformed host is refused, a valid one accepted"
python3 - <<'PY'
import importlib.util, sys

# The hyphen in the filename is legal on disk but not in an `import` statement.
_spec = importlib.util.spec_from_file_location(
    "catalog_core", "scripts/catalog/catalog-core.py"
)
catalog_core = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(catalog_core)

# Each of these is a name the app could never match: it matches a host whole
# and by suffix, with no glob and no IDNA. The validator must refuse all of
# them, or one becomes a silent dead row nobody ever notices.
bad = [
    "*.example.com", "http://example.com", "exa mple.com", "example..com",
    "-bad.com", "bad-.com", "exämple.com", "example.com.", "localhost",
    "example.com/path", "EXAMPLE.com",
]
for host in bad:
    document = {"version": 1, "categories": {host: "ads"}, "services": []}
    if not catalog_core.validate(document):
        print(f"✗ the validator accepted {host!r}", file=sys.stderr)
        raise SystemExit(1)

good = {"version": 1, "categories": {"example.com": "ads", "t.co": "social"},
        "services": []}
problems = catalog_core.validate(good)
if problems:
    print("✗ the validator rejected a valid host:", problems, file=sys.stderr)
    raise SystemExit(1)
print(f"✓ {len(bad)} malformed host(s) refused, a valid one accepted")
PY

step "10.5. Catalog overlap and distribution check"
python3 scripts/catalog/check-overlaps.py

step "10.6. Category consistency guardrails"
python3 scripts/catalog/audit-category-consistency.py

step "10.7. Source import quality guardrails"
python3 scripts/sources/audit-source-import.py

if [ "$FAST" -eq 0 ]; then
    step "11. Every script compiles"
    python3 -m py_compile scripts/*/*.py
    echo "✓ scripts compile"
fi

printf '\n\033[1;32mall checks passed\033[0m\n'
