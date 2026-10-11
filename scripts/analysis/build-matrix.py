"""Train a classifier on cached page text and render a confusion matrix.

The catalog label is the ground truth. A TF-IDF + LinearSVC model is
cross-validated (5-fold) so every host receives an out-of-fold prediction.
The confusion matrix then shows how consistently our labels agree with what
a text model can recover.

- Model comparison across several text classifiers
- Per-class precision/recall/F1 (classification_report)
- Chi-squared correlated terms per category (what terms separate each class)
- LinearSVC coefficient terms per category (what the fitted model weighs)
- Calibrated top-3 predictions per host and high-confidence errors

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
PAGES = Path(__file__).resolve().parent / ".pages"
OUT = ROOT / "docs" / "analysis" / "out"
CATALOG = ROOT / "catalog.json"


def top_predictions(classes: list[str], row, limit: int = 3) -> list[dict[str, object]]:
    ranked = sorted(zip(classes, row), key=lambda item: item[1], reverse=True)[:limit]
    return [
        {"category": category, "probability": round(float(probability), 3)}
        for category, probability in ranked
    ]


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
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.feature_selection import chi2
    from sklearn.metrics import (
        classification_report,
        confusion_matrix,
        ConfusionMatrixDisplay,
    )
    from sklearn.model_selection import cross_val_predict, StratifiedKFold
    from sklearn.linear_model import LogisticRegression
    from sklearn.naive_bayes import MultinomialNB
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
    catalog_order = list(dict.fromkeys(labels.values()))
    classes = [c for c in catalog_order if c in set(y)]
    kept_hosts = [h for h, m in zip(hosts, mask) if m]

    print(f"{len(hosts)} hosts with text -> {len(y)} after class filter")
    print(f"{len(classes)} classes: {', '.join(classes)}")

    pipe = make_pipeline(
        TfidfVectorizer(sublinear_tf=True, min_df=2, ngram_range=(1, 2), max_features=20000),
        LinearSVC(C=1.0, class_weight="balanced", max_iter=5000),
    )
    cv = StratifiedKFold(n_splits=args.folds, shuffle=True, random_state=42)
    pred = cross_val_predict(pipe, X, y, cv=cv, n_jobs=-1)

    # --- 0. Model comparison ---
    print("\nModel comparison (5-fold CV):")
    models = [
        ("LinearSVC", LinearSVC(C=1.0, class_weight="balanced", max_iter=5000)),
        ("LogisticRegression", LogisticRegression(C=4.0, class_weight="balanced", max_iter=1000)),
        ("MultinomialNB", MultinomialNB()),
    ]
    model_comparison: list[dict[str, object]] = []
    for name, model in models:
        model_pipe = make_pipeline(
            TfidfVectorizer(sublinear_tf=True, min_df=2, ngram_range=(1, 2), max_features=20000),
            model,
        )
        model_pred = pred if name == "LinearSVC" else cross_val_predict(model_pipe, X, y, cv=cv, n_jobs=-1)
        model_report = classification_report(y, model_pred, labels=classes, output_dict=True)
        model_comparison.append({
            "model": name,
            "accuracy": float(model_report["accuracy"]),
            "macro_f1": float(model_report["macro avg"]["f1-score"]),
            "weighted_f1": float(model_report["weighted avg"]["f1-score"]),
        })
        print(
            f"  {name:18} "
            f"accuracy={model_report['accuracy']:.3f} "
            f"macro_f1={model_report['macro avg']['f1-score']:.3f} "
            f"weighted_f1={model_report['weighted avg']['f1-score']:.3f}"
        )

    cm = confusion_matrix(y, pred, labels=classes)
    np.set_printoptions(linewidth=200)
    print("\nConfusion matrix (rows=true, cols=predicted):")
    print(cm)

    # --- 1. Classification report (precision/recall/F1) ---
    report = classification_report(y, pred, labels=classes, output_dict=True)
    print("\nPer-class metrics:")
    print(f"  {'class':14} {'prec':>6} {'rec':>6} {'f1':>6} {'support':>7}")
    for c in classes:
        r = report[c]
        print(f"  {c:14} {r['precision']:6.2f} {r['recall']:6.2f} {r['f1-score']:6.2f} {r['support']:7.0f}")
    print(f"  {'accuracy':14} {report['accuracy']:6.2f}")
    print(f"  {'macro avg':14} {report['macro avg']['precision']:6.2f} "
          f"{report['macro avg']['recall']:6.2f} {report['macro avg']['f1-score']:6.2f}")
    print(f"  {'weighted avg':14} {report['weighted avg']['precision']:6.2f} "
          f"{report['weighted avg']['recall']:6.2f} {report['weighted avg']['f1-score']:6.2f}")

    # --- 2. Chi-squared correlated terms per category ---
    print("\nChi-squared correlated terms (top 10 per class):")
    vectorizer = TfidfVectorizer(sublinear_tf=True, min_df=2, ngram_range=(1, 2), max_features=20000)
    X_vec = vectorizer.fit_transform(X)
    feature_names = np.array(vectorizer.get_feature_names_out())
    correlated_terms: dict[str, list[tuple[str, float]]] = {}
    for i, c in enumerate(classes):
        class_mask = y == c
        chi2_class, _ = chi2(X_vec, class_mask.astype(int))
        top_indices = np.argsort(chi2_class)[-10:][::-1]
        terms = [(feature_names[j], float(chi2_class[j])) for j in top_indices]
        correlated_terms[c] = terms
        print(f"  {c:14} {', '.join(t for t, _ in terms[:5])}")

    # --- 2b. LinearSVC model terms per category ---
    print("\nLinearSVC weighted terms (top 10 per class):")
    term_model = LinearSVC(C=1.0, class_weight="balanced", max_iter=5000)
    term_model.fit(X_vec, y)
    model_terms: dict[str, list[tuple[str, float]]] = {}
    for class_index, c in enumerate(term_model.classes_):
        top_indices = np.argsort(term_model.coef_[class_index])[-10:][::-1]
        terms = [(feature_names[j], float(term_model.coef_[class_index][j])) for j in top_indices]
        model_terms[c] = terms
        print(f"  {c:14} {', '.join(t for t, _ in terms[:5])}")

    # --- 3. Calibrated probabilities -> high-confidence errors ---
    print("\nCalibrating for probability estimates...")
    cal_pipe = make_pipeline(
        TfidfVectorizer(sublinear_tf=True, min_df=2, ngram_range=(1, 2), max_features=20000),
        CalibratedClassifierCV(
            LinearSVC(C=1.0, class_weight="balanced", max_iter=5000),
            cv=3,
            method="sigmoid",
        ),
    )
    cal_pipe.fit(X, y)
    proba = cal_pipe.predict_proba(X)
    cal_pred = cal_pipe.predict(X)
    probability_classes = list(cal_pipe.classes_)

    # High-confidence errors: model is confident but wrong
    high_conf_errors: list[dict] = []
    predictions: list[dict] = []
    for i, host in enumerate(kept_hosts):
        true_label = y[i]
        pred_label = cal_pred[i]
        top3 = top_predictions(probability_classes, proba[i], limit=3)
        confidence = float(top3[0]["probability"])
        predictions.append({
            "host": host,
            "catalog_label": true_label,
            "predicted": pred_label,
            "confidence": round(confidence, 3),
            "top_predictions": top3,
        })
        if true_label != pred_label:
            high_conf_errors.append({
                "host": host,
                "true": true_label,
                "predicted": pred_label,
                "confidence": round(confidence, 3),
                "top_predictions": top3,
            })
    high_conf_errors.sort(key=lambda x: -x["confidence"])
    predictions.sort(key=lambda x: (x["catalog_label"], x["host"]))

    print(f"\nHigh-confidence errors (confidence >= 0.7, first 30):")
    hce_strong = [e for e in high_conf_errors if e["confidence"] >= 0.7]
    for e in hce_strong[:30]:
        print(f"  {e['host']:40} true={e['true']:12} pred={e['predicted']:12} conf={e['confidence']:.2f}")
    print(f"  ... total high-confidence errors: {len(hce_strong)}")

    # --- 4. Plot confusion matrix (raw + normalized side by side) ---
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(24, 11))

    disp1 = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=classes)
    disp1.plot(ax=ax1, xticks_rotation=90, cmap="Blues", values_format="d")
    ax1.set_title("Confusion Matrix (counts)")

    cm_norm = cm.astype("float") / cm.sum(axis=1, keepdims=True)
    cm_norm = np.nan_to_num(cm_norm)
    disp2 = ConfusionMatrixDisplay(confusion_matrix=cm_norm, display_labels=classes)
    disp2.plot(ax=ax2, xticks_rotation=90, cmap="Blues", values_format=".2f")
    ax2.set_title("Confusion Matrix (row-normalized)")

    fig.suptitle("Catalog consistency: page-text classifier vs catalog labels", fontsize=14)
    fig.tight_layout()
    OUT.mkdir(exist_ok=True)
    fig.savefig(OUT / "confusion-matrix.png", dpi=150)
    print(f"\nSaved {OUT / 'confusion-matrix.png'}")

    # --- 5. Write correlated-terms.md ---
    lines = ["# Correlated Terms per Category", ""]
    lines.append("Two signals are shown for each category:")
    lines.append("")
    lines.append("- **Chi-squared** terms are the words/bigrams most statistically associated with the category.")
    lines.append("- **Model weight** terms are the words/bigrams the fitted LinearSVC model weighs most positively.")
    lines.append("")
    for c in classes:
        lines.append(f"## {c}")
        lines.append("")
        lines.append("### Chi-squared")
        lines.append("")
        lines.append("| Term | Score |")
        lines.append("| :--- | ---: |")
        for term, score in correlated_terms[c]:
            lines.append(f"| {term} | {score:.1f} |")
        lines.append("")
        lines.append("### Model weight")
        lines.append("")
        lines.append("| Term | Weight |")
        lines.append("| :--- | ---: |")
        for term, score in model_terms.get(c, []):
            lines.append(f"| {term} | {score:.3f} |")
        lines.append("")
    (OUT / "correlated-terms.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Saved {OUT / 'correlated-terms.md'}")

    # --- 6. Write high-confidence-errors.md ---
    lines = ["# High-Confidence Errors", ""]
    lines.append("Hosts where the model is confident (>=70%) but disagrees with")
    lines.append("the catalog label. These are the strongest candidates for")
    lines.append("mislabeled entries.")
    lines.append("")
    lines.append(f"Total: {len(hce_strong)} hosts")
    lines.append("")
    lines.append("| Host | Catalog label | Predicted | Confidence | Top 3 predictions |")
    lines.append("| :--- | :--- | :--- | ---: | :--- |")
    for e in hce_strong:
        top3 = ", ".join(
            f"{p['category']} {p['probability']:.0%}" for p in e.get("top_predictions", [])
        )
        lines.append(f"| {e['host']} | {e['true']} | {e['predicted']} | {e['confidence']:.0%} | {top3} |")
    lines.append("")
    (OUT / "high-confidence-errors.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Saved {OUT / 'high-confidence-errors.md'}")

    # --- 7. Save matrix-data.json (extended) ---
    report_data = {
        "total_hosts": len(labels),
        "hosts_with_text": len(hosts),
        "hosts_after_filter": int(len(y)),
        "classes": classes,
        "matrix": cm.tolist(),
        "matrix_normalized": cm_norm.tolist(),
        "counts": {c: int(counts[c]) for c in classes},
        "model_comparison": model_comparison,
        "classification_report": {c: report[c] for c in classes},
        "accuracy": report["accuracy"],
        "macro_avg": report["macro avg"],
        "weighted_avg": report["weighted avg"],
        "correlated_terms": {c: correlated_terms[c] for c in classes},
        "model_terms": {c: model_terms.get(c, []) for c in classes},
        "predictions": predictions,
        "high_confidence_errors": hce_strong,
    }
    (OUT / "matrix-data.json").write_text(json.dumps(report_data, indent=2), encoding="utf-8")
    print(f"Saved {OUT / 'matrix-data.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
