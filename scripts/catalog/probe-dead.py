#!/usr/bin/env python3
"""Find catalog hosts that no longer exist in DNS — evidence, never a guess.

    python3 scripts/catalog/probe-dead.py --self-test
    python3 scripts/catalog/probe-dead.py --round 1 [--limit 200]
    python3 scripts/catalog/probe-dead.py --round 2        # at least 10 minutes later
    python3 scripts/catalog/probe-dead.py --summary

A domain that no longer resolves is not just dead weight. It can be bought by
somebody else, and it would keep the category the previous owner had — a user
who allows `finance` would then be allowing whoever holds that name now. So
removing a dead host is a correctness fix, not tidiness.

The hard part is telling *dead* apart from *unreachable*. This network cannot
do that: a firewall that drops NXDOMAIN-only names, a captive portal, a broken
upstream resolver all look identical to a dead domain from inside the process.
That mistake has already nearly cost this catalog 181 real banks, so this
script does it the one way that cannot lie — it asks the resolvers directly
and reads the response code they return:

    0  NOERROR    the name exists
    3  NXDOMAIN   the name does not exist

It asks three independent resolvers (Cloudflare, Google and AdGuard) about
three record types (A, AAAA, NS), because NXDOMAIN is type-independent: if a
name is gone, every question about it comes back `3`. That gives a host nine
chances to prove it is alive, and it has to fail all nine to be called dead.

Then it has to do it twice. One round is a snapshot; a resolver outage is a
round. `--round 2` refuses to run until `--min-gap-minutes` has passed since
round 1, and refuses silently reusing round 1's answers.

Nothing here edits catalog data. The output is evidence plus a *proposal*
(the hosts both rounds agree are gone), and a person decides what to do with
it. This script is deliberately not part of `test/test.sh`: it needs the
network, and CI must never depend on a network.

Precedence of the answer, least to most trusted: an HTTP success beats any DNS
answer; a `NOERROR` with records beats a `NOERROR` without; a `NOERROR`
without records is *not* dead (`nodata` — a mail-only domain has no A record);
a timeout, `SERVFAIL` or rate-limit is *unknown*, and unknown is kept.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
import importlib.util
import json
import os
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CATEGORIES = os.path.join(ROOT, "seeds", "categories.json")
RULES = os.path.join(ROOT, "config/rules.json")
EVIDENCE = os.path.join(ROOT, "evidence")
STATE = os.path.join(EVIDENCE, "dead-domain-sweep.json")
MARKDOWN = os.path.join(EVIDENCE, "dead-domain-sweep.md")
CATALOG_CORE = os.path.join(ROOT, "scripts", "catalog", "catalog-core.py")

USER_AGENT = "net-traffic-control-catalog/1.0 (dead-domain sweep)"
SAVE_EVERY = 200

# A canary each resolver must answer correctly before the run is allowed to
# start. If these are wrong, every host in the catalog would "look dead" and
# the tool would hand a human a list of 7,177 mistakes. Aborting is the only
# correct response to a resolver that cannot answer a trivial question.
CANARIES = [
    # (name, type, expected_status, expected_has_answers, why)
    ("google.com", "A", 0, True, "a name that certainly exists must return NOERROR with records"),
    ("net-traffic-control-catalog-probe.invalid", "A", 3, False, ".invalid is reserved for this; it must return NXDOMAIN"),
    ("ai", "A", 0, False, "a TLD has no address record: NOERROR with zero answers, still alive"),
]

# Three independent resolvers, queried by name and rcode rather than by the
# system resolver, so the answer does not depend on this network's upstream.
# AdGuard's *unfiltered* endpoint is required: the default one answers blocked
# ad and tracker names with 0.0.0.0, and this catalog is largely about exactly
# those names, so a filtering resolver would be measuring its own blocklist.
RESOLVERS = {
    "cloudflare": "https://cloudflare-dns.com/dns-query",
    "google": "https://dns.google/resolve",
    "adguard": "https://unfiltered.adguard-dns.com/resolve",
}

# Three record types. Dead means NXDOMAIN on all of them, not just one.
RECORD_TYPES = ("A", "AAAA", "NS")

# Every verdict a host can get in one round, in the order the report prints
# them. `servfail` and `unknown` are both kept: neither is evidence that a
# name is gone, only that a public resolver could not answer for it.
DECISIONS = ("alive", "nodata", "servfail", "dead", "unknown")

_spec = importlib.util.spec_from_file_location("catalog_core", CATALOG_CORE)
catalog_core = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(catalog_core)


def load_categories(path=CATEGORIES):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def doh_query(resolver_url, name, rrtype, timeout, cd=False):
    """Return `(status, answer_count)`, or `(None, 0)` when the network failed.

    A `None` status means "this resolver did not answer", which is an unknown —
    never dead. Distinguishing that from a real rcode is the entire point of
    talking to a resolver directly.

    `cd=True` sets the Checking Disabled flag, so DNSSEC validation is skipped:
    the same question asked a second way, to tell a validation failure from a
    delegation that never worked.
    """
    url = f"{resolver_url}?name={urllib.parse.quote(name)}&type={rrtype}"
    if cd:
        url += "&cd=1"
    request = urllib.request.Request(url, headers={"accept": "application/dns-json", "user-agent": USER_AGENT})
    for attempt in (0, 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = json.load(response)
            return int(payload.get("Status", -1)), len(payload.get("Answer") or [])
        except (urllib.error.URLError, OSError, ValueError):
            # A dropped packet on the first try is not news. The second try
            # is free and turns a flap into an answer; if it fails too, the
            # status stays unknown.
            if attempt:
                return None, 0
    return None, 0


def self_test(timeout):
    """Verify every resolver answers the canaries. Returns a list of problems."""
    problems = []
    for resolver, url in sorted(RESOLVERS.items()):
        for name, rrtype, expected_status, expected_answers, why in CANARIES:
            status, answers = doh_query(url, name, rrtype, timeout)
            if status != expected_status or bool(answers) is not expected_answers:
                problems.append(
                    f"{resolver}: {name} {rrtype} returned status={status} answers={answers}, "
                    f"expected status={expected_status} answers={'some' if expected_answers else 'none'} — {why}"
                )
    return problems


def classify(statuses, answers):
    """alive / nodata / dead / unknown, for one host in one round.

    `statuses` is `{resolver: {rtype: rcode or None}}`, `answers` the totals.
    Anywhere a name shows up with a record it is alive, and that decision is
    final no matter what the other five questions said.
    """
    if answers > 0:
        return "alive"
    seen = [s for per_type in statuses.values() for s in per_type.values()]
    if any(s == 0 for s in seen):
        # NOERROR with no records: the name exists, it just has no address.
        # A mail-only or redirect-only domain lands here. It must be kept.
        return "nodata"
    if seen and all(s == 3 for s in seen):
        return "dead"
    if seen and all(s == 2 for s in seen):
        # Every resolver says SERVFAIL: the zone is broken, not missing. That
        # is often a dangling domain whose owner let the registration lapse,
        # so it is worth showing a person — but a broken zone proves nothing
        # about whether the name is gone, so it is never proposed for removal.
        return "servfail"
    return "unknown"


def probe_one(host, timeout):
    statuses, answers = {}, 0
    for resolver, url in sorted(RESOLVERS.items()):
        statuses[resolver] = {}
        for rrtype in RECORD_TYPES:
            status, count = doh_query(url, host, rrtype, timeout)
            statuses[resolver][rrtype] = status
            answers += count
    decision = classify(statuses, answers)
    cd = None
    if decision == "servfail":
        # SERVFAIL is two different failures wearing the same rcode: DNSSEC
        # validation, or a lame delegation. One query with checking disabled
        # tells them apart — a name that answers once validation is off was
        # never "broken", it was just unvalidated. This does not change the
        # verdict: SERVFAIL is still never proposed for removal.
        checked = [
            doh_query(url, host, "A", timeout, cd=True)[0]
            for url in sorted(RESOLVERS.values())
        ]
        if any(s == 0 for s in checked):
            cd = "dnssec"
        elif checked and all(s == 2 for s in checked):
            cd = "lame"
    return {
        "statuses": statuses,
        "answers": answers,
        "decision": decision,
        "cd": cd,
    }


def round_timestamp(state, round_number):
    for entry in state.get("rounds", []):
        if entry.get("round") == round_number:
            return entry.get("generated")
    return None


def save_round(state, round_number, results, counts, complete, elapsed_seconds=None):
    """Record a run of `round_number`, replacing any earlier run of it.

    `elapsed_seconds` is kept because the documents quote how long a sweep
    takes, and a quoted duration nobody measures is a guess that goes stale
    silently — the last one was three times the real figure. The checker in
    `scripts/checks/check-docs-fresh.mjs` reads it from here.
    """
    entry = {
        "round": round_number,
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "complete": complete,
        "elapsed_seconds": round(elapsed_seconds, 2) if elapsed_seconds is not None else None,
        "counts": counts,
        "results": results,
    }
    state["rounds"] = [e for e in state.get("rounds", []) if e.get("round") != round_number] + [entry]
    return entry


def gap_minutes(state, round_number):
    """Minutes since the previous round, or None when there is no previous one."""
    if round_number == 1:
        return None
    previous = round_timestamp(state, round_number - 1)
    if not previous:
        return None
    try:
        earlier = datetime.fromisoformat(previous)
    except ValueError:
        return None
    if earlier.tzinfo is None:
        earlier = earlier.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - earlier).total_seconds() / 60.0


def save_state(state, path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(state, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def write_markdown(state, categories, proposal, path=MARKDOWN):
    rounds = {entry["round"]: entry.get("counts", {}) for entry in state.get("rounds", [])}
    lines = [
        "# Dead-domain sweep",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        "Two rounds, at least ten minutes apart, asking Cloudflare, Google and",
        "AdGuard directly about A, AAAA and NS. A host is only *dead* when every",
        "one of the nine questions in **both** rounds answers NXDOMAIN.",
        "",
        "| Round | alive | nodata | servfail | dead | unknown |",
        "| ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for number in sorted(rounds):
        counts = rounds[number]
        lines.append(
            f"| {number} | " + " | ".join(str(counts.get(key, 0)) for key in DECISIONS) + " |"
        )

    # SERVFAIL rows are kept but surfaced: a broken zone is usually a domain
    # nobody owns any more, which is exactly the recycling risk this sweep is
    # for. It is listed so a person can look, never so it can be deleted.
    flagged = sorted(
        host
        for entry in state.get("rounds", [])
        for host, result in entry.get("results", {}).items()
        if result.get("decision") == "servfail"
    )
    lines += [
        "",
        f"## Worth a look — {len(flagged)} host(s) SERVFAIL from every resolver",
        "",
        "Kept, not dropped. A zone that SERVFAILs everywhere is usually a name",
        "whose registration lapsed, so its category may now describe whoever",
        "holds it. This is the recycling risk; it is reported, not acted on.",
        "",
    ]
    lines.extend(f"- `{host}` ({categories.get(host, '?')})" for host in flagged)
    lines += [
        "",
        f"## Proposal — {len(proposal)} host(s) dead in both rounds",
        "",
        "This is a proposal, not a deletion. Applying it means adding the host to",
        "`rules.json` → `drop.hosts` with a reason that cites this evidence, then",
        "regenerating the catalog.",
        "",
        "| Category | Host | Parent also dead |",
        "| :--- | :--- | :--- |",
    ]
    dead = set(proposal)
    for host in proposal:
        parent = next(
            (p for i in range(1, len(host.split(".")) - 1) if (p := ".".join(host.split(".")[i:])) in dead),
            None,
        )
        lines.append(f"| {categories.get(host, '?')} | `{host}` | {parent or '—'} |")
    lines.append("")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def markdown_path(args):
    """Sit the table beside the state file, so a `--state` test stays out of
    `evidence/` instead of leaving a half-finished sweep for someone to find."""
    if args.state == STATE:
        return MARKDOWN
    return os.path.splitext(args.state)[0] + ".md"


def run_round(args, categories, state, round_number):
    hosts = sorted(categories)
    if args.limit:
        hosts = hosts[: args.limit]

    problems = self_test(args.timeout)
    if problems:
        print("✗ resolver self-test failed — aborting rather than reporting a catalog of guesses:",
              file=sys.stderr)
        for problem in problems:
            print(f"    {problem}", file=sys.stderr)
        return 1
    print(f"✓ resolver self-test passed ({len(RESOLVERS)} resolvers, {len(CANARIES)} canaries)")

    minutes = gap_minutes(state, round_number)
    if minutes is not None and minutes < args.min_gap_minutes:
        print(f"✗ round {round_number} is only {minutes:.1f} minute(s) after round {round_number - 1}; "
              f"this run needs at least {args.min_gap_minutes}", file=sys.stderr)
        print("  one round is a snapshot, and a resolver outage is a snapshot too",
              file=sys.stderr)
        return 1
    if minutes is not None:
        print(f"✓ {minutes:.1f} minute(s) since round {round_number - 1} (minimum {args.min_gap_minutes})")

    print(f"probing {len(hosts)} host(s) for round {round_number} "
          f"({args.workers} workers, {len(RESOLVERS)} resolvers × {len(RECORD_TYPES)} record types)")
    started = time.time()
    results, counts = {}, {}
    done = 0

    try:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(probe_one, host, args.timeout): host for host in hosts}
            for future in as_completed(futures):
                host = futures[future]
                result = future.result()
                results[host] = result
                counts[result["decision"]] = counts.get(result["decision"], 0) + 1
                done += 1
                if done % SAVE_EVERY == 0:
                    # Partial progress is worth saving: a twenty-minute round
                    # must not be lost to one dropped connection. Only the
                    # latest run of this round number is kept, so a re-run
                    # replaces rather than appends.
                    save_round(state, round_number, results, counts, complete=False,
                               elapsed_seconds=time.time() - started)
                    save_state(state, args.state)
                if done % 250 == 0:
                    print(f"  {done}/{len(hosts)}  " + " ".join(f"{k}={counts[k]}" for k in sorted(counts)))
    except KeyboardInterrupt:
        print(f"\n! interrupted after {done} host(s); partial progress saved", file=sys.stderr)

    save_round(state, round_number, results, counts, complete=done == len(hosts),
               elapsed_seconds=time.time() - started)
    save_state(state, args.state)

    print(f"\nround {round_number}: " + " ".join(f"{k}={counts.get(k, 0)}" for k in DECISIONS))
    print(f"✓ wrote {os.path.relpath(args.state, ROOT)} in {time.time() - started:.0f}s")

    if not state["rounds"][-1]["complete"]:
        print(f"! round {round_number} was incomplete; run it again to get a full picture", file=sys.stderr)
        return 1
    return 0


def build_proposal(state):
    """Hosts both rounds independently call dead. `None` when round 2 is absent."""
    by_round = {entry["round"]: entry.get("results", {}) for entry in state.get("rounds", [])}
    if 1 not in by_round or 2 not in by_round:
        return None
    first = {host for host, result in by_round[1].items() if result["decision"] == "dead"}
    second = {host for host, result in by_round[2].items() if result["decision"] == "dead"}
    return sorted(first & second)


def apply_proposal(state, categories_path, rules_path, dry_run=True):
    """Remove the proposal from the seeds and record why in `drop.hosts`.

    Two files change, and they change for different reasons:

    - `seeds/categories.json` is the source of truth for the catalog, so the
      host has to leave it for `generate.py` to stop emitting it.
    - `rules.json` → `drop.hosts` is the guard that stops `harvest.py` from
      importing the host again on the next source refresh, and the reason is
      what makes the removal explainable later.

    Idempotent: a host already in `drop.hosts` is overwritten with the fresh
    evidence, and a host already gone from the seeds is skipped, so re-running
    after a partial failure is safe.
    """
    proposal = build_proposal(state)
    if proposal is None:
        print("✗ no proposal yet — run --round 1 and --round 2 first", file=sys.stderr)
        return None

    with open(categories_path, encoding="utf-8") as handle:
        categories = json.load(handle)
    with open(rules_path, encoding="utf-8") as handle:
        rules = json.load(handle)

    drops = rules.setdefault("drop", {}).setdefault("hosts", {})
    dates = [entry["generated"][:10] for entry in sorted(state.get("rounds", []), key=lambda e: e["round"])]
    when = " and ".join(dates)

    removed, already_gone, recorded = [], [], []
    resolvers = "+".join(sorted(RESOLVERS))
    for host in proposal:
        # Read the category before deleting the entry: the reason is supposed to
        # record which category the host was in, and asking after the delete
        # wrote "?" for every one of the 432 hosts removed on 2026-10-14.
        category = categories.get(host, "?")
        if host in categories:
            del categories[host]
            removed.append(host)
        else:
            already_gone.append(host)
        drops[host] = f"NXDOMAIN from {resolvers} on {when}; {category}"

    print(f"proposal: {len(proposal)} host(s) dead in both rounds")
    print(f"  in the seeds, to remove: {len(removed)}")
    print(f"  already absent from the seeds: {len(already_gone)}")
    print(f"  drop.hosts entries written: {len(proposal)}")

    if dry_run:
        print("\ndry run — nothing written. Re-run with --apply to change the files.")
        return {"removed": removed, "already_gone": already_gone, "proposal": proposal}

    with open(categories_path, "w", encoding="utf-8") as handle:
        json.dump({host: categories[host] for host in sorted(categories)}, handle,
                  ensure_ascii=False, indent=2)
        handle.write("\n")
    rules["drop"]["hosts"] = {host: drops[host] for host in sorted(drops)}
    with open(rules_path, "w", encoding="utf-8") as handle:
        json.dump(rules, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    print(f"\n✓ {os.path.relpath(categories_path, ROOT)}: {len(categories)} host(s) remain")
    print(f"✓ {os.path.relpath(rules_path, ROOT)}: {len(drops)} drop.hosts entr(ies)")
    return {"removed": removed, "already_gone": already_gone, "proposal": proposal}


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--round", type=int, choices=(1, 2), help="run a probe round")
    parser.add_argument("--limit", type=int, default=0, help="probe only the first N hosts; 0 means all")
    parser.add_argument("--workers", type=int, default=40)
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--min-gap-minutes", type=float, default=10.0,
                        help="minimum minutes between rounds before round 2 may run")
    parser.add_argument("--categories", default=CATEGORIES)
    parser.add_argument("--rules", default=RULES)
    parser.add_argument("--state", default=STATE)
    parser.add_argument("--summary", action="store_true", help="print counts and the proposal, do not probe")
    parser.add_argument("--apply", action="store_true",
                        help="remove the proposal from the seeds and record it in drop.hosts")
    parser.add_argument("--self-test", action="store_true", help="check the resolvers and exit")
    args = parser.parse_args(argv[1:])

    if args.self_test:
        problems = self_test(args.timeout)
        if problems:
            for problem in problems:
                print(f"✗ {problem}", file=sys.stderr)
            return 1
        print(f"✓ resolvers answer the canaries ({', '.join(sorted(RESOLVERS))})")
        return 0

    if args.state != STATE:
        os.makedirs(os.path.dirname(args.state), exist_ok=True)

    # Round 1 creates the state file; only a later round, --summary or --apply
    # needs one to already exist. Starting a round from a blank state is also
    # what makes a re-run of round 1 safe.
    needs_state = args.round == 2 or args.summary or args.apply
    if needs_state and not os.path.exists(args.state):
        print(f"✗ no sweep state at {os.path.relpath(args.state, ROOT)}; run --round 1 first",
              file=sys.stderr)
        return 1
    if os.path.exists(args.state):
        with open(args.state, encoding="utf-8") as handle:
            state = json.load(handle)
    else:
        state = {"schema": 1, "generated": date.today().isoformat()}

    categories = load_categories(args.categories)

    if args.round in (1, 2):
        return run_round(args, categories, state, args.round)

    if args.apply:
        # `--apply` writes. Without it the same report is a preview, so a
        # person can read the numbers before a seed file changes under them.
        result = apply_proposal(state, args.categories, args.rules, dry_run=False)
        return 0 if result else 1

    if args.summary:
        rounds = {entry["round"]: entry for entry in state.get("rounds", [])}
        if not rounds:
            print("no rounds recorded yet")
            return 1
        for number in sorted(rounds):
            counts = rounds[number].get("counts", {})
            print(f"round {number}: " + " ".join(f"{k}={counts.get(k, 0)}" for k in DECISIONS)
                  + f"  ({'' if rounds[number].get('complete') else 'INCOMPLETE'})")
        proposal = build_proposal(state)
        if proposal is None:
            print("\nround 2 has not run yet; there is no proposal")
            return 0
        write_markdown(state, categories, proposal, markdown_path(args))
        print(f"\nproposal: {len(proposal)} host(s) dead in both rounds")
        for host in proposal:
            print(f"  {categories.get(host, '?'):12} {host}")
        print(f"\n✓ wrote {os.path.relpath(markdown_path(args), ROOT)}")
        return 0

    result = apply_proposal(state, args.categories, args.rules, dry_run=True)
    return 0 if result else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
