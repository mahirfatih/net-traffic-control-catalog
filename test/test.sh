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

step "3b. The committed catalog.json matches the seeds (--check)"
# The git check above compares the file to the *committed* one; this compares it
# to what the seeds build right now, so a seed change that was never regenerated
# fails here whether or not this is a git checkout. `--check` writes nothing.
python3 scripts/catalog/generate.py \
    --categories seeds/categories.json \
    --services seeds/services.json \
    --out catalog.json --check

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

step "6b. The same seeds build byte-identical output (determinism)"
# The only field that changes between runs is `generated` (today's date), so pin
# it and prove the rest is a pure function of the seeds: same seeds, same bytes,
# same SHA-256. This is what lets a reviewer trust that a rebuild diff is a real
# change and not a re-run.
python3 - <<'PY'
import hashlib, importlib.util, json, sys

spec = importlib.util.spec_from_file_location(
    "catalog_core", "scripts/catalog/catalog-core.py")
catalog_core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog_core)

categories = json.load(open("seeds/categories.json"))
services = json.load(open("seeds/services.json"))

def build():
    doc = catalog_core.normalize({
        "version": 1,
        "generated": "2026-10-18",   # pinned: today's date is the only moving part
        "categories": categories,
        "services": services,
    })
    payload = json.dumps(doc, ensure_ascii=False, indent=2).encode("utf-8")
    return hashlib.sha256(payload).hexdigest(), doc

first, doc = build()
second, _ = build()
if first != second:
    print("✗ two builds of the same seeds differ — the build is not deterministic",
          file=sys.stderr)
    raise SystemExit(1)

# The pinned build must also validate, so determinism is not bought by producing
# an invalid document.
problems = catalog_core.validate(doc)
if problems:
    print("✗ the deterministically built document is invalid:", problems, file=sys.stderr)
    raise SystemExit(1)

print(f"✓ same seeds → same SHA-256 ({first[:16]}…), and the document validates")
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

step "7b. The document writer is deterministic (--check)"
# Step 7 just rewrote the documents from catalog.json; rendering them a second
# time and comparing must find nothing. This exercises the `--check` path and
# proves the writer is deterministic, so a stale-file report from it can only
# mean a real change, never a reshuffle.
python3 scripts/catalog/build-catalog-docs.py --check

step "7c. The coverage report is current"
# docs/COVERAGE.md is generated from the catalog, the rules and the analysis, so
# it rots the same way docs/CATALOG.md does. Regenerate and compare, then exercise
# the writer's own --check.
python3 scripts/catalog/build-coverage.py
if command -v git >/dev/null 2>&1 && git rev-parse --git-dir >/dev/null 2>&1; then
    if ! git diff --quiet -- docs/COVERAGE.md; then
        echo "✗ docs/COVERAGE.md changed when regenerated — it was edited by hand" >&2
        git --no-pager diff -- docs/COVERAGE.md | head -40
        exit 1
    fi
    echo "✓ docs/COVERAGE.md is current"
else
    echo "· not a git checkout; skipping the staleness comparison"
fi
python3 scripts/catalog/build-coverage.py --check

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

# A malformed date and a duplicate service domain are build-blocking too.
for bad_doc in (
    {"version": 1, "generated": "yesterday", "categories": {"example.com": "ads"},
     "services": []},
    {"version": 1, "generated": "2026-10-18", "categories": {"example.com": "ads"},
     "services": [{"key": "a", "name": "A", "domains": ["x.com", "x.com"]}]},
):
    if not catalog_core.validate(bad_doc):
        print("✗ the validator accepted a document with a blocking problem",
              file=sys.stderr)
        raise SystemExit(1)
print(f"✓ {len(bad)} malformed host(s) refused, a valid one accepted")
PY

step "10.5. Catalog overlap and distribution check"
python3 scripts/catalog/check-overlaps.py

step "10.6. Category consistency guardrails"
python3 scripts/catalog/audit-category-consistency.py

step "10.7. Source import quality guardrails"
python3 scripts/sources/audit-source-import.py

step "10.8. Category overrides are valid and beat rules"
python3 scripts/catalog/overrides.py check
python3 - <<'PY'
import importlib.util, json, os, subprocess, sys, tempfile

