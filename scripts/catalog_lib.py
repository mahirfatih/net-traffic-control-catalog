"""Shared load / validate / write logic for the catalog.

Both `validate.py` and `generate.py` import this, so the rules live in one place
and anything `generate.py` writes is checkable by `validate.py` — a generated
file can never be valid to the writer and invalid to the checker.
"""
import json

# The category vocabulary. This is the contract with the app: a name outside
# this list is ignored on device, so it must fail here instead.
VOCABULARY = {
    "analytics", "ads", "social", "messaging", "cdn", "crash", "video", "music",
    "gaming", "shopping", "search", "news", "email", "encyclopedia", "software",
    "ai", "finance", "government", "health", "transport", "telecom", "travel",
    "education", "sports", "crypto", "dating", "maps", "adult", "gambling",
    "other",
}


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
        "categories": {host: categories[host] for host in sorted(categories)},
        "services": sorted(services, key=lambda s: s["key"]),
    }


def validate(doc):
    """Return a list of problem strings; an empty list means valid."""
    problems = []
    if not isinstance(doc, dict):
        return ["root is not a JSON object"]

    if doc.get("version") != 1:
        problems.append(f"version must be 1 (got {doc.get('version')!r})")

    categories = doc.get("categories")
    if not isinstance(categories, dict):
        problems.append("categories must be an object")
        categories = {}
    else:
        for host, category in categories.items():
            if category not in VOCABULARY:
                problems.append(f"category {category!r} for {host!r} is not in the vocabulary")
            if host != host.lower():
                problems.append(f"host {host!r} is not lowercase")
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
            for domain in domains:
                if not isinstance(domain, str) or not domain:
                    problems.append(f"{key!r} has an empty domain")
                elif domain != domain.lower():
                    problems.append(f"{key!r} domain {domain!r} is not lowercase")

    if not categories and not services:
        problems.append("catalog has no categories and no services")
    return problems


def write(doc, path):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(normalize(doc), handle, ensure_ascii=False, indent=2)
        handle.write("\n")
