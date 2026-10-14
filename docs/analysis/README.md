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

**Accuracy: 89%** (4,045/4,565, 27 classes, 3-fold CV) — **balanced accuracy
60%**. Both numbers are correct and the gap between them is the whole story.

The audit measures **every category in the catalog**. It covers the 4,565 hosts
whose homepage yields usable text, and keeps all 27 — including `maps`, which has
3 examples.

### The 29-point gap

`finance` is 53.1% of the catalog. Accuracy asks "how often is the model right",
and the model is right about `finance` almost always. Balanced accuracy asks
"how often is it right *per category*", weighting all 27 equally. LinearSVC
scores 0.886 and 0.595.

Read the first number alone and the catalog looks nearly perfect. Read the second
and the real picture is that two of every three labels cannot be recovered from
page text. The second number is the one that means something.

### Why 3 folds and not 5

`maps` has three labelled examples, so the matrix cannot be split five ways.
Rather than drop the category — which is how nine of them went unmeasured for
the entire history of this audit — the fold count drops to meet the smallest
class. Every category is present; the cost is that a class seen once per fold
yields an F1 that is close to a coin toss.

Eight categories are **thin** (under 20 examples) and their F1 should be read as
indicative, not measured: `maps` 3, `sports` 7, `music` 8, `crypto` 8, `other`
10, `crash` 11, `telecom` 11, `email` 19. They are listed in `matrix-data.json`
as `thin_classes` so a document can be checked against them.

`other` scores 0.00, and that is not a bug: `other` means a person looked and
could not decide, so by construction it carries no learnable signal. The model
never predicts it, correctly.

### Model comparison

All three are reweighted toward the rare classes — `class_weight="balanced"` for
the two linear models, and a hand-computed inverse-frequency prior for naive
Bayes, which rejects the string `"balanced"` and only accepts an array. With 27
categories and `maps` at 3 examples that reweighting runs to a ratio of about
800:1, and naive Bayes shows what it does: 0.605 accuracy, 0.166 balanced. A
model that can only guess the dominant class, measured rather than inferred.

| Model | Accuracy | Balanced accuracy | Macro F1 | Weighted F1 |
| :--- | ---: | ---: | ---: | ---: |
| LinearSVC | 0.886 | 0.595 | 0.584 | 0.889 |
| LogisticRegression | 0.862 | 0.576 | 0.548 | 0.871 |
| MultinomialNB | 0.605 | 0.166 | 0.166 | 0.650 |

### Getting the last categories in

The nine that were missing were not missing because the catalog is small. It
was the fetcher: a host that returned nothing once was written to cache as an
empty file and never tried again. `--retry-empty` re-fetches those, trying
`www.` as well.

That recovered 310 hosts overall and moved the missing categories from
90/168 measurable to 157/168: `sports` 0 → 7, `crash` 2 → 11, `crypto` 2 → 8,
`maps` 1 → 3.

It cannot close the gap completely, and the residue is measured rather than
assumed. Of the hosts still without text, **54 of 65 answer no HTTP request at
all** — `akamai.net`, `akadns.net` and similar are edge CDNs whose apex does
not serve a page. Those need a different signal than page text, not a different
fetch.

### Per-class metrics

| Class | Precision | Recall | F1 | Support |
| :--- | ---: | ---: | ---: | ---: |
| finance | 0.96 | 0.95 | 0.96 | 2533 |
| government | 0.98 | 0.97 | 0.97 | 923 |
| software | 0.64 | 0.70 | 0.67 | 168 |
| gaming | 0.62 | 0.70 | 0.65 | 69 |
| health | 0.75 | 0.70 | 0.73 | 57 |
| shopping | 0.61 | 0.59 | 0.60 | 73 |
| news | 0.85 | 0.87 | 0.86 | 115 |
| travel | 0.52 | 0.37 | 0.43 | 38 |
| ads | 0.65 | 0.74 | 0.69 | 46 |
| education | 0.95 | 0.89 | 0.92 | 172 |
| other | 0.00 | 0.00 | 0.00 | 10 |
| analytics | 0.65 | 0.69 | 0.67 | 32 |
| cdn | 0.30 | 0.43 | 0.35 | 21 |
| ai | 0.75 | 0.66 | 0.70 | 50 |
| crash | 0.86 | 0.55 | 0.67 | 11 |
| transport | 0.58 | 0.42 | 0.48 | 36 |
| video | 0.37 | 0.46 | 0.41 | 46 |
| search | 0.63 | 0.48 | 0.55 | 25 |
| encyclopedia | 0.25 | 0.41 | 0.31 | 27 |
| sports | 0.67 | 0.57 | 0.62 | 7 |
| music | 0.43 | 0.38 | 0.40 | 8 |
| telecom | 0.38 | 0.55 | 0.44 | 11 |
| social | 0.48 | 0.35 | 0.41 | 34 |
| crypto | 0.11 | 0.50 | 0.19 | 8 |
| maps | 0.67 | 0.67 | 0.67 | 3 |
| messaging | 0.59 | 0.83 | 0.69 | 23 |
| email | 0.76 | 0.68 | 0.72 | 19 |
| **accuracy** | | | **0.89** | |
| **macro avg** | 0.59 | 0.60 | 0.58 | |
| **weighted avg** | 0.89 | 0.89 | 0.89 | |

