# Analysis: catalog consistency

This directory holds a one-off analysis that fetches homepage text for the
hosts in `catalog.json`, trains a text classifier (TF-IDF + LinearSVC) on
our labels, and produces a confusion matrix showing how consistently our
labels agree with what a text model can recover.

**Not part of the shipped catalog pipeline.** The catalog repo's `scripts/`
are standard-library-only; this analysis needs `scikit-learn` and
`matplotlib`. It is excluded from `test/test.sh`.

## Usage

```bash
# 1. Install deps (arm64 wheels for Python 3.11+)
pip3 install scikit-learn matplotlib

# 2. Fetch pages (~3 min, cached under pages/)
python3 fetch-pages.py

# 3. Train + render matrix
python3 build-matrix.py
```

Outputs land in `out/`:

- `confusion-matrix.png` — the matrix (counts + row-normalized side by side)
- `correlated-terms.md` — chi-squared correlated terms per category
- `high-confidence-errors.md` — hosts where the model is confident but disagrees
- `matrix-data.json` — raw numbers

## Result

**Accuracy: 66%** (543/823, 19 classes, 5-fold CV).

Read this number correctly:

- **It is consistency, not accuracy.** The model learns how well our own
  labels can be recovered from page text. 66% means about two-thirds of our
  labels are predictable from the page.
- **Highest F1:** `ai`, `finance`, `government`, `health`, `messaging` —
  all at 0.80. These categories have strong, distinctive page signals.
- **Lowest F1:** `cdn` (0.43), `social` (0.44), `travel` (0.41) — some
  of these are infrastructure (page text is meaningless). But examples like
  `search` category correlating with "gmail rseller" suggest some hosts may
  be miscategorized.

### Per-class metrics

| Class | Precision | Recall | F1 | Support |
| :--- | ---: | ---: | ---: | ---: |
| ads | 0.60 | 0.68 | 0.64 | 40 |
| ai | 0.86 | 0.75 | 0.80 | 48 |
| analytics | 0.60 | 0.75 | 0.67 | 32 |
| cdn | 0.41 | 0.45 | 0.43 | 20 |
| education | 0.57 | 0.50 | 0.53 | 26 |
| encyclopedia | 0.48 | 0.54 | 0.51 | 26 |
| finance | 0.86 | 0.75 | 0.80 | 68 |
| gaming | 0.65 | 0.69 | 0.67 | 29 |
| government | 0.72 | 0.89 | 0.80 | 55 |
| health | 0.85 | 0.75 | 0.80 | 55 |
| messaging | 0.71 | 0.91 | 0.80 | 22 |
| news | 0.78 | 0.75 | 0.77 | 57 |
| search | 0.68 | 0.54 | 0.60 | 24 |
| shopping | 0.70 | 0.66 | 0.68 | 71 |
| social | 0.42 | 0.45 | 0.44 | 31 |
| software | 0.65 | 0.63 | 0.64 | 111 |
| transport | 0.65 | 0.43 | 0.52 | 35 |
| travel | 0.36 | 0.48 | 0.41 | 29 |
| video | 0.57 | 0.57 | 0.57 | 44 |
| **accuracy** | | | **0.66** | |
| **macro avg** | 0.64 | 0.64 | 0.63 | |
| **weighted avg** | 0.67 | 0.66 | 0.66 | |

### Correlated terms (chi-squared, top 5 per class)

| Class | Top correlated terms |
| :--- | :--- |
| ads | publishers, advertisers, affiliate marketing, advertising, advertiser |
| ai | kimi, k3, kimi k3, models, deepseek |
| analytics | journeys, customer engagement, session replay, analytics, retention |
| cdn | cdn, not found, 404, 404 not, yandex |
| education | graduate, admissions, undergraduate, restricted, academics |
| encyclopedia | dictionary, sözlük, encyclopedia, commons, türk dil |
| finance | bankacılık, sigortası, emeklilik, sigorta, mevduat |
| gaming | mihoyo, legends, game, royale, tab opens |
| government | gov, müdürlüğü, cumhurbaşkanlığı, genel müdürlüğü, başkanlığı |
| health | doktor, hasta, randevu, klinik, tıbbi |
| messaging | telegram, telegram for, video calls, messenger, 새창열림 |
| news | haberleri, son dakika, ekonomi, oldu, abd |
| search | hakkında com, rseller, şartlar uygulamaları, gmail rseller, google gmail |
| shopping | giyim, amazon com, amazon, com inc, ayakkabı |
| social | vk, threads, qq, continue with, random |
| software | plex, 365 microsoft, english united, education microsoft, software |
| transport | gönderi, fiyat listesi, modeller, servis randevusu, sürüşü |
| travel | uçak bileti, bileti, uçak, ucuz uçak, ucuz |
| video | yeni bölüm, peacock, diziler, ana haber, bölüm |

### High-confidence errors

Only 1 host where the model is confident (≥70%) but disagrees with the
catalog label:

| Host | Catalog label | Predicted | Confidence |
| :--- | :--- | :--- | ---: |
| googlesyndication.com | ads | search | 77% |

This is Google's ad serving infrastructure — the label is debatable.

## What the matrix does and does not measure

It does **not** measure whether our labels are *correct* — there is no
independent ground truth. It measures **self-consistency**: given the page
text, can a model recover our label? High diagonal = our labels are
predictable from page content. Off-diagonal = our label disagrees with what
the text suggests (either the label is wrong, or the page is not
representative of the category).

Infrastructure hosts (CDNs, analytics, ads) have no meaningful page text,
so they are naturally filtered out by `--min-text`.

## Methodology

1. **Text extraction** (`fetch-pages.py`): Fetches each host's homepage and
   extracts `<title>`, meta description, meta keywords, headings (h1–h6),
   and body text. Title/meta/headings are placed first because they carry
   the strongest category signal.

2. **Classification** (`build-matrix.py`): TF-IDF (1–2 grams, 20k features)
   + LinearSVC with 5-fold stratified cross-validation. Every host receives
   an out-of-fold prediction.

3. **Calibration**: `CalibratedClassifierCV` (sigmoid, 3-fold) provides
   probability estimates, enabling identification of high-confidence errors.

4. **Chi-squared test**: For each category, the 10 terms most strongly
   associated with that category are identified, revealing what drives
   each class and flagging potential miscategorizations.
