#!/usr/bin/env python3
"""Generate `docs/CATALOG.md` from `catalog.json`.

    python3 scripts/catalog/build-catalog-docs.py

Add `--check` to verify the committed `docs/CATALOG.md` and README blocks are
current without writing anything.

The catalog ships as a binary-ish JSON blob, so a prose summary of it would be
a second copy to keep in step. This writes that copy on purpose, from the same
file the app reads, so the documentation cannot claim a count the shipped data
does not have. Run it after `generate.py` and commit the result.

It also refreshes the generated blocks (badges, category treemap, bar and pie,
and the verification bar) in `README.md` and its translation `README.tr.md`,
between matching `<!-- ...:start -->` and `<!-- ...:end -->` markers. README.md
is the source of truth and README.tr.md mirrors it; both receive the identical
block content, so the numbers cannot drift between the two languages. The rest
of each README is written by hand and is left untouched; the markers are only a
convenience so the diagrams below cannot drift from the counts above them. The
test suite checks those counts independently, in
`scripts/checks/check-docs-fresh.mjs`.

`docs/NEEDS-REVIEW.md` is written by hand, not by this script — it explains
why a host is unresolved, which needs a person.
"""
import argparse
import json
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CATALOG = os.path.join(ROOT, "catalog.json")
RULES = os.path.join(ROOT, "rules.json")
OUT = os.path.join(ROOT, "docs", "CATALOG.md")
README = os.path.join(ROOT, "README.md")
README_TR = os.path.join(ROOT, "README.tr.md")
# README.md is the source of truth; README.tr.md is its translation. Both carry
# the same marked blocks, so the counts cannot drift between the two languages.
READMES = (README, README_TR)
ANALYSIS = os.path.join(ROOT, "docs", "analysis", "out", "matrix-data.json")

TREEMAP_START = "<!-- category-treemap:start -->"
TREEMAP_END = "<!-- category-treemap:end -->"
BAR_START = "<!-- category-bar:start -->"
BAR_END = "<!-- category-bar:end -->"
PIE_START = "<!-- category-pie:start -->"
PIE_END = "<!-- category-pie:end -->"
BADGES_START = "<!-- catalog-badges:start -->"
BADGES_END = "<!-- catalog-badges:end -->"
SWEEP_START = "<!-- verification-status:start -->"
SWEEP_END = "<!-- verification-status:end -->"


def render_treemap(counts):
    """A mermaid `treemap-beta` of the catalog, biggest category first.

    A treemap reads as a picture of the whole catalog — what share `finance`
    is, how small `maps` is — in a way a table cannot. It is generated rather
    than drawn so the numbers in it are the numbers in `catalog.json`.
    """
    lines = [
        TREEMAP_START,
        "",
        "```mermaid",
        "treemap-beta",
        '"Catalog by category"',
    ]
    for name, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f'    "{name}": {count:,}')
    lines += ["```", "", TREEMAP_END]
    return "\n".join(lines)


def render_bar(counts, top=10):
    """A mermaid `xychart-beta` bar of the biggest categories.

    Reads as a ranked list at a glance — the same information as the treemap,
    but comparable in height, which a treemap's fixed area cannot show for a
    long tail.
    """
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:top]
    names = ", ".join(name for name, _ in ranked)
    values = ", ".join(str(c) for _, c in ranked)
    ceiling = ranked[0][1] if ranked else 0
    return "\n".join([
        BAR_START,
        "",
        "```mermaid",
        "xychart-beta",
        '    title "Hosts by category (top %d)"' % top,
        f"    x-axis [{names}]",
        f'    y-axis "hosts" 0 --> {ceiling}',
        f"    bar [{values}]",
        "```",
        "",
        BAR_END,
    ])


