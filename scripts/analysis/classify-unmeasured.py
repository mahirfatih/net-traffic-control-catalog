"""Explain the hosts the reliability audit could not measure.

The audit classifies a host from its homepage text. A fifth of the catalog has
none, and until now that was recorded as one number: "no usable page text". But
that is at least three different things, and conflating them reads as a single
failure when it is three:

  - the host does not answer at all (the network fact the dead-domain sweep
    already covers — DNS resolves, but nothing listens)
  - the host answers with something that is not a page: an API, a redirect, a
    CDN edge, a bare TLS endpoint. No amount of rendering will produce text.
  - the host answers with HTML whose words only exist after JavaScript runs.

Only the first is a dead end. The other two name what a different signal would
have to be — headers, or a renderer — instead of leaving a count nobody can act
on. This records which one each host is, from the response itself.

Standard library only. Not part of `test/test.sh`: it needs the network, and CI
must never depend on the network.

    python3 scripts/analysis/classify-unmeasured.py [--limit N] [--workers 40]
"""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import re
import ssl
import urllib.error
import urllib.request
from datetime import date, datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CATALOG = os.path.join(ROOT, "catalog.json")
PAGES = os.path.join(ROOT, "scripts", "analysis", ".pages")
EVIDENCE = os.path.join(ROOT, "evidence", "unmeasured-hosts.json")
MARKDOWN = os.path.join(ROOT, "evidence", "unmeasured-hosts.md")

USER_AGENT = "net-traffic-control-catalog/1.0 (unmeasured-host audit)"
MIN_TEXT = 100  # the audit's floor, in characters

# The reason a host stayed unmeasured. Ordered from "nothing we can do" to
# "needs a renderer"; the summary prints them in this order.
REASONS = (
    "no-answer",
    "http-error",
    "non-html",
    "empty-body",
    "html-without-text",
    "now-measurable",
    "unreachable",
)


def load_unmeasured():
    """Catalog hosts whose cached page is too short for the audit to use."""
    catalog = json.load(open(CATALOG, encoding="utf-8"))["categories"]
    unmeasured = []
    for host in catalog:
        path = os.path.join(PAGES, f"{host}.txt")
        size = os.path.getsize(path) if os.path.exists(path) else 0
        if size < MIN_TEXT:
            unmeasured.append(host)
    return catalog, unmeasured


_TAG = re.compile(r"<[^>]+>")
_SCRIPT = re.compile(r"<(script|style|noscript)\b[^>]*>.*?</\1>", re.I | re.S)
_WS = re.compile(r"\s+")


def visible_text_length(html):
    """A rough length of the words a browser would show without running JS.

    Deliberately rough: it only has to separate "this page has prose" from
    "this page is an empty shell waiting for a script".
    """
    stripped = _SCRIPT.sub(" ", html)
    return len(_WS.sub(" ", _TAG.sub(" ", stripped)).strip())