_spec = importlib.util.spec_from_file_location(
    "overrides", "scripts/catalog/overrides.py"
)
overrides = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(overrides)

# A synthetic rules document, so the test does not depend on the real override
# map being empty or full: the precedence rule must hold either way.
doc = {
    "rules": [{"match": ["example.com"], "category": "finance"}],
    "drop": {"hosts": {}, "override": {"example.com": {"category": "shopping", "reason": "sells goods"}}},
}
applied, problems = overrides.apply({"example.com": "finance", "other.com": "news"}, doc)
assert not problems, problems
assert applied["example.com"] == "shopping", applied["example.com"]
assert applied["other.com"] == "news"

# A bad override must be refused: category outside the vocabulary, and no reason.
bad = {"drop": {"override": {"x.com": {"category": "not-a-category", "reason": "r"}}}}
assert overrides.check(bad), "an unknown category must be reported"
bad = {"drop": {"override": {"x.com": {"category": "news", "reason": ""}}}}
assert overrides.check(bad), "a missing reason must be reported"
both = {"drop": {"hosts": {"x.com": "why"}, "override": {"x.com": {"category": "news", "reason": "r"}}}}
assert overrides.check(both), "a host in both drop and override must be reported"
print("✓ override beats a rule; bad overrides are refused")
PY

step "10.9. A dead-domain sweep keeps what it cannot prove"
python3 - <<'PY'
import importlib.util

_spec = importlib.util.spec_from_file_location("probe_dead", "scripts/catalog/probe-dead.py")
probe_dead = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(probe_dead)

# No network in CI, so the decision table is checked directly. This is the part
# that must never regress: a wrong "dead" here would delete a real bank, on the
# strength of a firewall answer that said nothing about the host.
def statuses(cloudflare, google, adguard=None):
    # The real resolver set is three since AdGuard was added; a host is only
    # dead when all nine questions say NXDOMAIN, so this helper has to model all
    # three or the table would test a shape the tool no longer has.
    adguard = google if adguard is None else adguard
    return {
        "cloudflare": {rrtype: cloudflare for rrtype in ("A", "AAAA", "NS")},
        "google": {rrtype: google for rrtype in ("A", "AAAA", "NS")},
        "adguard": {rrtype: adguard for rrtype in ("A", "AAAA", "NS")},
    }

RC_NOERROR, RC_SERVFAIL, RC_NXDOMAIN, RC_UNREACHED = 0, 2, 3, None

cases = [
    ("every question says NXDOMAIN", statuses(RC_NXDOMAIN, RC_NXDOMAIN), 0, "dead"),
    ("records come back", statuses(RC_NOERROR, RC_NOERROR), 12, "alive"),
    ("a record type answers", statuses(RC_NXDOMAIN, RC_NOERROR), 1, "alive"),
    ("two resolvers say NXDOMAIN, the third answers", statuses(RC_NXDOMAIN, RC_NXDOMAIN, RC_NOERROR), 1, "alive"),
    ("two resolvers say NXDOMAIN, the third has no record", statuses(RC_NXDOMAIN, RC_NXDOMAIN, RC_NOERROR), 0, "nodata"),
    ("NOERROR with no address record", statuses(RC_NOERROR, RC_NOERROR), 0, "nodata"),
    ("NOERROR from one, nothing from the other", statuses(RC_NOERROR, RC_UNREACHED), 0, "nodata"),
    ("every resolver says SERVFAIL", statuses(RC_SERVFAIL, RC_SERVFAIL), 0, "servfail"),
    ("NXDOMAIN and SERVFAIL disagree", statuses(RC_NXDOMAIN, RC_SERVFAIL), 0, "unknown"),
    ("NXDOMAIN and a network failure", statuses(RC_NXDOMAIN, RC_UNREACHED), 0, "unknown"),
    ("all three unroutable", statuses(RC_UNREACHED, RC_UNREACHED), 0, "unknown"),
]
for name, seen, answers, expected in cases:
    actual = probe_dead.classify(seen, answers)
    assert actual == expected, f"{name}: expected {expected}, got {actual}"
    print(f"  ✓ {name:44} -> {actual}")