def render_pie(counts, top=8):
    """A mermaid `pie` of the category share, the long tail folded into `other`."""
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    head = ranked[:top]
    tail_total = sum(c for _, c in ranked[top:])
    lines = [PIE_START, "", "```mermaid", "pie title Catalog by category (share)"]
    for name, count in head:
        lines.append(f'    "{name}" : {count}')
    if tail_total:
        lines.append(f'    "other ({len(ranked) - top} smaller)" : {tail_total}')
    lines += ["```", "", PIE_END]
    return "\n".join(lines)


def render_badges(catalog, rules):
    """Static shields.io badges — the headline numbers, coloured and at the top."""
    total = len(catalog.get("categories") or {})
    cats = len(set((catalog.get("categories") or {}).values()))
    services = len(catalog.get("services") or [])
    removed = len(((rules.get("drop") or {}).get("hosts")) or {})
    def badge(label, value, color):
        v = str(value).replace(",", "").replace("-", "--").replace("_", "__")
        return f"![{label}](https://img.shields.io/badge/{label}-{v}-{color})"
    badges = [
        badge("hosts", f"{total:,}", "blue"),
        badge("categories", cats, "brightgreen"),
        badge("services", services, "blueviolet"),
        badge("removed", removed, "red"),
    ]
    return "\n".join([BADGES_START, "", " ".join(badges), "", BADGES_END])


def render_verification():
    """A mermaid bar of the DNS sweep outcomes, if its evidence is present.

    The catalog's own verification status: how many hosts the dead-domain sweep
    checked and what it found. Empty when there is no evidence, so a fresh
    checkout without a sweep run does not advertise numbers it cannot back.
    """
    path = os.path.join(ROOT, "evidence", "dead-domain-sweep.json")
    try:
        with open(path, encoding="utf-8") as handle:
            sweep = json.load(handle)
    except (OSError, ValueError):
        return None
    rounds = [r for r in (sweep.get("rounds") or []) if r.get("complete") and r.get("counts")]
    if not rounds:
        return None
    counts = rounds[-1].get("counts") or {}
    order = ["alive", "nodata", "servfail", "dead", "unknown"]
    present = [(k, counts.get(k, 0)) for k in order if k in counts]
    if not present:
        return None
    names = ", ".join(k for k, _ in present)
    values = ", ".join(str(v) for _, v in present)
    ceiling = max(v for _, v in present)
    return "\n".join([
        SWEEP_START,
        "",
        "```mermaid",
        "xychart-beta",
        '    title "Dead-domain sweep — verdicts (last round)"',
        f"    x-axis [{names}]",
        f'    y-axis "hosts" 0 --> {ceiling}',
        f"    bar [{values}]",
        "```",
        "",
        SWEEP_END,
    ])


def _replace_block(text, start, end, content):
    """Return `text` with the content between two markers replaced."""
    if start not in text or end not in text:
        return None
    before, rest = text.split(start, 1)
    _, after = rest.split(end, 1)
    return f"{before}{content}{after}"


def apply_readme_blocks(text, counts, catalog, rules):
    """Return `(text, skipped)` with every marked block rewritten in place.

    Pure: it does not touch the file, so `--check` can ask what the README would
    become without writing it.
    """
    skipped = 0
    for start, end, content in (
        (BADGES_START, BADGES_END, render_badges(catalog, rules)),
        (TREEMAP_START, TREEMAP_END, render_treemap(counts)),
        (BAR_START, BAR_END, render_bar(counts)),
        (PIE_START, PIE_END, render_pie(counts)),
    ):
        replaced = _replace_block(text, start, end, content)
        if replaced is None:
            skipped += 1
        else:
            text = replaced
    verification = render_verification()
    if verification is not None:
        replaced = _replace_block(text, SWEEP_START, SWEEP_END, verification)
        if replaced is None:
            skipped += 1
        else:
            text = replaced
    return text, skipped


def update_readme_blocks(path, counts, catalog, rules):
    """Rewrite every marked block in `path`. Returns (changed, skipped).

    A block whose markers are missing is skipped, not a failure — the README is
    a hand-written document and must not become required furniture. A path that
    does not exist returns (None, 0), so a checkout without the translation
    still works.
    """
    try:
        with open(path, encoding="utf-8") as handle:
            original = handle.read()
    except OSError:
        return None, 0
    text, skipped = apply_readme_blocks(original, counts, catalog, rules)
    if text == original:
        return False, skipped
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return True, skipped


