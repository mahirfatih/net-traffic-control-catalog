"""Draw a reviewable precision sample for the two dominant categories.

The classifier's own score is not evidence that a *label* is right: finance is
half the catalog and its labels partly come from a bank list, so a model fitted
on those labels is graded on the very signal that made them. This script draws a
fixed, seeded sample of `finance` and `government` hosts, attaches the cached
homepage text as evidence, and — once verdicts are filled — computes how many
labels are actually correct.

It is deliberately independent of the classifier: the verdict comes from a
person (or an agent) reading the page, not from the model being judged.

Standard library only. Not part of `test/test.sh`: it reads `.pages/`, which is
a network artifact.

    python3 precision-sample.py --emit           # write the worksheet
    python3 precision-sample.py --score          # precision + Wilson interval
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CATALOG = ROOT / "catalog.json"
PAGES = Path(__file__).resolve().parent / ".pages"
ANALYSIS = ROOT / "docs" / "analysis"
SAMPLE = ANALYSIS / "precision-sample.json"
VERDICTS = ANALYSIS / "precision-verdicts.json"
REPORT = ANALYSIS / "precision.md"

# What the audit asked for: the two categories big enough for the number to
# mean something, sampled in proportion to nothing — a flat spend per category.
SAMPLE_PLAN = {"finance": 200, "government": 100}
SEED = 20261018
MIN_TEXT = 100
_WS = re.compile(r"\s+")


def page_text(host: str) -> str:
    path = PAGES / f"{host}.txt"
    if not path.exists():
        return ""
    return _WS.sub(" ", path.read_text(encoding="utf-8", errors="replace")).strip()


def evidence(host: str, width: int = 220) -> str:
    text = page_text(host)
    return text[:width] if text else ""


def emit() -> int:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))["categories"]
    rng = random.Random(SEED)
    rows = []
    for category, want in SAMPLE_PLAN.items():
        pool = sorted(h for h, c in catalog.items() if c == category and len(page_text(h)) >= MIN_TEXT)
        if len(pool) <= want:
            chosen = pool
        else:
            chosen = sorted(rng.sample(pool, want))
        for host in chosen:
            rows.append({"host": host, "label": category, "evidence": evidence(host), "verdict": None})
    doc = {
        "seed": SEED,
        "min_text": MIN_TEXT,
        "plan": SAMPLE_PLAN,
        "note": "verdict: true = label right, false = label wrong, null = not yet reviewed",
        "sampled": rows,
    }
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    SAMPLE.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    # A compact, greppable twin so the review is readable line by line.
    lines = [f"# {r['label']}\t{r['host']}\t{r['evidence']}" for r in rows]
    (ANALYSIS / "precision-sample.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {SAMPLE.relative_to(ROOT)} and precision-sample.tsv ({len(rows)} rows)")
    return 0


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a proportion — honest at small n."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


def score() -> int:
    sample = json.loads(SAMPLE.read_text(encoding="utf-8"))
    verdicts = {}
    wrong_notes: dict[str, str] = {}
    if VERDICTS.exists():
        doc = json.loads(VERDICTS.read_text(encoding="utf-8"))
        verdicts = doc.get("verdicts", doc)
        wrong_notes = doc.get("wrong", {})

    totals: dict[str, list[int]] = {}
    unreviewed = 0
    wrong: list[str] = []
    for row in sample["sampled"]:
        verdict = verdicts.get(row["host"], row.get("verdict"))
        if verdict is None:
            unreviewed += 1
            continue
        bucket = totals.setdefault(row["label"], [0, 0])
        bucket[0] += 1  # reviewed
        bucket[1] += 1 if verdict else 0  # correct
        if not verdict:
            wrong.append(row["host"])

    lines = ["# Label precision — a hand-read sample", ""]
    lines.append("Independent of the classifier: each host's homepage text was read and its")
    lines.append("label judged right or wrong. The gap to a model's score is the point.")
    lines.append("")
    lines.append("| Category | Reviewed | Correct | Precision | 95% CI |")
    lines.append("| :--- | ---: | ---: | ---: | :--- |")
    for category in sample["plan"]:
        reviewed, correct = totals.get(category, [0, 0])
        if reviewed == 0:
            lines.append(f"| {category} | 0 | — | — | — |")
            continue
        p = correct / reviewed
        lo, hi = wilson(correct, reviewed)
        lines.append(f"| {category} | {reviewed} | {correct} | {p:.1%} | {lo:.1%}–{hi:.1%} |")
    lines.append("")
    if wrong:
        lines.append("Labels judged wrong, and why:")
        lines.append("")
        for host in sorted(wrong):
            reason = wrong_notes.get(host, "")
            lines.append(f"- `{host}` — {reason}" if reason else f"- `{host}`")
        lines.append("")
    if unreviewed:
        lines.append(f"{unreviewed} host(s) drawn but not yet reviewed; the number above is "
                     f"precision on the reviewed part, not the category.")
        lines.append("")
    lines.append(f"Seed {sample['seed']}, sample of {sum(sample['plan'].values())} "
                 f"hosts with ≥{sample['min_text']} characters of homepage text.")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nwrote {REPORT.relative_to(ROOT)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit", action="store_true", help="write the sample worksheet")
    ap.add_argument("--score", action="store_true", help="score the verdicts and write precision.md")
    args = ap.parse_args()
    if args.emit:
        return emit()
    if args.score:
        return score()
    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