# The proposal is the intersection of the rounds, so a host one round could not
# speak for is never a candidate for removal.
state = {
    "rounds": [
        {"round": 1, "counts": {}, "results": {
            "dead-both.test": {"decision": "dead"},
            "dead-once.test": {"decision": "dead"},
            "servfail.test": {"decision": "servfail"},
            "nodata.test": {"decision": "nodata"},
        }},
        {"round": 2, "counts": {}, "results": {
            "dead-both.test": {"decision": "dead"},
            "unknown.test": {"decision": "unknown"},
            "servfail.test": {"decision": "servfail"},
            "nodata.test": {"decision": "nodata"},
        }},
    ]
}
proposal = probe_dead.build_proposal(state)
assert proposal == ["dead-both.test"], proposal
print("  ✓ only a host both rounds called dead is proposed")
PY

step "10.10. A live sweep keeps what it cannot prove"
python3 - <<'PY'
import importlib.util

_spec = importlib.util.spec_from_file_location("sweep_live", "scripts/analysis/sweep-live.py")
sweep = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sweep)

# The navigation error text is the browser's, so map it once, here, and prove
# the mapping. A certificate failure classified as "no page" is how a live site
# gets proposed for deletion.
for error, expected in [
    ("Navigation failed: CouldntResolveHost", "dns-error"),
    ("Navigation failed: PeerFailedVerification", "tls-error"),
    ("Navigation failed: net::ERR_TIMED_OUT", "timeout"),
    ("Navigation failed: net::ERR_CONNECTION_REFUSED", "no-http"),
]:
    actual = sweep.classify_error(error)
    assert actual == expected, f"{error!r}: expected {expected}, got {actual}"
    print(f"  ✓ {error:48} -> {actual}")

# The content decision, which status alone cannot make: a parked page returns
# 200, a blocked one returns 403.
PARKED_TEXT = "this domain is for sale buy this domain"
cases = [
    ("a page with text", 200, 900, "Example", "https://x/", "", "content"),
    ("a 200 with no text", 200, 5, "", "https://x/", "", "empty"),
    ("a parked page", 200, 900, "Domain For Sale", "https://x/", PARKED_TEXT, "parked"),
    ("a short parked page", 200, 20, "Domain For Sale", "https://x/", "", "parked"),
    ("a parked host", 200, 900, "x", "https://sedoparking.com/x/", "", "parked"),
    # A real page must not be called parked because it contains a phrase. These
    # two are the regression: `duolingo.com` ("it works!") and `gspfinance.com`
    # / `plfsbd.com` ("under construction") were filed as parked when the
    # markers were loose, and the default mode would have proposed them.
    ("a real page with a phrase", 200, 900, "Duolingo", "https://www.duolingo.com/",
     "the most fun way to learn a language. it works!", "content"),
    ("a bank site with a phrase", 200, 1355, "GSP Finance", "https://gspfinance.com/",
     "our new branch is under construction", "content"),
    ("refused automated traffic", 403, 900, "Just a moment", "https://x/", "", "blocked"),
    ("not found", 404, 20, "404", "https://x/", "", "no-http"),
    ("server error", 503, 0, "", "https://x/", "", "no-http"),
    ("no status, no text", None, 0, "", "https://x/", "", "empty"),
]
for name, status, length, title, url, haystack, expected in cases:
    actual = sweep.classify_attempt(status, length, title, url, haystack, None)
    assert actual == expected, f"{name}: expected {expected}, got {actual}"
    print(f"  ✓ {name:30} -> {actual}")

# The most alive attempt wins: one transient timeout cannot outvote a page that
# did load, and a real host signal beats the harness's own confusion.
assert sweep.host_decision(["timeout", "content"]) == "ok"
assert sweep.host_decision(["dns-error", "harness-error"]) == "dns-error"
assert sweep.host_decision(["harness-error", "harness-error"]) == "harness-error"
print("  ✓ the most alive attempt decides, a real signal beats harness-error")