def other_from_rules():
    """Hosts `rules.json` deliberately files under `other`.

    Read from the rules rather than hardcoded here, so a host cannot drift into
    `other` without the document noticing that it was a decision and not a
    shrug.
    """
    try:
        with open(RULES, encoding="utf-8") as handle:
            rules = json.load(handle)
    except (OSError, ValueError):
        return set()
    return {
        pattern.lower()
        for rule in rules.get("rules", [])
        if rule.get("category") == "other"
        for pattern in rule.get("match", [])
    }

# What a person reads the screen by, not what happens to be common.
ORDER = [
    ("software", "a tool, a platform, a developer utility"),
    ("shopping", "a store, a marketplace, a payment provider"),
    ("video", "streaming, live TV, a broadcaster"),
    ("finance", "banks, cards, trading, markets"),
    ("news", "press, and the reporting it depends on"),
    ("health", "hospitals, pharmacies, health apps"),
    ("ai", "model providers and the products built on them"),
    ("ads", "ad networks, affiliate platforms, retargeting"),
    ("government", "ministries, municipalities, agencies"),
    ("cdn", "delivery networks carrying somebody else's bytes"),
    ("social", "where people talk to each other"),
    ("travel", "airlines, booking, ground transport"),
    ("gaming", "stores, launchers, and the games"),
    ("transport", "shipping, driving, ride and rail"),
    ("encyclopedia", "reference, metadata, documentation"),
    ("education", "schools, universities, courses"),
    ("analytics", "measurement, crash reporting, experimentation"),
    ("search", "search engines and search portals"),
    ("messaging", "chat, mail, messaging"),
    ("email", "mailbox providers"),
    ("telecom", "carriers and network operators"),
    ("other", "deliberately a last resort, not a fallback"),
    ("crash", "crash and error reporting"),
    ("crypto", "exchanges, wallets, chains"),
    ("music", "streaming and audio"),
    ("sports", "leagues, scores, fixtures"),
    ("maps", "map tiles and geocoding"),
]


