"""Shared load / validate / write logic for the catalog.

Both `validate.py` and `generate.py` import this, so the rules live in one place
and anything `generate.py` writes is checkable by `validate.py` — a generated
file can never be valid to the writer and invalid to the checker.
"""
import json
import re
import time

# The category vocabulary. This is the contract with the app: a name outside
# this list is ignored on device, so it must fail here instead.
VOCABULARY = {
    "analytics", "ads", "social", "messaging", "cdn", "crash", "video", "music",
    "gaming", "shopping", "search", "news", "email", "encyclopedia", "software",
    "ai", "finance", "government", "health", "transport", "telecom", "travel",
    "education", "sports", "crypto", "dating", "maps", "adult", "gambling",
    "other",
}

# One DNS label: letters, digits and interior hyphens, 1–63 characters.
HOST_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")


def host_problems(host):
    """Why `host` is not a name the app can match; `None` when it is fine.

    The app matches a listed host *whole*, and every subdomain of it by suffix.
    It does not glob, does not decode IDNA, and lowercases nothing on the
    device. So a wildcard (`*.example.com`), a unicode label, a URL, a trailing
    dot or a stray space is a name nothing will ever ask about — it would sit in
    the catalog and never match. Catching that here is the difference between a
    rejected pull request and a silent dead row.
    """
    if not isinstance(host, str) or not host:
        return "is empty"
    if host != host.strip():
        return "has surrounding whitespace"
    if host != host.lower():
        return "is not lowercase"
    if not host.isascii():
        return "is not ASCII (the matcher does not decode IDNA)"
    if len(host) > 253:
        return "is longer than 253 characters"
    labels = host.split(".")
    if len(labels) < 2:
        return "is not qualified (needs at least one dot)"
    for label in labels:
        if not HOST_LABEL.fullmatch(label):
            return f"has an invalid label {label!r}"
    return None


def load(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def normalize(doc):
    """Lowercase hosts, sort categories and services — deterministic output."""
    categories = {
        host.strip().lower(): str(category).strip().lower()
        for host, category in (doc.get("categories") or {}).items()
        if host.strip()
    }
    services = []
    for service in doc.get("services") or []:
        services.append({
            "key": str(service.get("key", "")).strip(),
            "name": str(service.get("name", "")).strip(),
            "domains": [str(d).strip().lower() for d in service.get("domains", []) if str(d).strip()],
        })
    return {
        "version": int(doc.get("version", 1)),
        "generated": str(doc.get("generated", "")),
        "generated_unix": int(doc.get("generated_unix", 0)),
        "categories": {host: categories[host] for host in sorted(categories)},
        "services": sorted(services, key=lambda s: s["key"]),
        "format_version": int(doc.get("format_version", 2)),
        "manifest_version": int(doc.get("manifest_version", 1)),
        "manifest_file": str(doc.get("manifest_file", "manifest.json")),
    }


def validate(doc):
    """Return a list of problem strings; an empty list means valid."""
    problems = []
    if not isinstance(doc, dict):
        return ["root is not a JSON object"]

    if doc.get("version") != 3:
        problems.append(f"version must be 3 (got {doc.get('version')!r})")

    generated = doc.get("generated")
    if generated is not None and (
        not isinstance(generated, str)
        or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", generated)
    ):
        problems.append("generated must be a YYYY-MM-DD date string")

    generated_unix = doc.get("generated_unix")
    if generated_unix is not None and (
        not isinstance(generated_unix, int)
        or generated_unix < 0
    ):
        problems.append("generated_unix must be a non-negative integer")

    fv = doc.get("format_version")
    if fv is not None and (not isinstance(fv, int) or fv < 1):
        problems.append("format_version must be a positive integer")

    mv = doc.get("manifest_version")
    if mv is not None and (not isinstance(mv, int) or mv < 1):
        problems.append("manifest_version must be a positive integer")

    mf = doc.get("manifest_file")
    if mf is not None and (not isinstance(mf, str) or not mf.strip()):
        problems.append("manifest_file must be a non-empty string")

    categories = doc.get("categories")
    if not isinstance(categories, dict):
        problems.append("categories must be an object")
        categories = {}
    else:
        for host, category in categories.items():
            host_problem = host_problems(host)
            if host_problem:
                problems.append(f"host {host!r} {host_problem}")
            if category not in VOCABULARY:
                problems.append(f"category {category!r} for {host!r} is not in the vocabulary")
        if list(categories) != sorted(categories):
            problems.append("categories are not sorted by host")

    services = doc.get("services", [])
    if not isinstance(services, list):
        problems.append("services must be an array")
        services = []
    seen = set()
    for index, service in enumerate(services):
        if not isinstance(service, dict):
            problems.append(f"services[{index}] is not an object")
            continue
        key = service.get("key")
        if not isinstance(key, str) or not key:
            problems.append(f"services[{index}].key is missing")
        elif key in seen:
            problems.append(f"duplicate service key {key!r}")
        else:
            seen.add(key)
        name = service.get("name")
        if not isinstance(name, str) or not name:
            problems.append(f"services[{index}].name is missing")
        domains = service.get("domains")
        if not isinstance(domains, list) or not domains:
            problems.append(f"services[{index}].domains is missing")
        else:
            seen_domains = set()
            for domain in domains:
                domain_problem = host_problems(domain)
                if domain_problem:
                    problems.append(f"{key!r} domain {domain!r} {domain_problem}")
                if domain in seen_domains:
                    problems.append(f"{key!r} lists {domain!r} more than once")
                seen_domains.add(domain)

    if not categories and not services:
        problems.append("catalog has no categories and no services")
    return problems


def validate_hand_added(doc, hosts):
    """Validate `seeds/hand-added.json`: door 3's per-host who/when/why.

    `hosts` is the set of hosts already in `seeds/categories.json`. A record here
    names a host a person added by hand, so every field a future reader needs is
    mandatory — a record with no `reason` is exactly the gap this file exists to
    close. Returns problem strings, as `validate` does.
    """
    problems = []
    if not isinstance(doc, dict):
        return ["root is not a JSON object"]

    added = doc.get("added")
    if not isinstance(added, dict):
        return ["added must be an object mapping host to its record"]

    for host, record in added.items():
        host_problem = host_problems(host)
        if host_problem:
            problems.append(f"hand-added host {host!r} {host_problem}")
        if host not in hosts:
            problems.append(
                f"hand-added host {host!r} is not in seeds/categories.json — "
                "add it there first; this file only records who added it"
            )
        if not isinstance(record, dict):
            problems.append(f"hand-added record for {host!r} is not an object")
            continue
        for field in ("by", "at", "reason"):
            value = record.get(field)
            if not isinstance(value, str) or not value.strip():
                problems.append(f"hand-added host {host!r} has no {field!r}")
        at = record.get("at")
        if isinstance(at, str) and at.strip() and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", at):
            problems.append(f"hand-added host {host!r} has an invalid 'at' date")
        unexpected = set(record) - {"by", "at", "reason"}
        if unexpected:
            problems.append(
                f"hand-added host {host!r} has unknown field(s): {', '.join(sorted(unexpected))}"
            )
    return problems


def write(doc, path):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(normalize(doc), handle, ensure_ascii=False, indent=2)
        handle.write("\n")