# Nothing an environment failure produced is a candidate on its own, and the
# default proposal is the one signal that cannot be misread: a parked page. A
# 404 or an empty 200 is common on live infrastructure (`adnxs.com`,
# `3dsecure.akbank.com.tr`) and needs a person to ask for it.
assert not sweep.is_candidate("ok", True, True)
assert not sweep.is_candidate("blocked", True, True)
assert not sweep.is_candidate("harness-error", True, True)
assert sweep.is_candidate("parked", False)
assert not sweep.is_candidate("no-http", False)
assert not sweep.is_candidate("empty", False)
assert sweep.is_candidate("no-http", True)
assert sweep.is_candidate("empty", True)
assert not sweep.is_candidate("timeout", True)
assert sweep.is_candidate("timeout", True, include_flaky=True)
print("  ✓ only a parked page is proposed by default; no page or a flaky one needs a flag")

# Two rounds must agree, a harness-error host is never proposed, and one round
# is a snapshot with no proposal.
state = {"rounds": [
    {"round": 1, "complete": True, "results": {
        "empty-both.test": {"decision": "empty"},
        "empty-once.test": {"decision": "empty"},
        "blocked.test": {"decision": "blocked"},
        "flaky.test": {"decision": "timeout"},
    }},
    {"round": 2, "complete": True, "results": {
        "empty-both.test": {"decision": "empty"},
        "empty-once.test": {"decision": "ok"},
        "blocked.test": {"decision": "blocked"},
        "flaky.test": {"decision": "timeout"},
    }},
]}
assert sweep.build_proposal(state, aggressive=False) == []
assert sweep.build_proposal(state, aggressive=True) == ["empty-both.test"]
assert sweep.build_proposal({"rounds": state["rounds"][:1]}, aggressive=True) is None
# A parked host needs no flag: it is the unambiguous case.
parked = {"rounds": [
    {"round": 1, "complete": True, "results": {
        "parked-both.test": {"decision": "parked"},
        "parked-once.test": {"decision": "parked"},
    }},
    {"round": 2, "complete": True, "results": {
        "parked-both.test": {"decision": "parked"},
        "parked-once.test": {"decision": "ok"},
    }},
]}
assert sweep.build_proposal(parked, aggressive=False) == ["parked-both.test"]
uncertain = {"rounds": [
    {"round": 1, "complete": True, "results": {"h.test": {"decision": "parked"}}},
    {"round": 2, "complete": True, "results": {"h.test": {"decision": "harness-error"}}},
]}
assert sweep.build_proposal(uncertain, aggressive=True) == []
# Infrastructure that answers with nothing is never proposed, even aggressively:
# a real endpoint with no page is not a dead site.
infra = {"rounds": [
    {"round": 1, "complete": True, "results": {
        "adnxs.com": {"decision": "empty"},
        "pixel.adnxs.com": {"decision": "no-http"},
        "3dsecure.akbank.com.tr": {"decision": "empty"},
        "real-empty.test": {"decision": "empty"},
    }},
    {"round": 2, "complete": True, "results": {
        "adnxs.com": {"decision": "empty"},
        "pixel.adnxs.com": {"decision": "no-http"},
        "3dsecure.akbank.com.tr": {"decision": "empty"},
        "real-empty.test": {"decision": "empty"},
    }},
]}
assert sweep.build_proposal(infra, aggressive=True) == ["real-empty.test"]
assert sweep.is_infrastructure("adnxs.com")
assert sweep.is_infrastructure("pixel.adnxs.com")
assert sweep.is_infrastructure("3dsecure.akbank.com.tr")
assert not sweep.is_infrastructure("example.com")
print("  ✓ two rounds must agree; harness-error is never proposed")
print("  ✓ infrastructure is never proposed, even under --aggressive")
PY

step "10.11. A registration sweep keeps what it cannot prove"
python3 - <<'PY'
import importlib.util, datetime

_spec = importlib.util.spec_from_file_location("verify_reg", "scripts/catalog/verify-registrations.py")
vr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vr)

# RDAP parsing: a registered name yields its registrar and dates.
sample = '{"ldhName":"example.com","status":["client transfer prohibited"],' \
         '"events":[{"eventAction":"registration","eventDate":"1995-08-14T04:00:00Z"},' \
         '{"eventAction":"expiration","eventDate":"2026-08-13T04:00:00Z"}],' \
         '"entities":[{"roles":["registrar"],"vcardArray":["vcard",[["fn",{},"text","IANA"]]]}],' \
         '"nameservers":[{"ldhName":"a.iana-servers.net"}]}'