def check_artifacts(rendered, counts, catalog, rules):
    """Report whether the committed artifacts match what this run would write.

    Nothing is written. `docs/CATALOG.md` is compared byte for byte; each README
    is compared as the text it would become, so a hand-written README with no
    marked blocks is left alone, exactly as the writer leaves it.
    """
    problems = []
    try:
        with open(OUT, encoding="utf-8") as handle:
            committed = handle.read()
    except OSError:
        committed = None
    if committed != rendered:
        problems.append("docs/CATALOG.md is stale — rerun build-catalog-docs.py")

    for path in READMES:
        try:
            with open(path, encoding="utf-8") as handle:
                readme = handle.read()
        except OSError:
            continue
        updated, _ = apply_readme_blocks(readme, counts, catalog, rules)
        if updated != readme:
            problems.append(
                f"{os.path.basename(path)}'s marked blocks are stale — rerun build-catalog-docs.py"
            )

    if problems:
        for problem in problems:
            print(f"✗ {problem}", file=sys.stderr)
        return 1
    print("✓ docs/CATALOG.md and the README blocks are current")
    return 0


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true",
        help="verify the committed documents are current; write nothing",
    )
    args = parser.parse_args(argv[1:])

    try:
        with open(CATALOG, encoding="utf-8") as handle:
            doc = json.load(handle)
    except (OSError, ValueError) as error:
        print(f"✗ cannot read {CATALOG}: {error}", file=sys.stderr)
        return 1

    categories = doc.get("categories") or {}
    services = doc.get("services") or []
    counts = Counter(categories.values())

    missing = [name for name, _ in ORDER if name not in counts]
    if missing:
        print(f"✗ categories in the catalog but not in ORDER: {', '.join(sorted(missing))}", file=sys.stderr)
        print("  add them, or this document under-reports the shipped data.", file=sys.stderr)
        return 1
    unknown = sorted(set(counts) - {name for name, _ in ORDER})
    if unknown:
        print(f"✗ ORDER lists categories the catalog does not use: {', '.join(unknown)}", file=sys.stderr)
        return 1

    used = [(name, note) for name, note in ORDER if counts[name]]
    total = len(categories)

    lines = []
    add = lines.append
    add("# Catalog")
    add("")
    add("Generated from `catalog.json` by `scripts/catalog/build-catalog-docs.py`. **Do not")
    add("edit by hand** — edit `seeds/` and regenerate, or this file and the shipped")
    add("data will disagree, which is the one thing a data file must never do.")
    add("")
    add("## Totals")
    add("")
    add(f"**{total:,} names** across **{len(used)} categories**, plus **{len(services)} services**.")
    add("")
    add("The app loads `catalog.json` as a Category Data source and matches a host")
    add("whole, so `facebook.com` covers `graph.facebook.com` without listing it.")
    add("")
    add("## By category")
    add("")
    add("| Category | Hosts | What it means |")
    add("| :--- | --: | :--- |")
    for name, note in used:
        add(f"| `{name}` | {counts[name]} | {note} |")
    add("")
    add("### `other` is a decision")
    add("")
    others = sorted(h for h, c in categories.items() if c == "other")
    ruled = other_from_rules()
    shorteners = [h for h in others if h in ruled]
    add(f"{len(others)} host{'s' if len(others) != 1 else ''} sit in `other`: "
        f"{len(shorteners)} URL shorteners and {len(others) - len(shorteners)} curated by hand.")
    add("")
    if shorteners:
        add("The shorteners are " + ", ".join(f"`{h}`" for h in shorteners) + ".")
        add("A shortener is not a thing a person uses on purpose, so there is no honest")
        add("category for it.")
        add("")
    rest = [h for h in others if h not in ruled]
    if rest:
        add("The remainder were labelled `other` by hand — " + ", ".join(f"`{h}`" for h in rest) + ".")
        add("")
    add("`harvest.py` will not write `other` on its own. Only a rule in `rules.json`")
    add("may, because `other` has to be a decision rather than a shrug.")
    add("")
    add("## By service")
    add("")
    add(f"{len(services)} products, one entry each in `seeds/services.json`:")
    add("")
    add("| Service | Domains |")
    add("| :--- | --: |")
    for service in services:
        add(f"| {service.get('name', '?')} (`{service.get('key', '?')}`) | {len(service.get('domains', []))} |")
    add("")
    add("One entry per **product**, not per company — Facebook, Instagram, WhatsApp")
    add("and Threads are separate on purpose, because a DNS filter sees domains, not")
    add("apps, and a product is what a person recognises.")
    add("")
    add("## Where a name came from")
    add("")
    add("| Source | Licence | What it means |")
    add("| :--- | :--- | :--- |")
    add("| the seeds, curated here | CC0 | a person decided this label |")
    add("| `anudeepND` (3 lists) | MIT | hosts commonly caught by overzealous blocklists, used only to *find* hosts that are missing |")
    add("")
    add("Every source, and every source refused, is in [`SOURCES.md`](SOURCES.md).")
    add("External sources propose hosts; **no source assigns a category**. A category")
    add("is either a rule in `rules.json` or a person with a reason.")
    add("")
    add("Hosts still missing a label are in [`NEEDS-REVIEW.md`](NEEDS-REVIEW.md).")

    if os.path.exists(ANALYSIS):
        with open(ANALYSIS, encoding="utf-8") as handle:
            analysis = json.load(handle)
        if analysis.get("total_hosts") == total:
            accuracy = analysis.get("accuracy", 0.0)
            balanced = analysis.get("balanced_accuracy")
            classes = analysis.get("classes", [])
            hosts = analysis.get("hosts_after_filter", 0)
            dropped = analysis.get("dropped_classes", {})
            add("")
            add("## Reliability")
            add("")
            add("An audit compares TF-IDF text classifiers, keeps LinearSVC for")
            add(f"the detailed {analysis.get('folds', 5)}-fold cross-validation, and asks")
            add(f"how reliably each label can be recovered from the host's own page:")
            add(f"**accuracy {accuracy:.0%}** over {hosts:,} hosts across {len(classes)} categories.")
            add("")
            if balanced is not None:
                add(f"Balanced accuracy is **{balanced:.0%}**. `finance` is over half the catalog,")
                add("so accuracy mostly reports how well the model predicts `finance`; the")
                add("balanced figure weights every category equally and is the one that")
                add("describes the labels as a whole.")
                add("")
            add("This measures *self-consistency*, not correctness — there is no independent")
            add("ground truth, so a low figure means a label disagrees with its page, not")
            add("that the label is wrong.")
            add("")
            if analysis.get("measured_hosts") and analysis.get("total_hosts"):
                un = analysis.get("unmeasured", {})
                add(f"The audit reaches {analysis['measured_hosts']:,} of the catalog's")
                add(f"{analysis['total_hosts']:,} hosts; the rest serve no usable page text"
                    + (f" — {un.get('no_response', 0):,} answer nothing at all and"
                       f" {un.get('too_short', 0):,} return under {un.get('min_text', 100)}"
                       " characters." if un else "."))
                add("The failures are uneven — some categories are measured on a small")
                add("fraction of their hosts. A per-class score describes the hosts that")
                add("produced text, not the category. Per-category coverage is in")
                add("[`analysis/README.md`](analysis/README.md).")
                add("")
            if dropped:
                names = ", ".join(f"`{c}` {n}" for c, n in sorted(dropped.items(), key=lambda kv: -kv[1]))
                add(f"{len(dropped)} further categories have too few labelled examples to")
                add(f"be measured at all and are excluded: {names}. Nothing here says")
                add("whether those labels are correct.")
                add("")
            if analysis.get("thin_classes"):
                thin = analysis["thin_classes"]
                names = ", ".join(f"`{c}` {n}" for c, n in sorted(thin.items(), key=lambda kv: kv[1]))
                add(f"{len(thin)} categories rest on under 20 examples, so their scores are")
                add(f"indicative rather than measured: {names}.")
                add(f"The matrix uses {analysis.get('folds', 5)}-fold cross-validation because the")
                add("smallest category cannot be split five ways.")
                add("")
            if analysis.get("predictions"):
                add("The audit output also records each host's top three predicted categories")
                add("and confidence score, and the correlated-terms report shows both")
                add("chi-squared terms and the fitted LinearSVC weights.")
                add("")
            add("![Confusion matrix](analysis/out/confusion-matrix.png)")
            add("")
            add("Methodology, per-class metrics and the error list: [`analysis/`](analysis/README.md).")

    rendered = "\n".join(lines) + "\n"

    try:
        with open(RULES, encoding="utf-8") as handle:
            rules = json.load(handle)
    except (OSError, ValueError):
        rules = {}

    if args.check:
        return check_artifacts(rendered, counts, doc, rules)

    with open(OUT, "w", encoding="utf-8") as handle:
        handle.write(rendered)
    print(f"✓ wrote docs/CATALOG.md: {total} names, {len(used)} categories, {len(services)} services")

    changed, skipped = False, 0
    for path in READMES:
        this_changed, this_skipped = update_readme_blocks(path, counts, doc, rules)
        name = os.path.basename(path)
        if this_changed is None:
            print(f"· {name} has no marked blocks; left it alone")
        elif this_changed:
            print(f"✓ refreshed the {name} blocks (badges, treemap, bar, pie, verification)"
                  + (f"; {this_skipped} marker(s) absent" if this_skipped else ""))
        else:
            print(f"· the {name} blocks were already current")
        changed = changed or bool(this_changed)
        skipped += this_skipped
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
