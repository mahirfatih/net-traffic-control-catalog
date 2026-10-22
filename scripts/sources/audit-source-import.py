#!/usr/bin/env python3
"""Audit imported source domains against durable quality guardrails.

    python3 scripts/sources/audit-source-import.py
    python3 scripts/sources/audit-source-import.py --source adguard-https-exclusions-banks

The harvest pipeline can prove that a source row matched a rule, but it cannot
prove that the row is a good catalog claim. This script keeps the source-level
checks that should survive future imports: no same-category redundant
subdomains, no known false-positive hosts from broad sources, a reviewable
report for weakly signalled finance names, and a warning when one source owns
more than 40% of a category. See also `scripts/catalog/build-coverage.py`, which
writes the same concentration picture into `docs/reference/COVERAGE.md`.
"""
import argparse
from collections import Counter, defaultdict
import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CATEGORIES = os.path.join(ROOT, "seeds", "categories.json")
SUMMARY = os.path.join(ROOT, "evidence", "harvest-summary.json")
POLICIES = os.path.join(ROOT, "scripts", "sources", "source-policies.py")

_spec = importlib.util.spec_from_file_location("source_policies", POLICIES)
source_policies = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(source_policies)
SOURCE_POLICIES = source_policies.SOURCE_POLICIES


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def ancestor_with_same_category(host, categories):
    category = categories.get(host)
    if not category:
        return None
    parts = host.split(".")
    for index in range(1, len(parts) - 1):
        parent = ".".join(parts[index:])
        if categories.get(parent) == category:
            return parent
    return None


def rows_for_source(summary, source_id):
    return [row for row in summary.get("categorized", []) if row.get("source") == source_id]


def audit_source(source_id, categories, summary):
    policy = SOURCE_POLICIES[source_id]
    expected = policy["expected_category"]
    rows = rows_for_source(summary, source_id)
    harvested_hosts = sorted({row["host"] for row in rows})
    imported_hosts = sorted(host for host in harvested_hosts if categories.get(host) == expected)

    problems = []
    warnings = []

    if not harvested_hosts:
        problems.append(f"{source_id}: no categorized harvest evidence found")

    for host, reason in policy.get("known_false_positives", {}).items():
        if categories.get(host) == expected:
            problems.append(f"{source_id}: known false positive {host!r} is still {expected}: {reason}")

    for host in imported_hosts:
        parent = ancestor_with_same_category(host, categories)
        if parent:
            problems.append(f"{source_id}: {host} is redundant; {parent} already covers {expected}")

    weak_re = policy.get("weak_signal_re")
    weak = [host for host in imported_hosts if weak_re and not weak_re.search(host)]
    tlds = Counter(host.rsplit(".", 1)[-1] for host in imported_hosts)

    if weak:
        warnings.append(
            f"{source_id}: {len(weak)} imported {expected} host(s) have weak lexical finance signals "
            "and should be spot-checked"
        )

    print(f"=== Source import audit: {source_id} ===")
    print(f"Harvest categorized: {len(harvested_hosts)}")
    print(f"Still imported as {expected}: {len(imported_hosts)}")
    print("Top TLDs: " + ", ".join(f".{tld}={count}" for tld, count in tlds.most_common(10)))
    if weak:
        print("Weak-signal sample: " + ", ".join(weak[:30]))
    else:
        print("Weak-signal sample: none")

    return problems, warnings


# A category that takes more than this share of its rows from one harvest source
# inherits that source's blind spots wholesale. The check warns; it does not fail,
# because a founding list legitimately owns a category on day one.
CONCENTRATION_WARN = 0.40

# Known, accepted single-source dependencies, so the warning stays about *new*
# ones. Keyed (category, source).
EXPECTED_CONCENTRATION = {
    ("finance", "adguard-https-exclusions-banks"): "the founding bank list",
}


def audit_concentration(categories, summary):
    """Warn when one harvest source owns more than 40% of a category.

    Counts only rows that are still in the catalog under the category they were
    harvested as — a harvested row that was later dropped is not part of the
    category any more. The report prints every category above the threshold; the
    warning list holds only the ones that are not already known and accepted.
    """
    totals = Counter(categories.values())
    by_category = defaultdict(Counter)
    for row in summary.get("categorized", []):
        if categories.get(row.get("host")) == row.get("category"):
            by_category[row["category"]][row["source"]] += 1

    warnings = []
    print("\n=== Category source concentration ===")
    for category, total in sorted(totals.items()):
        top = by_category.get(category, Counter()).most_common(1)
        if not top:
            continue
        source, count = top[0]
        share = count / total
        if share <= CONCENTRATION_WARN:
            continue
        known = EXPECTED_CONCENTRATION.get((category, source))
        print(f"  {category}: {count}/{total} ({share:.0%}) from {source}"
              + (f" — known: {known}" if known else " — NEW"))
        if not known:
            warnings.append(
                f"{category}: {share:.0%} of the category comes from a single source "
                f"{source!r}; make sure it is not one list's blind spot"
            )
    return warnings


def main(argv):
    parser = argparse.ArgumentParser(description="Audit source import quality guardrails.")
    parser.add_argument("--source", action="append", choices=sorted(SOURCE_POLICIES), help="source id; repeatable")
    args = parser.parse_args(argv[1:])

    categories = load_json(CATEGORIES)
    summary = load_json(SUMMARY)
    chosen = args.source or sorted(SOURCE_POLICIES)

    all_problems = []
    all_warnings = []
    for source_id in chosen:
        problems, warnings = audit_source(source_id, categories, summary)
        all_problems.extend(problems)
        all_warnings.extend(warnings)

    all_warnings.extend(audit_concentration(categories, summary))

    if all_warnings:
        print("\nWarnings:")
        for warning in all_warnings:
            print(f"  ! {warning}")

    if all_problems:
        print("\n✗ source import audit found problem(s):", file=sys.stderr)
        for problem in all_problems:
            print(f"  {problem}", file=sys.stderr)
        return 1

    print("\n✓ source import audit passed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