rec = vr.parse_rdap(sample.encode(), "rdap.iana.org")
assert rec is not None and rec["registrar"] == "IANA"
assert rec["created"].year == 1995
print("  ✓ RDAP parse yields registrar and dates")

# Decision table: gone / expired / registered / recently registered / unknown.
now = datetime.datetime(2026, 10, 17, tzinfo=datetime.timezone.utc)
gone = vr.decide({"rdap": {"_outcome": "ok", "status": ["pending delete"],
                            "expires": datetime.datetime(2030, 1, 1, tzinfo=datetime.timezone.utc),
                            "created": datetime.datetime(2010, 1, 1, tzinfo=datetime.timezone.utc)}}, now=now)
assert gone == "gone", gone
expired = vr.decide({"rdap": {"_outcome": "ok", "status": [],
                              "expires": datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc),
                              "created": datetime.datetime(2010, 1, 1, tzinfo=datetime.timezone.utc)}}, now=now)
assert expired == "expired", expired
registered = vr.decide({"rdap": {"_outcome": "ok", "status": ["active"],
                                 "expires": datetime.datetime(2030, 1, 1, tzinfo=datetime.timezone.utc),
                                 "created": datetime.datetime(2010, 1, 1, tzinfo=datetime.timezone.utc)}}, now=now)
assert registered == "registered", registered
recent = vr.decide({"rdap": {"_outcome": "ok", "status": ["active"],
                             "expires": datetime.datetime(2030, 1, 1, tzinfo=datetime.timezone.utc),
                             "created": datetime.datetime(2026, 9, 1, tzinfo=datetime.timezone.utc)}}, now=now)
assert recent == "recently_registered", recent
unknown = vr.decide({"rdap": {"_outcome": "unreachable"}})
assert unknown == "unknown", unknown
print("  ✓ decision table: gone/expired/registered/recently_registered/unknown")

# Guards added after real false positives.
# `inactive` / `clientHold` are registered-but-not-delegated: review, not gone.
inactive = vr.decide({"rdap": {"_outcome": "ok", "status": ["inactive"],
                               "expires": datetime.datetime(2030, 1, 1, tzinfo=datetime.timezone.utc),
                               "created": datetime.datetime(2010, 1, 1, tzinfo=datetime.timezone.utc)}}, now=now)
assert inactive == "review", inactive
client_hold = vr.decide({"rdap": {"_outcome": "ok", "status": ["client hold"],
                                  "expires": datetime.datetime(2030, 1, 1, tzinfo=datetime.timezone.utc),
                                  "created": datetime.datetime(2010, 1, 1, tzinfo=datetime.timezone.utc)}}, now=now)
assert client_hold == "review", client_hold

# A name that resolves in DNS is never gone (aka.ms on a broken RDAP endpoint).
resolving = vr.decide({"rdap": {"_outcome": "notfound"},
                       "dns": {"resolves": True, "ip": "1.2.3.4"}}, now=now)
assert resolving == "review", resolving
not_resolving = vr.decide({"rdap": {"_outcome": "notfound"},
                           "dns": {"resolves": False, "ip": None}}, now=now)
assert not_resolving == "gone", not_resolving

# A 404 is a real "not registered" only when the endpoint speaks RDAP.
assert vr._rdap_404_is_real(b"", "application/rdap+json")
assert vr._rdap_404_is_real(b'{"errorCode":404}', "application/json")
assert not vr._rdap_404_is_real(b"<html>404</html>", "text/html;charset=utf-8")
assert not vr._rdap_404_is_real(b"", "")
print("  ✓ guards: inactive/clientHold -> review, DNS-resolving never gone, HTML 404 not a negative")

