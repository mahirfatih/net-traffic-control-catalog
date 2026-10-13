#!/usr/bin/env python3
"""Audit imported source domains against durable quality guardrails.

    python3 scripts/sources/audit-source-import.py
    python3 scripts/sources/audit-source-import.py --source adguard-https-exclusions-banks

The harvest pipeline can prove that a source row matched a rule, but it cannot
prove that the row is a good catalog claim. This script keeps the source-level
checks that should survive future imports: no same-category redundant
subdomains, no known false-positive hosts from broad sources, and a reviewable
report for weakly signalled finance names.
"""
import argparse
from collections import Counter
import json
import os
import re
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CATEGORIES = os.path.join(ROOT, "seeds", "categories.json")
SUMMARY = os.path.join(ROOT, "evidence", "harvest-summary.json")


SOURCE_POLICIES = {
    "adguard-https-exclusions-banks": {
        "expected_category": "finance",
        "known_false_positives": {
            "qantas.com": "airline/travel domain; not a finance service",
        },
        "weak_signal_re": re.compile(
            r"(bank|banc|banq|banque|banka|banco|banken|banking|credit|cred|"
            r"financ|pay|pago|wallet|card|cash|loan|invest|broker|trade|"
            r"securit|capital|asset|wealth|fund|mortgage|insurance|insur|"
            r"lease|leasing|union|sparkasse|raiffeisen|volksbank|voba|"
            r"vrbank|ziraat|akbank|alfa|hsbc|ing|seb|dbs|ubs|visa|"
            r"mastercard|amex|paypal|stripe|adyen|skrill|venmo|westernunion|"
            r"alipay|klarna|revolut|wise|monzo|n26|bbva|santander|barclays|"
            r"lloyds|natwest|citi|chase|wellsfargo|fidelity|vanguard|"
            r"robinhood|3ds|3dsecure|acs)",
            re.IGNORECASE,
        ),
    }
}


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
