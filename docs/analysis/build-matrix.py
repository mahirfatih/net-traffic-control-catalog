"""Train a classifier on cached page text and render a confusion matrix.

The catalog label is the ground truth. A TF-IDF + LinearSVC model is
cross-validated (5-fold) so every host receives an out-of-fold prediction.
The confusion matrix then shows how consistently our labels agree with what
a text model can recover.

Usage:
    python3 build-matrix.py [--min-text 100] [--min-class 20] [--folds 5]
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PAGES = Path(__file__).resolve().parent / "pages"
OUT = Path(__file__).resolve().parent / "out"
CATALOG = ROOT / "catalog.json"


def load_pages(min_text: int) -> dict[str, str]:
    pages: dict[str, str] = {}
    for f in PAGES.glob("*.txt"):
        text = f.read_text(encoding="utf-8", errors="replace")
        if len(text) >= min_text:
            pages[f.stem] = text
    return pages


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-text", type=int, default=100)
    ap.add_argument("--min-class", type=int, default=20)
    ap.add_argument("--folds", type=int, default=5)
    args = ap.parse_args()

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay
    from sklearn.model_selection import cross_val_predict, StratifiedKFold
    from sklearn.pipeline import make_pipeline
    from sklearn.svm import LinearSVC

    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    labels = catalog["categories"]
    pages = load_pages(args.min_text)

    # Keep only hosts that have text AND are in the catalog.
    hosts = sorted(h for h in pages if h in labels)
    y = np.array([labels[h] for h in hosts])
    X = np.array([pages[h] for h in hosts])

    counts = collections.Counter(y)
    keep = {c for c, n in counts.items() if n >= args.min_class}
    mask = np.array([c in keep for c in y])
    X, y = X[mask], y[mask]
    classes = sorted(set(y))

    print(f"{len(hosts)} hosts with text -> {len(y)} after class filter")
    print(f"{len(classes)} classes: {', '.join(classes)}")

    pipe = make_pipeline(
        TfidfVectorizer(sublinear_tf=True, min_df=2, ngram_range=(1, 2), max_features=20000),
        LinearSVC(C=1.0, class_weight="balanced", max_iter=5000),
    )
    cv = StratifiedKFold(n_splits=args.folds, shuffle=True, random_state=42)
    pred = cross_val_predict(pipe, X, y, cv=cv, n_jobs=-1)

    cm = confusion_matrix(y, pred, labels=classes)
    np.set_printoptions(linewidth=200)
    print("\nConfusion matrix (rows=true, cols=predicted):")
    print(cm)

    # Per-class accuracy
    print("\nPer-class accuracy:")
    for i, c in enumerate(classes):
        tp = cm[i, i]
        total = cm[i].sum()
        print(f"  {c:14} {tp:4}/{total:4}  {tp/total:.0%}")

    # Off-diagonal examples
    print("\nOff-diagonal predictions (first 40):")
    kept_hosts = [h for h, m in zip(hosts, mask) if m]
    shown = 0
    for i, host in enumerate(kept_hosts):
        if y[i] != pred[i] and shown < 40:
            print(f"  {host:40} true={y[i]:12} pred={pred[i]}")
            shown += 1

    # Plot
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=classes)
    fig, ax = plt.subplots(figsize=(14, 12))
    disp.plot(ax=ax, xticks_rotation=90, cmap="Blues", values_format="d")
    ax.set_title("Catalog consistency: page-text classifier vs catalog labels")
    fig.tight_layout()
    OUT.mkdir(exist_ok=True)
    fig.savefig(OUT / "confusion-matrix.png", dpi=150)
    print(f"\nSaved {OUT / 'confusion-matrix.png'}")

    # Save data for report
    report = {
        "total_hosts": len(labels),
        "hosts_with_text": len(hosts),
        "hosts_after_filter": int(len(y)),
        "classes": classes,
        "matrix": cm.tolist(),
        "counts": {c: int(counts[c]) for c in classes},
    }
    (OUT / "matrix-data.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Saved {OUT / 'matrix-data.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
