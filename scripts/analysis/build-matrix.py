"""Train a classifier on cached page text and render a confusion matrix.

The catalog label is the ground truth. A TF-IDF + LinearSVC model is
cross-validated (5-fold) so every host receives an out-of-fold prediction.
The confusion matrix then shows how consistently our labels agree with what
a text model can recover.

- Model comparison across several text classifiers
- Per-class precision/recall/F1 (classification_report)
- Chi-squared correlated terms per category (what terms separate each class)
- LinearSVC coefficient terms per category (what the fitted model weighs)
- Out-of-fold calibrated top-3 predictions per host and high-confidence errors

Usage:
    python3 build-matrix.py [--min-text 100] [--min-class 2] [--folds 5]
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

# The multilingual sentence-embedding model compared against TF-IDF. The corpus
# is not English-only (Turkish, German, Korean, Russian, Chinese), and a
# bag-of-words model keeps those languages apart while a sentence embedding maps
# them into one space — so the row is a genuinely different representation, not
# a different head on the same features.
EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
EMBED_CACHE = Path(__file__).resolve().parent / ".embeddings.npz"

# Below this many examples a category's F1 is reported but should not be read as
# a measurement. A class seen three times can only ever be seen once per fold.
THIN_SUPPORT = 20


def load_embeddings(hosts: list[str], texts: list[str], model_name: str):
    """Embed homepage texts into vectors, cached by (model, host list).

    `sentence_transformers` is imported lazily so the audit still runs without
    the heavy dependency; the caller decides what to do when it is missing.
    Embeddings are cached under `.embeddings.npz` (git-ignored) because the
    first encode of ~4.5k pages is minutes of CPU work and nothing about it
    changes between runs on the same cache.
    """
    import numpy as np

    if EMBED_CACHE.exists():
        cached = np.load(EMBED_CACHE, allow_pickle=True)
        if str(cached["model"]) == model_name and list(cached["hosts"]) == list(hosts):
            print(f"embeddings: reused cache for {len(hosts)} hosts")
            return cached["vectors"]

    from sentence_transformers import SentenceTransformer

    print(f"embeddings: encoding {len(texts)} hosts with {model_name} (first run is slow)")
    model = SentenceTransformer(model_name)
    vectors = np.asarray(
        model.encode(texts, batch_size=32, show_progress_bar=True, normalize_embeddings=True),
        dtype="float32",
    )
    np.savez(
        str(EMBED_CACHE),
        hosts=np.array(list(hosts), dtype=object),
        vectors=vectors,
        model=model_name,
    )
    return vectors


def top_predictions(classes: list[str], row, limit: int = 3) -> list[dict[str, object]]:
    ranked = sorted(zip(classes, row), key=lambda item: item[1], reverse=True)[:limit]
    return [
        {"category": category, "probability": round(float(probability), 3)}
        for category, probability in ranked
    ]


def load_pages(min_text: int) -> tuple[dict[str, str], dict[str, int]]:
    """Usable pages, plus every cached host's length so the rest can be explained.

    `min_text` counts characters, not bytes — a page of Turkish or Chinese text
    crosses the threshold with far fewer bytes, and measuring the file size
    instead quietly filed those hosts under the wrong reason.
    """
    pages: dict[str, str] = {}
    lengths: dict[str, int] = {}
    for f in PAGES.glob("*.txt"):
        text = f.read_text(encoding="utf-8", errors="replace")
        lengths[f.stem] = len(text)
        if len(text) >= min_text:
            pages[f.stem] = text
    return pages, lengths


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-text", type=int, default=100)
    ap.add_argument(
        "--min-class",
        type=int,
        default=2,
        help="keep a category with at least this many labelled examples",
    )
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
        balanced_accuracy_score,
        classification_report,
        confusion_matrix,
        ConfusionMatrixDisplay,
    )
    from sklearn.model_selection import cross_val_predict, StratifiedKFold
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression, RidgeClassifier, SGDClassifier
    from sklearn.naive_bayes import MultinomialNB
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.pipeline import make_pipeline
    from sklearn.svm import LinearSVC
    from sklearn.tree import DecisionTreeClassifier

    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    labels = catalog["categories"]
    pages, lengths = load_pages(args.min_text)

    # Why the unmeasured hosts are unmeasured, over the catalog only — the cache
    # holds hosts the catalog has since dropped, and counting those would inflate
    # every bucket. "No usable page text" is not one thing: a host that answers
    # nothing cannot be fixed by fetching harder, and one that answers a stub
    # needs different handling. The split is recorded so no gap goes unexplained.
    never_fetched = [h for h in labels if h not in lengths]
    no_response = [h for h in labels if lengths.get(h) == 0]
    too_short = [h for h in labels if 0 < lengths.get(h, 0) < args.min_text]
    unmeasured = {
        "min_text": args.min_text,
        "never_fetched": len(never_fetched),
        "no_response": len(no_response),
        "too_short": len(too_short),
        "dropped_by_class_filter": 0,  # filled once the class floor is applied
    }

    # Keep only hosts that have text AND are in the catalog.
    hosts = sorted(h for h in pages if h in labels)
    y = np.array([labels[h] for h in hosts])
    X = np.array([pages[h] for h in hosts])

    counts = collections.Counter(y)
    keep = {c for c, n in counts.items() if n >= args.min_class}
    # A class that drops below the floor leaves the matrix silently, and a
    # reader comparing two runs sees a lower class count with no explanation.
    dropped = {c: n for c, n in counts.items() if n < args.min_class}
    if dropped:
        print(
            f"dropped below --min-class {args.min_class}: "
            + ", ".join(f"{c} ({n} examples)" for c, n in sorted(dropped.items()))
        )
    mask = np.array([c in keep for c in y])
    X, y = X[mask], y[mask]
    catalog_order = list(dict.fromkeys(labels.values()))
    classes = [c for c in catalog_order if c in set(y)]
    kept_hosts = [h for h, m in zip(hosts, mask) if m]

    print(f"{len(hosts)} hosts with text -> {len(y)} after class filter")
    print(f"{len(classes)} classes: {', '.join(classes)}")

    # A category with three examples cannot be split five ways. Rather than drop
    # it - which is how nine of the catalog's categories went unmeasured for the
    # whole history of this audit - the fold count drops to meet the smallest
    # class. `maps` has 3 examples, so the matrix is 3-fold and every category is
    # present. The trade is real and it is recorded: a class seen once per fold
    # yields a per-class F1 that is nearly a coin toss, which is why thin classes
    # are flagged rather than quietly averaged into the headline.
    min_support = min(counts[c] for c in classes)
    n_splits = max(2, min(args.folds, min_support))
    if n_splits != args.folds:
        print(
            f"folds reduced {args.folds} -> {n_splits}: the smallest class has "
            f"{min_support} example(s)"
        )
    thin = {c: int(counts[c]) for c in classes if counts[c] < THIN_SUPPORT}
    if thin:
        print(
            f"thin evidence (< {THIN_SUPPORT} examples), treat these F1 scores as indicative: "
            + ", ".join(f"{c} {n}" for c, n in sorted(thin.items(), key=lambda kv: kv[1]))
        )

    # A score describes the hosts that produced text, not the category. Print the
    # difference so nobody reads a gaming F1 as a statement about 360 hosts when
    # it was computed on 69.
    catalog_counts_all = collections.Counter(labels.values())
    print(f"\ncoverage: {len(y)} of {len(labels)} catalog hosts ({len(y) / len(labels):.0%})")
    print(
        f"  unexplained-by-design: never fetched {unmeasured['never_fetched']}, "
        f"no response {unmeasured['no_response']}, "
        f"under {unmeasured['min_text']} chars {unmeasured['too_short']}, "
        f"class filter {unmeasured['dropped_by_class_filter']}"
    )
    worst = sorted(
        ((c, catalog_counts_all[c], int(counts.get(c, 0))) for c in classes),
        key=lambda t: t[2] / t[1],
    )[:5]
    for c, total, seen in worst:
        print(f"  thinnest: {c:14} {seen:4}/{total:<5} measured ({seen / total:.0%})")

    pipe = make_pipeline(
        TfidfVectorizer(sublinear_tf=True, min_df=2, ngram_range=(1, 2), max_features=20000),
        LinearSVC(C=1.0, class_weight="balanced", max_iter=5000, random_state=42),
    )
    # LinearSVC is seeded, and it has to be. liblinear shuffles its dual
    # coordinate descent from the OS entropy when random_state is None, so two
    # runs on identical input produced coefficient tables differing around the
    # sixth digit - 277 changed lines in a committed artifact, none of them a
    # finding. Every LinearSVC in this file takes the same seed.
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    pred = cross_val_predict(pipe, X, y, cv=cv, n_jobs=-1)

    # --- 0. Model comparison ---
    print("\nModel comparison (5-fold CV):")
    # All three are reweighted toward the rare classes. LinearSVC and logistic
    # regression get it through class_weight; naive Bayes has no such parameter
    # and — checked against sklearn 1.9 — does not accept the "balanced" string
    # for class_prior either, only an array. So the balanced prior is computed
    # the way sklearn documents it: inversely proportional to class frequency.
    # Without this the comparison is not a comparison: the other two were being
    # judged on how well they handle the 2,359-example finance class while naive
    # Bayes was left to guess it.
    balanced_prior = np.array([1.0 / counts[c] for c in classes], dtype=float)
    balanced_prior = balanced_prior / balanced_prior.sum()
    models = [
        ("LinearSVC", LinearSVC(C=1.0, class_weight="balanced", max_iter=5000, random_state=42)),
        ("LogisticRegression", LogisticRegression(C=4.0, class_weight="balanced", max_iter=1000)),
        ("MultinomialNB", MultinomialNB(class_prior=balanced_prior)),
        # The linear/probabilistic family, complete: ridge and SGD are the two
        # nearest neighbours of the witness and the reason it was chosen.
        ("RidgeClassifier", RidgeClassifier(alpha=1.0, class_weight="balanced", random_state=42)),
        ("SGDClassifier", SGDClassifier(loss="hinge", class_weight="balanced", max_iter=5000, random_state=42)),
        # Non-linear heads. On sparse lexical features these are expected to
        # trail the linear models — which is the point of measuring rather than
        # asserting it. RandomForest accepts the sparse matrix directly, so
        # nothing is densified.
        ("DecisionTreeClassifier", DecisionTreeClassifier(class_weight="balanced", random_state=42)),
        ("RandomForestClassifier", RandomForestClassifier(n_estimators=100, class_weight="balanced", random_state=42, n_jobs=-1)),
        # KNN has no class_weight parameter, so it cannot be reweighted the way
        # the others are and starts at a structural disadvantage on balanced
        # accuracy. The confound is recorded rather than hidden.
        ("KNeighborsClassifier", KNeighborsClassifier(weights="distance")),
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
            # The honest number. finance is 56% of the sample, so accuracy
            # mostly reports how well a model predicts finance.
            "balanced_accuracy": float(balanced_accuracy_score(y, model_pred)),
            "macro_f1": float(model_report["macro avg"]["f1-score"]),
            "weighted_f1": float(model_report["weighted avg"]["f1-score"]),
        })
        print(
            f"  {name:18} "
            f"accuracy={model_report['accuracy']:.3f} "
            f"balanced={balanced_accuracy_score(y, model_pred):.3f} "
            f"macro_f1={model_report['macro avg']['f1-score']:.3f} "
            f"weighted_f1={model_report['weighted avg']['f1-score']:.3f}"
        )

    # The embedding row is a different *representation* (dense sentence vectors,
    # multilingual) with the same logistic head. If the dependency is missing
    # the run still completes — but it completes with one row fewer, so the
    # committed table must match the run that produced it.
    embedding_ran = False
    try:
        X_emb = load_embeddings(kept_hosts, list(X), EMBED_MODEL)
        emb_pipe = make_pipeline(
            LogisticRegression(C=4.0, class_weight="balanced", max_iter=1000)
        )
        emb_pred = cross_val_predict(emb_pipe, X_emb, y, cv=cv, n_jobs=-1)
        emb_report = classification_report(y, emb_pred, labels=classes, output_dict=True)
        model_comparison.append({
            "model": "MultilingualEmbeddingLogReg",
            "accuracy": float(emb_report["accuracy"]),
            "balanced_accuracy": float(balanced_accuracy_score(y, emb_pred)),
            "macro_f1": float(emb_report["macro avg"]["f1-score"]),
            "weighted_f1": float(emb_report["weighted avg"]["f1-score"]),
        })
        embedding_ran = True
        print(
            f"  {'MultilingualEmbLogReg':18} "
            f"accuracy={emb_report['accuracy']:.3f} "
            f"balanced={balanced_accuracy_score(y, emb_pred):.3f} "
            f"macro_f1={emb_report['macro avg']['f1-score']:.3f} "
            f"weighted_f1={emb_report['weighted avg']['f1-score']:.3f}  ({EMBED_MODEL})"
        )
    except ImportError:
        print(
            "  MultilingualEmbLogReg  SKIPPED — sentence-transformers not installed\n"
            "    install with: .venv/bin/pip install sentence-transformers",
            file=sys.stderr,
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
    # Chi-squared is kept uncapped. Capping oversized classes was tried to stop
    # finance returning stopwords once it reached 2,359 examples, and it does
    # fix that class - but it wrecks the rest, because shrinking a class to the
    # same size as a rare one lets a bigram appearing in two small-class
    # documents outscore a term that actually characterises government
    # (`belediye, meclis, belediyesi` became `oprocentowanie, karriere bvr`).
    # The test is a frequency statistic; it is readable on a large class and
    # noisy on a small one, which is the opposite of what this column needs.
    # Read the model-weight column instead when a class is big.
    for c in classes:
        class_mask = y == c
        chi2_class, _ = chi2(X_vec, class_mask.astype(int))
        top_indices = np.argsort(chi2_class)[-10:][::-1]
        terms = [(feature_names[j], float(chi2_class[j])) for j in top_indices]
        correlated_terms[c] = terms
        print(f"  {c:14} {', '.join(t for t, _ in terms[:5])}")

    # --- 2b. LinearSVC model terms per category ---
    print("\nLinearSVC weighted terms (top 10 per class):")
    term_model = LinearSVC(C=1.0, class_weight="balanced", max_iter=5000, random_state=42)
    term_model.fit(X_vec, y)
    model_terms: dict[str, list[tuple[str, float]]] = {}
    for class_index, c in enumerate(term_model.classes_):
        top_indices = np.argsort(term_model.coef_[class_index])[-10:][::-1]
        terms = [(feature_names[j], float(term_model.coef_[class_index][j])) for j in top_indices]
        model_terms[c] = terms
        print(f"  {c:14} {', '.join(t for t, _ in terms[:5])}")

    # --- 3. Calibrated probabilities -> high-confidence errors ---
    print("\nCalibrating for probability estimates...")
    # Calibration runs inside the fold, so it can only split what a training
    # fold holds: the outer count alone is not the constraint. The smallest class
    # keeps `min_support - ceil(min_support / n_splits)` examples in each training
    # fold, and 3-fold cross-validation needs at least 3 of them, so the inner
    # count must stay at or below that.
    smallest_train = min_support - (-(-min_support // n_splits))
    if smallest_train < 2:
        raise SystemExit(
            "the smallest class leaves fewer than 2 examples in a training fold, "
            "so a calibrator cannot be split — raise --min-class"
        )
    inner_cv = max(2, min(3, smallest_train))
    cal_pipe = make_pipeline(
        TfidfVectorizer(sublinear_tf=True, min_df=2, ngram_range=(1, 2), max_features=20000),
        CalibratedClassifierCV(
            LinearSVC(C=1.0, class_weight="balanced", max_iter=5000, random_state=42),
            cv=inner_cv,
            method="sigmoid",
        ),
    )
    # Out of fold, like the confusion matrix above. A probability read from a
    # model fitted on all of X measures recall, not confidence: the model has
    # already seen the host it is now "sure" about, which is why an in-sample
    # confidence lists a host as a confident error in one place and predicts it
    # correctly in the per-host table. cross_val_predict re-fits per fold, so a
    # host's probability comes from a model that never saw it.
    proba = cross_val_predict(cal_pipe, X, y, cv=cv, method="predict_proba", n_jobs=-1)
    # The predict_proba columns follow the fitted estimator's classes_, which is
    # np.unique(y) — sorted. Keep that order for the top-k lookup.
    probability_classes = sorted({str(label) for label in y})
    cal_pred = [probability_classes[int(i)] for i in proba.argmax(axis=1)]

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
    # Coverage matters as much as the score. A class where 81% of the hosts
    # yield no page text reports an F1 for the 19% that did, and reading that
    # as a statement about the category is the mistake this table prevents.
    catalog_counts = collections.Counter(labels.values())
    coverage = {
        c: {
            "in_catalog": int(catalog_counts[c]),
            "measured": int(counts.get(c, 0)),
        }
        for c in sorted(catalog_counts)
    }
    unmeasured["dropped_by_class_filter"] = len(hosts) - len(y)
    report_data = {
        "total_hosts": len(labels),
        "measured_hosts": int(len(y)),
        "hosts_with_text": len(hosts),
        "hosts_after_filter": int(len(y)),
        "classes": classes,
        "dropped_classes": dropped,
        "thin_classes": thin,
        "folds": n_splits,
        "coverage": coverage,
        "unmeasured": unmeasured,
        "matrix": cm.tolist(),
        "matrix_normalized": cm_norm.tolist(),
        "counts": {c: int(counts[c]) for c in classes},
        "model_comparison": model_comparison,
        "embedding_model": EMBED_MODEL if embedding_ran else None,
        "classification_report": {c: report[c] for c in classes},
        "accuracy": report["accuracy"],
        # finance is 56% of the sample, so accuracy and balanced accuracy differ
        # by 23 points. Quoting only the first is how a catalog gets told its
        # labels are 90% recoverable when per-class they are about 67%.
        "balanced_accuracy": float(balanced_accuracy_score(y, pred)),
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
