#!/usr/bin/env python3
"""Collect evidence for pending source hosts without changing catalog data.

    python3 scripts/sources/triage-pending.py --limit 100

The output is an operator worksheet. It never assigns a category, edits seeds,
or writes rules. A person must review the title and source context before any
host is promoted into the catalog.
"""
import argparse
import json
import re
import socket
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PENDING = ROOT / "evidence/pending-source-hosts.json"
DEFAULT_OUT = ROOT / "evidence/pending-triage.json"
UA = "net-traffic-control-catalog-pending-triage/1"
TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
TAG = re.compile(r"<[^>]+>")


def clean_title(value):
    return " ".join(TAG.sub(" ", value).split())[:300]


def load_hosts(path=PENDING):
    data = json.loads(path.read_text(encoding="utf-8"))
    hosts = data.get("hosts")
    if not isinstance(hosts, list):
        raise ValueError("pending evidence has no hosts array")
    return hosts


def inspect(item, timeout):
    host = item["host"]
    result = {"host": host, "source": item.get("source", "")}
    try:
        result["addresses"] = sorted({row[4][0] for row in socket.getaddrinfo(host, 443)})
    except OSError as error:
        result["dns_error"] = str(error)
        result["addresses"] = []
    try:
        request = urllib.request.Request(
            f"https://{host}/", headers={"User-Agent": UA, "Accept": "text/html"}
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(512 * 1024).decode("utf-8", "replace")
            result["status"] = response.status
            result["final_url"] = response.geturl()
            match = TITLE.search(body)
            result["title"] = clean_title(match.group(1)) if match else ""
    except (OSError, urllib.error.URLError, ValueError) as error:
        result["http_error"] = str(error)
    return result


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0, help="inspect only the first N hosts")
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv[1:])
    if args.self_test:
        assert clean_title(" <title> A\n  B </title> ") == "A B"
        assert load_hosts(PENDING)
        print("✓ pending triage self-test")
        return 0
    if args.limit < 0:
        parser.error("--limit cannot be negative")
    hosts = load_hosts()
    if args.limit:
        hosts = hosts[:args.limit]
    results = [inspect(item, args.timeout) for item in hosts]
    document = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "count": len(results),
        "results": results,
    }
    Path(args.out).write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"✓ wrote {args.out}: {len(results)} pending host(s) inspected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(__import__("sys").argv))
