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
.venv/bin/python fetch-pages.py     # cache each host's homepage (~25 min from cold)
.venv/bin/python build-matrix.py    # ← writes docs/analysis/out/
```

Outputs land in `out/`:

- `confusion-matrix.png` — the matrix (counts + row-normalized side by side)
- `correlated-terms.md` — chi-squared **and** LinearSVC model-weight terms per category
- `high-confidence-errors.md` — hosts where the model is confident but disagrees
- `matrix-data.json` — raw numbers including model comparison and per-host top-3 predictions

## Result

**Accuracy: 90%** (3,800/4,213, 18 classes, 5-fold CV) — **balanced accuracy
67%**. Both numbers are correct and the gap between them is the whole story.

The audit covers every catalog host whose homepage yields usable text — 4,303 of
6,745 — and keeps the 18 classes with at least 20 labelled examples.

### The 23-point gap

`finance` is 53.1% of the catalog, so it is 56% of the sample. Accuracy asks
"how often is the model right", and the model is right about `finance` almost
always. Balanced accuracy asks "how often is it right *per class*", weighting
every category equally. LinearSVC scores 0.902 and 0.672.

Read the first number alone and the catalog looks nearly perfect. Read the second
and the real picture is that a third of our labels cannot be recovered from page
text. The second number is the one that means something.

### Model comparison

The audit compares several TF-IDF classifiers before using LinearSVC for the
confusion matrix, term weights and calibrated error review.

| Model | Accuracy | Balanced accuracy | Macro F1 | Weighted F1 |
| :--- | ---: | ---: | ---: | ---: |
| LinearSVC | 0.902 | 0.672 | 0.674 | 0.904 |
| LogisticRegression | 0.884 | 0.668 | 0.644 | 0.891 |
| MultinomialNB | 0.734 | 0.263 | 0.259 | 0.740 |

All three are reweighted toward the rare classes — `class_weight="balanced"` for
the two linear models, and a hand-computed inverse-frequency prior for naive
Bayes, which rejects the string `"balanced"` and only accepts an array. That
last part matters: without it the comparison was not a comparison, because two
models were being judged on how they handle a 2,359-example class while the
third was left to guess it.

The ranking is unchanged, and forcing naive Bayes off the dominant class shows
exactly how weak it is: its accuracy *fell* (0.792 → 0.734) while its macro F1
*rose* (0.197 → 0.259). A model that cannot do better than the dominant class
loses overall accuracy the moment it is forced to try the rare ones. Its
balanced accuracy of 0.263 is the honest summary.

### What is not measured at all

Nine of the 27 categories have fewer than 20 labelled examples and are dropped
before the matrix is built. They are not scored, and nothing above says so:

| Category | Examples | Category | Examples |
| :--- | ---: | :--- | ---: |
| `cdn` | 19 | `other` | 9 |
| `email` | 18 | `crypto` | 8 |
| `crash` | 11 | `sports` | 7 |
| `telecom` | 10 | `music` | 6 |
| | | `maps` | 2 |

`maps` has two examples — the category is effectively untested, and a user
routed by it gets no evidence at all that the label is right. The audit used to
be silent about this; `cdn` vanished from the matrix at one point with no
explanation, which is the kind of quiet change that is impossible to notice six
months later. The dropped classes are now printed and stored in
`matrix-data.json` as `dropped_classes`.

Read this number correctly:

- **It is consistency, not accuracy.** The model learns how well our own
  labels can be recovered from page text. 90% means about nine in ten of our
  labels are predictable from the page.
- **Highest F1:** `government` 0.97, `finance` 0.96, `education` 0.91, `news`
  0.87, `messaging` 0.83. These categories have strong, distinctive page
  signals.
- **Lowest F1:** `encyclopedia` 0.28, `video` 0.45, `social` 0.47, `transport`
  0.53 — some of these are infrastructure (page text is meaningless). But
  correlated terms and model-weight terms reveal potential miscategorizations.
- **`cdn` left the matrix.** At 20 labelled examples it only just cleared the
  `--min-class 20` floor; the catalog changes moved it under, so it is no
  longer measured. That is the filter working, not a regression — and it is
  also why the class count went 19 → 18 while the catalog more than doubled.

### Per-class metrics

| Class | Precision | Recall | F1 | Support |
| :--- | ---: | ---: | ---: | ---: |
| finance | 0.97 | 0.96 | 0.96 | 2359 |
| government | 0.98 | 0.97 | 0.97 | 879 |
| software | 0.66 | 0.74 | 0.70 | 159 |
| gaming | 0.66 | 0.70 | 0.68 | 66 |
| health | 0.85 | 0.75 | 0.80 | 55 |
| shopping | 0.55 | 0.63 | 0.59 | 71 |
| news | 0.87 | 0.87 | 0.87 | 114 |
| travel | 0.59 | 0.43 | 0.50 | 37 |
| ads | 0.61 | 0.70 | 0.65 | 43 |
| education | 0.93 | 0.89 | 0.91 | 161 |
| analytics | 0.59 | 0.72 | 0.65 | 32 |
| ai | 0.74 | 0.64 | 0.69 | 50 |
| transport | 0.68 | 0.43 | 0.53 | 35 |
| video | 0.37 | 0.56 | 0.45 | 45 |
| search | 0.80 | 0.50 | 0.62 | 24 |
| encyclopedia | 0.22 | 0.38 | 0.28 | 26 |
| social | 0.56 | 0.41 | 0.47 | 34 |
| messaging | 0.83 | 0.83 | 0.83 | 23 |
| **accuracy** | | | **0.90** | |
| **macro avg** | 0.69 | 0.67 | 0.67 | |
| **weighted avg** | 0.91 | 0.90 | 0.90 | |

### Correlated terms (chi-squared + model weight, top 5 per class)

| Class | Chi-squared top terms | Model weight top terms |
| :--- | :--- | :--- |
| finance | ve, und, sie, für, belediye | bank, banking, financial, id, для |
| government | belediye, meclis, belediyesi, başkan, beledi | belediye, belediyesi, gov, duyurular, beledi |
| software | github, copilot, azure, enterprise, developer | github, soon, plex, azure, git |
| gaming | game, games, doom, the elder, elder scrolls | game, games, com why, 401, of |
| health | doktor, tedavisi, cerrahisi, cerrahi, hastalıkları | doktor, medical, org, http www, health |
| shopping | giyim, amazon, aksesuar, ayakkabı, elbise | com tr, amazon, com why, mavi, shop |
| news | son dakika, dakika, yazarlar, abd, trump | hulu, 바로가기, yahoo, haberleri, medium |
| travel | uçak bileti, bileti, uçak, ucuz, otelleri | http www, flight, com why, www, homes |
| ads | publishers, advertisers, advertising, audience, publisher | publishers, affiliate, marketing, advertising, advertisers |
| education | akademik, fakültesi, araştırma, öğrenci, koordinatörlüğü | üniversitesi, öğrenci, edu, akademik, study |
| analytics | journeys, retention, analytics, replay, observability | http www, analytics, www, retention, your data |
| ai | kimi, models, deepseek, inference, ai | ai, models, character, kimi, deepseek |
| transport | gönderi, modeller, fiyat listesi, sürüşü, randevusu | maps, com tr, gönderi, kargo, limit |
| video | yeni bölüm, sevdiğim sensin, başkalarının hayatı, sensin, originals | http www, max, tv, originals, stream |
| search | gelişmiş, mleri, uygulamaları, oturum, com tr | engine, search, json, 2004, com why |
| encyclopedia | dictionary, kelime, words, philosophy, ancient | dictionary, org, kelime, türkçe, unavailable |
| social | random, vk, nba, happening, to share | match, nba, vk, com why, linkedin |
| messaging | 새창열림, chats, messages, calls, meetings | 새창열림, ai, calls, talk, messages |

**The chi-squared column is unreliable on large classes, and it is worth knowing
why.** `finance` used to be 68 examples with discriminative terms; at 2,359 it
is 56% of the sample, and chi-squared ranks by raw frequency association, so the
words that win are simply the common ones — `ve`, `und`, `sie`. The model-weight
column is unaffected and still reads `bank`, `banking`, `financial`.

Capping each class before the test was tried and **reverted**. It does fix
`finance`, and it wrecks everything else: shrinking a class to the size of a
rare one lets a bigram appearing in two small-class documents outscore a term
that actually characterises the class (`belediye, meclis, belediyesi` became
`oprocentowanie, karriere bvr`). The test is a frequency statistic, which makes
it readable on a large class and noisy on a small one — the opposite of what
this column needs. **Read the model-weight column.**

### High-confidence errors

Only 4 hosts where the model is confident (≥70%) but disagrees with the
catalog label:

| Host | Catalog label | Predicted | Confidence | Top 3 predictions |
| :--- | :--- | :--- | ---: | :--- |
| guven.com.tr | finance | health | 88% | health 88%, finance 4%, government 1% |
| display.ugc.bazaarvoice.com | software | finance | 83% | finance 83%, government 3%, video 2% |
| iqiyi.com | video | finance | 83% | finance 83%, government 3%, video 2% |
| googlesyndication.com | ads | search | 75% | search 75%, ads 13%, finance 4% |

These are the strongest candidates for mislabeled entries, and the three new
ones share a shape: `finance` is 56% of the sample, so a confident model falls
back on it for anything that looks commercial.

- `guven.com.tr` — a Turkish insurer ("güven" is also the common word for
  *trust*), which is why the text reads as health. The label is defensible;
  the page is just not distinctive.
- `bazaarvoice.com` — UGC review infrastructure. `software` looks right; the
  text is a customer-review platform, which a model reads as finance.
- `iqiyi.com` — a Chinese video platform. The `video` label is clearly right
  and the model is wrong here; the top-3 shows the finance prior overriding it.
- `googlesyndication.com` — Google's ad serving infrastructure, the label is
  debatable.

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

2. **Model comparison** (`build-matrix.py`): TF-IDF (1–2 grams, 20k features)
   is evaluated with LinearSVC, logistic regression and multinomial naive Bayes
   using 5-fold stratified cross-validation.

3. **Classification**: LinearSVC is kept for the confusion matrix, term weights
   and calibrated error review. Every host receives an out-of-fold prediction.

4. **Calibration**: `CalibratedClassifierCV` (sigmoid, 3-fold) provides
   probability estimates, enabling identification of high-confidence errors.

5. **Chi-squared test**: For each category, the 10 terms most strongly
   associated with that category are identified, revealing what drives
   each class and flagging potential miscategorizations.

6. **Model weight terms**: The fitted LinearSVC coefficients show which
   terms the model itself weighs most positively for each class — a
   complementary signal to chi-squared.

7. **Per-host predictions**: Each host's top-3 predicted categories with
   calibrated probabilities are recorded in `matrix-data.json` and shown in
   the high-confidence errors table.