def classify(host, timeout=10.0):
    """Fetch a host once and say why its page did or did not yield text."""
    record = {
        "status": None,
        "content_type": None,
        "content_length": None,
        "final_url": None,
        "error": None,
    }
    for url in (f"https://{host}/", f"http://{host}/"):
        request = urllib.request.Request(
            url, headers={"user-agent": USER_AGENT, "accept": "text/html,*/*"}
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read(300_000)
                record["status"] = response.status
                record["content_type"] = (response.headers.get("content-type") or "").split(";")[0]
                record["content_length"] = len(body)
                record["final_url"] = response.url
                text = visible_text_length(body.decode("utf-8", "replace"))
                record["visible_text"] = text
                if not body:
                    record["reason"] = "empty-body"
                elif "html" not in record["content_type"]:
                    record["reason"] = "non-html"
                elif text < MIN_TEXT:
                    record["reason"] = "html-without-text"
                else:
                    record["reason"] = "now-measurable"
                return record
        except urllib.error.HTTPError as error:
            record["status"] = error.code
            record["content_type"] = (error.headers.get("content-type") or "").split(";")[0]
            record["error"] = f"HTTP {error.code}"
            record["reason"] = "http-error"
            # A 4xx/5xx on https may still be a page on http; try the next URL.
            continue
        except (urllib.error.URLError, ssl.SSLError, OSError) as error:
            record["error"] = type(error).__name__
            continue
    record["reason"] = "no-answer" if record["status"] is None else record["reason"]
    return record


def write_markdown(state, catalog):
    rows = state["hosts"]
    counts = state["counts"]
    lines = [
        "# Unmeasured hosts",
        "",
        f"Generated: {state['generated'][:10]}",
        "",
        f"The reliability audit measures {state['measured']} of the catalog's "
        f"{state['total']} hosts. The {state['unmeasured']} below yielded no usable page",
        "text, and this is *why* — a fetch result, not a guess.",
        "",
        "| Reason | Hosts | What it means |",
        "| :--- | ---: | :--- |",
        f"| no-answer | {counts.get('no-answer', 0)} | DNS resolves, nothing answers HTTP |",
        f"| http-error | {counts.get('http-error', 0)} | answers with 4xx/5xx, no page body |",
        f"| non-html | {counts.get('non-html', 0)} | answers, but not with a page |",
        f"| empty-body | {counts.get('empty-body', 0)} | 2xx with an empty body |",
        f"| html-without-text | {counts.get('html-without-text', 0)} | HTML whose words need JavaScript |",
        f"| now-measurable | {counts.get('now-measurable', 0)} | has text now — rerun the audit |",
        "",
    ]
    by_reason = {}
    for host, record in rows.items():
        by_reason.setdefault(record.get("reason", "unreachable"), []).append(host)
    for reason in REASONS:
        hosts = sorted(by_reason.get(reason, []))
        if not hosts:
            continue
        lines += [f"## {reason} — {len(hosts)} host(s)", ""]
        for host in hosts[:60]:
            record = rows[host]
            detail = record.get("content_type") or record.get("error") or record.get("status") or ""
            lines.append(f"- `{host}` ({catalog.get(host, '?')}) — {detail}")
        if len(hosts) > 60:
            lines.append(f"- … and {len(hosts) - 60} more (full list in the JSON)")
        lines.append("")
    with open(MARKDOWN, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limit", type=int, default=0, help="classify only the first N hosts")
    parser.add_argument("--workers", type=int, default=40)
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()

    catalog, unmeasured = load_unmeasured()
    if args.limit:
        unmeasured = unmeasured[: args.limit]
    print(f"{len(unmeasured)} unmeasured host(s) to classify")

    hosts, counts = {}, {}
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(classify, host, args.timeout): host for host in unmeasured}
        for done, future in enumerate(as_completed(futures), 1):
            host = futures[future]
            try:
                record = future.result()
            except Exception as error:  # noqa: BLE001 - one bad host must not stop the run
                record = {"reason": "unreachable", "error": type(error).__name__}
            hosts[host] = record
            counts[record["reason"]] = counts.get(record["reason"], 0) + 1
            if done % 250 == 0:
                print(f"  {done}/{len(unmeasured)}  "
                      + " ".join(f"{k}={counts[k]}" for k in sorted(counts)))

    state = {
        "schema": 1,
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total": len(catalog),
        "measured": len(catalog) - len(load_unmeasured()[1]),
        "unmeasured": len(unmeasured),
        "min_text": MIN_TEXT,
        "counts": counts,
        "hosts": dict(sorted(hosts.items())),
    }
    with open(EVIDENCE, "w", encoding="utf-8") as handle:
        json.dump(state, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    write_markdown(state, catalog)

    print()
    for reason in REASONS:
        if counts.get(reason):
            print(f"  {reason:20} {counts[reason]:5}")
    print(f"\n✓ wrote {os.path.relpath(EVIDENCE, ROOT)}")
    print(f"✓ wrote {os.path.relpath(MARKDOWN, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
