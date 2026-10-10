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
python3 scripts/sources.py --check

step "2. Seeds parse and use the vocabulary"
python3 - <<'PY'
import json, sys, os
sys.path.insert(0, "scripts")
import catalog_lib

categories = catalog_lib.load("seeds/categories.json")
services = catalog_lib.load("seeds/services.json")

bad = {c for c in categories.values() if c not in catalog_lib.VOCABULARY}
if bad:
    print("✗ category outside the vocabulary:", ", ".join(sorted(bad)), file=sys.stderr)
    raise SystemExit(1)
bad_hosts = [(h, catalog_lib.host_problems(h)) for h in categories]
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
import json, sys
sys.path.insert(0, "scripts")
import catalog_lib

categories = catalog_lib.load("seeds/categories.json")
services = catalog_lib.load("seeds/services.json")


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
        echo "  It is generated. Edit seeds/ and run scripts/generate.py instead:" >&2
        git --no-pager diff --stat -- catalog.json >&2
        exit 1
    fi
    echo "✓ catalog.json matches the committed build output"
else
    echo "· not a git checkout; skipping"
fi

step "4. Build catalog.json from the seeds"
python3 scripts/generate.py \
    --categories seeds/categories.json \
    --services seeds/services.json \
    --out catalog.json

step "5. Validate the built catalog"
python3 scripts/validate.py

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
python3 scripts/build-catalog-docs.py
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
node scripts/check-docs-fresh.mjs

step "9. A blocked source is refused, not quietly skipped"
python3 - <<'PY'
import sys
sys.path.insert(0, "scripts")
import sources as registry

reg = registry.load()
blocked = [s for s in reg["sources"] if not registry.verdict(s)[0]]
assert blocked, "no blocked source to test — the gate has nothing to prove"

for source in blocked:
    ok, reason = registry.verdict(source)
    assert not ok, f"{source['id']} should be blocked"
    assert reason.strip(), f"{source['id']} is blocked with no reason"
print(f"✓ {len(blocked)} blocked source(s), each with a stated reason")
PY

step "10. A malformed host is refused, a valid one accepted"
python3 - <<'PY'
import sys
sys.path.insert(0, "scripts")
import catalog_lib

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
    if not catalog_lib.validate(document):
        print(f"✗ the validator accepted {host!r}", file=sys.stderr)
        raise SystemExit(1)

good = {"version": 1, "categories": {"example.com": "ads", "t.co": "social"},
        "services": []}
problems = catalog_lib.validate(good)
if problems:
    print("✗ the validator rejected a valid host:", problems, file=sys.stderr)
    raise SystemExit(1)
print(f"✓ {len(bad)} malformed host(s) refused, a valid one accepted")
PY

if [ "$FAST" -eq 0 ]; then
    step "11. Every script compiles"
    python3 -m py_compile scripts/*.py
    echo "✓ scripts compile"
fi

printf '\n\033[1;32mall checks passed\033[0m\n'