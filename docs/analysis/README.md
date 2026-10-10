# Analysis: catalog consistency

This directory holds the results and methodology of an audit that fetches
homepage text for the hosts in `catalog.json`, trains a text classifier
(TF-IDF + LinearSVC) on our labels, and produces a confusion matrix showing how
consistently our labels agree with what a text model can recover.

**The tool lives in [`scripts/analysis/`](../../scripts/analysis/); its output
lands here.** It is not part of the shipped catalog pipeline — the rest of
`scripts/` is standard-library-only, while the audit needs `scikit-learn` and
`matplotlib`, and `test/test.sh` does not run it.

## Usage

```bash
cd scripts/analysis
python3 -m venv .venv && .venv/bin/pip install scikit-learn matplotlib
.venv/bin/python fetch-pages.py     # cache each host's homepage (~3 min)
.venv/bin/python build-matrix.py    # ← writes docs/analysis/out/
```

Outputs land in `out/`:

- `confusion-matrix.png` — the matrix (counts + row-normalized side by side)
- `correlated-terms.md` — chi-squared **and** LinearSVC model-weight terms per category
- `high-confidence-errors.md` — hosts where the model is confident but disagrees
- `matrix-data.json` — raw numbers including per-host top-3 predictions

## Result

**Accuracy: 84%** (1,545/1,844, 19 classes, 5-fold CV).

Read this number correctly:

- **It is consistency, not accuracy.** The model learns how well our own
  labels can be recovered from page text. 84% means about five-sixths of our
  labels are predictable from the page.
- **Highest F1:** `education` 0.93, `government` 0.97, `news` 0.91, `health`
  0.81, `messaging` 0.87. These categories have strong, distinctive page
  signals.
- **Lowest F1:** `cdn` 0.44, `social` 0.40, `travel` 0.44, `encyclopedia` 0.42 —
  some of these are infrastructure (page text is meaningless). But correlated
  terms and model-weight terms reveal potential miscategorizations.

### Per-class metrics

| Class | Precision | Recall | F1 | Support |
| :--- | ---: | ---: | ---: | ---: |
| government | 0.97 | 0.97 | 0.97 | 883 |
| software | 0.58 | 0.68 | 0.63 | 111 |
| health | 0.91 | 0.73 | 0.81 | 55 |
| shopping | 0.62 | 0.66 | 0.64 | 71 |
| news | 0.94 | 0.88 | 0.91 | 115 |
| ads | 0.68 | 0.70 | 0.69 | 40 |
| education | 0.95 | 0.90 | 0.93 | 161 |
| gaming | 0.60 | 0.72 | 0.66 | 29 |
| analytics | 0.68 | 0.66 | 0.67 | 32 |
| cdn | 0.40 | 0.50 | 0.44 | 20 |
| travel | 0.41 | 0.48 | 0.44 | 29 |
| finance | 0.79 | 0.79 | 0.79 | 68 |
| ai | 0.81 | 0.71 | 0.76 | 48 |
| transport | 0.68 | 0.43 | 0.53 | 35 |
| video | 0.57 | 0.61 | 0.59 | 44 |
| search | 0.71 | 0.50 | 0.59 | 24 |
| encyclopedia | 0.36 | 0.50 | 0.42 | 26 |
| social | 0.41 | 0.39 | 0.40 | 31 |
| messaging | 0.83 | 0.91 | 0.87 | 22 |
| **accuracy** | | | **0.84** | |
| **macro avg** | 0.68 | 0.67 | 0.67 | |
| **weighted avg** | 0.85 | 0.84 | 0.84 | |

### Correlated terms (chi-squared + model weight, top 5 per class)

| Class | Chi-squared top terms | Model weight top terms |
| :--- | :--- | :--- |
| government | belediye, meclis, belediyesi, başkan, beledi | belediye, belediyesi, meclis, başkan, beledi |
| software | enterprise, software, plex, developer, 365 microsoft | xs, plex, uv, software, web app |
| health | doktor, tedavisi, patients, cerrahisi, hasta | doktor, medical, patients, hasta, klinik |
| shopping | amazon, giyim, aksesuar, elbise, ayakkabı | amazon, shop, zara, com why, valid |
| news | son dakika, dakika, yazarlar, trump, abd | 바로가기, hulu, yahoo, 中文, haberleri |
| ads | publishers, advertisers, affiliate marketing, advertising, advertiser | publishers, marketing, advertising, affiliate, advertisers |
| education | akademik, fakültesi, araştırma, koordinatörlüğü, öğrenci | üniversitesi, öğrenci, akademik, araştırma, edu |
| gaming | legends, game, games, royale, tab opens | game, games, path, legends, save the |
| analytics | journeys, customer engagement, retention, analytics, session replay | analytics, retention, vercel, http www, your data |
| cdn | cdn, not found, 404, bunny net, ddos | javascript, cdn, not found, access denied, denied |
| travel | uçak bileti, bileti, uçak, ucuz, otelleri | com why, http www, bileti, uçak bileti, airbnb |
| finance | sigortası, bankacılık, mevduat, emeklilik, sigorta | bitcoin, mastercard, cache, crypto, quick |
| ai | kimi, k3, models, inference, deepseek | ai, models, kimi, k3, research |
| transport | gönderi, modeller, konfigüratör, fiyat listesi, test sürüşü | maps, gönderi, kargo, limit, fiyat listesi |
| video | yeni bölüm, diziler, 99 mo, sevdiğim sensin, başkalarının hayatı | tv, max, syntax, originals, column |
| search | gmail, şartlar, tr 2026, gelişmiş, mleri | search, engine, 2004, resul, com |
| encyclopedia | dictionary, sözlük, vocabulary, words, century | dictionary, sözlük, downtime, org, articles |
| social | random, happening, find your, nba, to share | nba, match, facebook, com why, opera |
| messaging | messenger, 새창열림, messages, calls, telegram | messenger, ai, calls, talk, 새창열림 |

### High-confidence errors

Only 1 host where the model is confident (≥70%) but disagrees with the
catalog label:

| Host | Catalog label | Predicted | Confidence | Top 3 predictions |
| :--- | :--- | :--- | ---: | :--- |
| googlesyndication.com | ads | search | 80% | search 80%, ads 4%, government 2% |

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

5. **Model weight terms**: The fitted LinearSVC coefficients show which
   terms the model itself weighs most positively for each class — a
   complementary signal to chi-squared.

6. **Per-host predictions**: Each host's top-3 predicted categories with
   calibrated probabilities are recorded in `matrix-data.json` and shown in
   the high-confidence errors table.