#!/usr/bin/env python3
"""Collect live evidence for a source import without editing catalog data.

    python3 scripts/sources/review-source-live.py \
      --source adguard-https-exclusions-banks \
      --only weak --limit 200

This script is intentionally *not* part of CI: it uses DNS and HTTP. It writes a
JSON evidence file and a Markdown triage table so a broad import can be reviewed
without hand-checking thousands of hosts one by one.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
import html
import importlib.util
import json
import os
import socket
import ssl
import sys
import time
import urllib.error
import urllib.request


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CATEGORIES = os.path.join(ROOT, "seeds", "categories.json")
SUMMARY = os.path.join(ROOT, "evidence", "harvest-summary.json")
EVIDENCE = os.path.join(ROOT, "evidence")
POLICIES = os.path.join(ROOT, "scripts", "sources", "source-policies.py")
USER_AGENT = "net-traffic-control-catalog/1.0 (source live review)"

_spec = importlib.util.spec_from_file_location("source_policies", POLICIES)
source_policies = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(source_policies)
SOURCE_POLICIES = source_policies.SOURCE_POLICIES


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def source_hosts(source_id, categories, summary, only, limit):
    policy = SOURCE_POLICIES[source_id]
    expected = policy["expected_category"]
    weak_re = policy.get("weak_signal_re")
    rows = [row for row in summary.get("categorized", []) if row.get("source") == source_id]
    hosts = sorted({row["host"] for row in rows if categories.get(row["host"]) == expected})
    if only == "weak" and weak_re:
        hosts = [host for host in hosts if not weak_re.search(host)]
    elif only == "strong" and weak_re:
        hosts = [host for host in hosts if weak_re.search(host)]
    if limit:
        hosts = hosts[:limit]
    return hosts


def resolve(host, timeout):
    old_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(timeout)
    try:
        addresses = sorted({item[4][0] for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)})
        return addresses, None
    except OSError as error:
        return [], str(error)
    finally:
        socket.setdefaulttimeout(old_timeout)


def fetch_url(url, timeout):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler())
        with opener.open(request, timeout=timeout) as response:
            raw = response.read(120_000)
            text = raw.decode("utf-8", "replace")
            return {
                "ok": True,
                "url": response.geturl(),
                "status": response.status,
                "content_type": response.headers.get("content-type", ""),
                "text": text,
                "error": None,
            }
    except urllib.error.HTTPError as error:
        # 401/403 from banking sites is still useful liveness evidence.
        return {
            "ok": 200 <= error.code < 500,
            "url": error.geturl(),
            "status": error.code,
            "content_type": error.headers.get("content-type", "") if error.headers else "",
            "text": "",
            "error": str(error),
        }
    except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError) as error:
        return {"ok": False, "url": url, "status": None, "content_type": "", "text": "", "error": str(error)}


def title_from(text):
    lower = text.lower()
    start = lower.find("<title")
    if start == -1:
        return ""
    start = lower.find(">", start)
    end = lower.find("</title>", start)
    if start == -1 or end == -1:
        return ""
    return " ".join(html.unescape(text[start + 1:end]).split())[:160]


def classify(host, policy, dns_addresses, dns_error, responses):
    weak_re = policy.get("weak_signal_re")
    positive_re = policy.get("page_positive_re")
    negative_re = policy.get("page_negative_re")

    score = 0
    reasons = []
    if weak_re and weak_re.search(host):
        score += 2
        reasons.append("domain-name finance signal")
    if dns_addresses:
        score += 1
        reasons.append("DNS resolves")
    live = [r for r in responses if r.get("ok")]
    if live:
        score += 1
        reasons.append("HTTP(S) live")

    text = "\n".join(r.get("text") or "" for r in responses)[:240_000]
    title = title_from(text)
    if positive_re and positive_re.search(text):
        score += 3
        reasons.append("page finance terms")
    if negative_re and negative_re.search(text) and not (positive_re and positive_re.search(text)):
        score -= 3
        reasons.append("page non-finance terms")
    if not dns_addresses and not live:
        score -= 2
        reasons.append(f"not live: {dns_error or 'no response'}")

    if score >= 5:
        decision = "keep"
    elif score <= 0:
        decision = "drop-review"
    else:
        decision = "review"
    return decision, score, reasons, title


def review_one(host, policy, timeout):
    dns_addresses, dns_error = resolve(host, timeout)
    responses = []
    for scheme in ("https", "http"):
        response = fetch_url(f"{scheme}://{host}/", timeout)
        responses.append({k: v for k, v in response.items() if k != "text"})
        if response.get("text"):
            responses[-1]["_text_for_scoring"] = response["text"]
    scoring_responses = []
    for response in responses:
        scoring = dict(response)
        scoring["text"] = scoring.pop("_text_for_scoring", "")
        scoring_responses.append(scoring)
    decision, score, reasons, title = classify(host, policy, dns_addresses, dns_error, scoring_responses)
    for response in responses:
        response.pop("_text_for_scoring", None)
    return {
        "host": host,
        "decision": decision,
        "score": score,
        "reasons": reasons,
        "title": title,
        "dns_addresses": dns_addresses[:8],
        "dns_error": dns_error,
        "responses": responses,
    }


def write_markdown(path, source_id, results):
    counts = {}
    for row in results:
        counts[row["decision"]] = counts.get(row["decision"], 0) + 1
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(f"# Live source review: `{source_id}`\n\n")
        handle.write(f"Generated: {date.today().isoformat()}\n\n")
        handle.write("## Summary\n\n")
        for decision, count in sorted(counts.items()):
            handle.write(f"- `{decision}`: {count}\n")
        handle.write("\n## Results\n\n")
        handle.write("| Decision | Score | Host | Evidence | Title |\n")
        handle.write("| :--- | ---: | :--- | :--- | :--- |\n")
        for row in sorted(results, key=lambda r: (r["decision"], r["score"], r["host"])):
            evidence = "; ".join(row["reasons"])
            title = (row.get("title") or "").replace("|", "\\|")
            handle.write(f"| `{row['decision']}` | {row['score']} | `{row['host']}` | {evidence} | {title} |\n")


def main(argv):
    parser = argparse.ArgumentParser(description="Live-review imported source hosts.")
    parser.add_argument("--source", required=True, choices=sorted(SOURCE_POLICIES))
    parser.add_argument("--only", choices=("all", "weak", "strong"), default="weak")
    parser.add_argument("--limit", type=int, default=200, help="maximum hosts to review; 0 means no limit")
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--out", help="JSON output path")
    args = parser.parse_args(argv[1:])

    categories = load_json(CATEGORIES)
    summary = load_json(SUMMARY)
    policy = SOURCE_POLICIES[args.source]
    limit = None if args.limit == 0 else args.limit
    hosts = source_hosts(args.source, categories, summary, args.only, limit)
    if not hosts:
        print("no hosts matched review selection")
        return 0

    print(f"reviewing {len(hosts)} host(s) from {args.source} ({args.only})")
    started = time.time()
    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(review_one, host, policy, args.timeout): host for host in hosts}
        for future in as_completed(futures):
            row = future.result()
            results.append(row)
            print(f"{row['decision']:11} {row['score']:>2} {row['host']}")

    results.sort(key=lambda row: row["host"])
    out = args.out or os.path.join(EVIDENCE, f"{args.source}-live-review.json")
    md = os.path.splitext(out)[0] + ".md"
    payload = {
        "generated": date.today().isoformat(),
        "source": args.source,
        "selection": args.only,
        "count": len(results),
        "elapsed_seconds": round(time.time() - started, 2),
        "results": results,
    }
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    write_markdown(md, args.source, results)
    print(f"\n✓ wrote {os.path.relpath(out, ROOT)}")
    print(f"✓ wrote {os.path.relpath(md, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