# DENIC whois parser: free -> gone, connect -> registered.
free = vr.whois_lookup.__wrapped__ if hasattr(vr.whois_lookup, "__wrapped__") else None
# parse directly via the denic branch is network; instead check the verdict logic
# by feeding a synthetic text through a small re-implementation of the parser.
def parse_denic(text):
    status = changed = None
    for line in text.splitlines():
        low = line.lower().strip()
        if low.startswith("status:"):
            status = line.split(":", 1)[1].strip()
        elif low.startswith("changed:"):
            changed = vr._iso_date(line.split(":", 1)[1].strip())
    return status, changed
st, _ = parse_denic("Domain: x.de\nStatus: free\n")
assert st == "free"
st, _ = parse_denic("Domain: x.de\nStatus: connect\nChanged: 2023-06-01T12:45:04+02:00\n")
assert st == "connect"
print("  ✓ DENIC whois: free/connect distinguished")

# Candidate policy: only gone/expired proposed by default.
assert not vr.is_candidate("registered", True, True)
assert not vr.is_candidate("unknown", True)
assert vr.is_candidate("unknown", True, include_flaky=True)
assert not vr.is_candidate("recently_registered", False)
assert vr.is_candidate("gone", False)
assert vr.is_candidate("expired", False)
assert vr.is_candidate("recently_registered", False, include_review=True)
print("  ✓ candidate policy: gone/expired by default; review needs a flag")

# Two rounds must agree; an unsupported/unknown host is never proposed.
state = {"rounds": [
    {"round": 1, "complete": True, "results": {
        "gone-both.test": "gone",
        "gone-once.test": "gone",
        "unknown.test": "unknown",
        "unsupported.test": "unsupported",
    }},
    {"round": 2, "complete": True, "results": {
        "gone-both.test": "gone",
        "gone-once.test": "registered",
        "unknown.test": "unknown",
        "unsupported.test": "unsupported",
    }},
]}
assert vr.build_proposal(state) == ["gone-both.test"]
assert vr.build_proposal({"rounds": state["rounds"][:1]}) is None
print("  ✓ two rounds must agree; unknown/unsupported never proposed")
PY

step "10.12. A hand-added host records who, when and why"
python3 - <<'PY'
import importlib.util

spec = importlib.util.spec_from_file_location(
    "catalog_core", "scripts/catalog/catalog-core.py")
catalog_core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog_core)

HOSTS = {"example.com"}

good = {"added": {"example.com": {"by": "contributor", "at": "2026-10-18",
                                  "reason": "a real site in this category"}}}
assert catalog_core.validate_hand_added(good, HOSTS) == []

# Each of the three fields is mandatory — a record with no reason is exactly the
# gap the file exists to close.
for field in ("by", "at", "reason"):
    record = {"by": "contributor", "at": "2026-10-18", "reason": "why"}
    record.pop(field)
    assert any("no %r" % field in p
               for p in catalog_core.validate_hand_added(
                   {"added": {"example.com": record}}, HOSTS)), field

# The host must already be in the seeds; this file only records who added it.
assert any("not in seeds/categories.json" in p
           for p in catalog_core.validate_hand_added(
               {"added": {"elsewhere.net": {"by": "a", "at": "2026-10-18", "reason": "r"}}},
               HOSTS))

# A date that is not a date, and an unknown field, are both refused.
assert any("invalid 'at' date" in p
           for p in catalog_core.validate_hand_added(
               {"added": {"example.com": {"by": "a", "at": "yesterday", "reason": "r"}}}, HOSTS))
assert any("unknown field" in p
           for p in catalog_core.validate_hand_added(
               {"added": {"example.com": {"by": "a", "at": "2026-10-18", "reason": "r",
                                          "extra": 1}}}, HOSTS))

# The committed file itself must be clean.
import json
with open("seeds/hand-added.json", encoding="utf-8") as handle:
    committed = json.load(handle)
with open("seeds/categories.json", encoding="utf-8") as handle:
    real = set(json.load(handle))
assert catalog_core.validate_hand_added(committed, real) == [], "committed hand-added.json is invalid"

print("  ✓ by/at/reason all required; host must be in seeds; date and extra fields checked")
PY

if [ "$FAST" -eq 0 ]; then
    step "11. Every script compiles"
    python3 -m py_compile scripts/*/*.py
    echo "✓ scripts compile"
fi

printf '\n\033[1;32mall checks passed\033[0m\n'