### Correlated terms (chi-squared + model weight, top 5 per class)

| Class | Chi-squared top terms | Model weight top terms |
| Class | Chi-squared top terms | Model weight top terms |
| :--- | :--- | :--- |
| finance | ve, und, sie, für, belediye | bank, banking, financial, для, online |
| government | belediye, meclis, belediyesi, başkan, beledi | belediye, belediyesi, gov, başkan, duyurular |
| software | github, copilot, azure, enterprise, microsoft | github, azure, plex, soon, software |
| gaming | game, games, doom, elder scrolls, the elder | game, games, storefront, com why, of |
| health | doktor, tedavisi, cerrahi, cerrahisi, tıbbi | doktor, medical, org, klinik, health |
| shopping | giyim, elbise, aksesuar, ayakkabı, amazon | com tr, amazon, com why, shop, giyim |
| news | son dakika, dakika, yazarlar, abd, trump | hulu, 바로가기, yahoo, trump, haberleri |
| travel | uçak bileti, bileti, uçak, ucuz, otelleri | http www, flight, com why, homes, uçak bileti |
| ads | publishers, advertisers, advertiser, advertising, publisher | publishers, affiliate, marketing, advertising, brands |
| education | akademik, fakültesi, araştırma, koordinatörlüğü, öğrenci | üniversitesi, öğrenci, akademik, edu, study |
| other | names, nasil, domain, invalid, ensure that | por, exclusive, engine, bitte, nasil |
| analytics | journeys, retention, analytics, mixpanel, splunk | analytics, http www, your data, retention, journeys |
| cdn | cdn, bunny, 404, ddos, dns | cdn, 109, access denied, denied, that |
| ai | kimi, models, deepseek, inference, ai | ai, models, character, kimi, deepseek |
| crash | performance monitoring, crash, firebase, monitoring, sentry | fix, crash, monitoring, performance monitoring, errors |
| transport | gönderi, fiyat listesi, kargo, modelleri, maps | audi, maps, gönderi, kargo, fiyat listesi |
| video | yeni bölüm, sevdiğim sensin, sensin, diziler, bölüm fragmanı | http www, max, tv, watch, sports |
| search | gmail, gelişmiş, mleri, uygulamaları, oturum | engine, search, 2004, json, load |
| encyclopedia | kelime, words, philosophy, lists, ancient | org, kelime, türkçe, philosophy, words |
| sports | puan durumu, gol, bundesliga, galatasaray, ligi | gol, puan, puan durumu, galatasaray, barcelona |
| music | artists, cache, radio, apple music, music | cache, artists, music, fra, radio |
| telecom | tivibu, fiber, hbo max, turkcell, hbo | net, fiber, tivibu, numara, kanalları |
| social | tencent, vk, random, happening, to share | match, vk, tencent, linkedin, com why |
| crypto | eth, kraken, btc, crypto, staking | http www, www, com, eth, price |
| maps | uydu, tarifi, toplu taşıma, konumu, daha fazlasını | tarifi, maps, uydu, konumu, for enterprise |
| messaging | 새창열림, chats, messages, calls, meetings | 새창열림, ai, calls, talk, messages |
| email | proton, proton mail, emails, inbox, your email | email, gmail, mail, gb, inbox |

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

Five hosts where the model is confident (≥70%) but disagrees with the catalog
label:

| Host | Catalog label | Predicted | Confidence | Top 3 predictions |
| :--- | :--- | :--- | ---: | :--- |
| guven.com.tr | finance | health | 87% | health 87%, finance 4%, government 1% |
| display.ugc.bazaarvoice.com | software | finance | 82% | finance 82%, government 3%, software 2% |
| iqiyi.com | video | finance | 82% | finance 82%, government 3%, video 2% |
| ilbank.gov.tr | finance | government | 72% | government 72%, finance 12%, news 2% |
| paypalobjects.com | finance | music | 71% | music 71%, finance 17%, software 4% |

Four of the five are labelled `finance`, and the reason is the same in every
case: `finance` is over half the sample, so it is both the label the model
falls back on and the one it drifts away from.

- `guven.com.tr` — a Turkish insurer; "güven" is also the common word for
  *trust*, so the text reads as health. The label is defensible, the page is
  just not distinctive.
- `bazaarvoice.com` — UGC review infrastructure. `software` looks right; a
  customer-review platform reads as finance to a model.
- `iqiyi.com` — a Chinese video platform. The `video` label is clearly right
  and the model is wrong; the top-3 shows the finance prior overriding it.
- `ilbank.gov.tr` — a Turkish state bank. Read as government because the page
  is full of institutional language.
- `paypalobjects.com` — PayPal's static asset CDN, predicted `music`. The label
  is arguably wrong: this is infrastructure, not a finance service.

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
