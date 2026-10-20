# Analysis: catalog consistency

This directory holds the results and methodology of an audit that fetches
homepage text for the hosts in `catalog.json`, compares nine text classifiers
(eight on TF-IDF features, one on multilingual sentence embeddings), keeps
TF-IDF + LinearSVC as the witness, and produces a confusion matrix showing how
consistently our labels agree with what a text model can recover.

**Provenance.** The committed `out/` was produced by `scripts/analysis/build-matrix.py`
at commit `84f549d` (2026-10-18) on 4,563 of the 6,731 catalog hosts. Re-run it
against each catalog release so the figures describe the current data rather than a
snapshot — the analysis is the catalog's only quantitative quality signal.

**The tool lives in [`scripts/analysis/`](../../scripts/analysis/); its output
lands here.** It is not part of the shipped catalog pipeline — the rest of
`scripts/` is standard-library-only, while the audit needs `scikit-learn`,
`matplotlib`, `torch` and `sentence-transformers`, and `test/test.sh` does not
run it.

## Usage

```bash
cd scripts/analysis
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python fetch-pages.py     # cache each host's homepage (~16 min warm, ~25 min from cold)
.venv/bin/python build-matrix.py    # ← writes docs/analysis/out/ (first run downloads the ~1 GB model)
python3 precision-sample.py --emit  # draw the hand-read precision sample (stdlib; reads .pages/)
python3 precision-sample.py --score # precision + Wilson interval, from the filled verdicts
```

Outputs land in `out/`:

- `confusion-matrix.png` — the matrix (counts + row-normalized side by side)
- `correlated-terms.md` — chi-squared **and** LinearSVC model-weight terms per category
- `high-confidence-errors.md` — hosts where the model is confident but disagrees
- `matrix-data.json` — raw numbers including model comparison and per-host top-3 predictions

The triage of those errors — why 57 of the 68 predict `finance`, and why that is
the model's prior rather than a relabel queue — is in
[`finance-triage.md`](finance-triage.md).

## Result

**Accuracy: 89%** (4,054/4,563, 27 classes, 3-fold CV) — **balanced accuracy
61%**. Both numbers are correct and the gap between them is the whole story.

The audit measures **every category in the catalog**. It covers the 4,563 hosts
whose homepage yields usable text, and keeps all 27 — including `maps`, which has
3 examples.

### The 28-point gap

`finance` is 53.1% of the catalog. Accuracy asks "how often is the model right",
and the model is right about `finance` almost always. Balanced accuracy asks
"how often is it right *per category*", weighting all 27 equally. LinearSVC
scores 0.888 and 0.605.

Read the first number alone and the catalog looks nearly perfect. Read the second
and the real picture is that two of every five labels cannot be recovered from
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

Nine models, two representations. Eight heads run on the same TF-IDF (1–2 grams,
20k features); the ninth runs on multilingual sentence embeddings. All are
reweighted toward the rare classes where the classifier supports it —
`class_weight="balanced"` for the linear, tree and forest heads, and a
hand-computed inverse-frequency prior for naive Bayes, which rejects the string
`"balanced"` and only accepts an array. With 27 categories and `maps` at 3
examples that reweighting runs to a ratio of about 800:1, and naive Bayes shows
what it does: 0.603 accuracy, 0.164 balanced — a model that can only guess the
dominant class, measured rather than inferred. `KNeighborsClassifier` is the one
head with no `class_weight`, so it starts at a structural disadvantage on
balanced accuracy.

| Model | Accuracy | Balanced accuracy | Macro F1 | Weighted F1 |
| :--- | ---: | ---: | ---: | ---: |
| MultilingualEmbeddingLogReg | 0.852 | 0.666 | 0.585 | 0.866 |
| RidgeClassifier | 0.864 | 0.637 | 0.566 | 0.876 |
| LinearSVC | 0.888 | 0.605 | 0.592 | 0.890 |
| SGDClassifier | 0.889 | 0.584 | 0.589 | 0.889 |
| LogisticRegression | 0.865 | 0.580 | 0.557 | 0.874 |
| RandomForestClassifier | 0.821 | 0.523 | 0.506 | 0.840 |
| KNeighborsClassifier | 0.856 | 0.444 | 0.513 | 0.839 |
| DecisionTreeClassifier | 0.797 | 0.395 | 0.391 | 0.800 |
| MultinomialNB | 0.603 | 0.164 | 0.165 | 0.649 |

The table is sorted by balanced accuracy and is descriptive, not a leaderboard.
**LinearSVC stays the witness**: it has the highest macro-F1 of the nine, and its
coefficients are what the correlated-terms report reads. Two models beat it on
balanced accuracy — `MultilingualEmbeddingLogReg` (0.666) and
`RidgeClassifier` (0.637) — both at a cost in macro-F1. The embedding result is
the interesting one: the corpus is not English-only (Turkish, German, Korean,
Russian, Chinese), and a bag-of-words model keeps those languages apart while a
sentence encoder maps them into one space, so it recovers the small, non-English
categories that TF-IDF cannot. The non-linear heads trail on the sparse lexical
features — the expected result, and part of why the witness is linear.

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

### What each score actually covers

The matrix measures 4,563 of 6,731 catalog hosts — 68%. The other 2,168 return
no usable page text: 1,709 answer nothing at all, and 459 return under 100
characters, which is the floor `build-matrix.py` needs.

So 5,022 hosts — 6,731 − 1,709 — answer *something*, and the classifier measures
4,563 of them. The difference between those two numbers is the stub pages: a few
dozen characters of navigation, a redirect notice or a cookie wall carries no
label signal. The floor counts **characters, not byte size**, which matters for
non-Latin pages — a Turkish or Chinese stub crosses 100 bytes with under 100
characters, and measuring the file size would file those hosts under the wrong
reason and leave the arithmetic short by exactly that many.

Those failures are **not evenly spread**, and that is the part that matters. A
per-class F1 describes the hosts that produced text, not the category. `gaming`
scores 0.67, and it was computed on 69 hosts out of 358:

| Category | In catalog | Measured | Coverage |
| :--- | ---: | ---: | ---: |
| gaming | 358 | 69 | 19% |
| cdn | 67 | 21 | 31% |
| software | 476 | 168 | 35% |
| search | 57 | 25 | 44% |
| travel | 80 | 38 | 48% |
| social | 65 | 34 | 52% |
| video | 87 | 46 | 53% |
| ads | 74 | 46 | 62% |
| email | 28 | 19 | 68% |
| encyclopedia | 40 | 27 | 68% |
| telecom | 16 | 11 | 69% |
| messaging | 33 | 23 | 70% |
| finance | 3571 | 2532 | 71% |
| other | 14 | 10 | 71% |
| shopping | 101 | 73 | 72% |
| ai | 68 | 50 | 74% |
| crypto | 10 | 8 | 80% |
| music | 10 | 8 | 80% |
| education | 212 | 172 | 81% |
| analytics | 39 | 32 | 82% |
| crash | 13 | 11 | 85% |
| health | 67 | 57 | 85% |
| transport | 42 | 36 | 86% |
| government | 1064 | 922 | 87% |
| news | 129 | 115 | 89% |
| maps | 3 | 3 | 100% |
| sports | 7 | 7 | 100% |
| **all** | **6731** | **4563** | **68%** |

The pattern is not random. Canvas/JS-heavy categories yield almost no text —
`gaming` at 19% is a pile of game clients whose homepage is script — while
static, server-rendered ones do well (`government` 87%, `news` 89%). So the
sample skews toward whatever renders as HTML, and every average in this document
inherits that skew.

Read a per-class number with its coverage row next to it. `maps` and `sports` at
100% are complete but tiny; `gaming` at 19% is a confident-looking score for a
fifth of the category.

### Per-class metrics

| Class | Precision | Recall | F1 | Support |
| :--- | ---: | ---: | ---: | ---: |
| finance | 0.96 | 0.95 | 0.96 | 2532 |
| government | 0.98 | 0.96 | 0.97 | 922 |
| software | 0.65 | 0.71 | 0.68 | 168 |
| gaming | 0.65 | 0.70 | 0.67 | 69 |
| health | 0.74 | 0.70 | 0.72 | 57 |
| shopping | 0.61 | 0.59 | 0.60 | 73 |
| news | 0.84 | 0.87 | 0.85 | 115 |
| travel | 0.56 | 0.37 | 0.44 | 38 |
| ads | 0.67 | 0.74 | 0.70 | 46 |
| education | 0.94 | 0.89 | 0.91 | 172 |
| other | 0.00 | 0.00 | 0.00 | 10 |
| analytics | 0.67 | 0.69 | 0.68 | 32 |
| cdn | 0.30 | 0.43 | 0.35 | 21 |
| ai | 0.76 | 0.70 | 0.73 | 50 |
| crash | 0.86 | 0.55 | 0.67 | 11 |
| transport | 0.65 | 0.42 | 0.51 | 36 |
| video | 0.35 | 0.50 | 0.41 | 46 |
| search | 0.63 | 0.48 | 0.55 | 25 |
| encyclopedia | 0.26 | 0.41 | 0.31 | 27 |
| sports | 0.60 | 0.43 | 0.50 | 7 |
| music | 0.43 | 0.38 | 0.40 | 8 |
| telecom | 0.41 | 0.64 | 0.50 | 11 |
| social | 0.46 | 0.35 | 0.40 | 34 |
| crypto | 0.19 | 0.63 | 0.29 | 8 |
| maps | 0.67 | 0.67 | 0.67 | 3 |
| messaging | 0.66 | 0.83 | 0.73 | 23 |
| email | 0.79 | 0.79 | 0.79 | 19 |
| **accuracy** | | | **0.89** | |
| **macro avg** | 0.60 | 0.61 | 0.59 | |
| **weighted avg** | 0.89 | 0.89 | 0.89 | |

### Correlated terms (chi-squared + model weight, top 5 per class)

| Class | Chi-squared top terms | Model weight top terms |
| :--- | :--- | :--- |
| finance | ve, und, sie, für, belediye | bank, banking, financial, для, online |
| government | belediye, meclis, belediyesi, başkan, beledi | belediye, belediyesi, gov, başkan, duyurular |
| software | github, copilot, azure, enterprise, microsoft | github, azure, plex, soon, software |
| gaming | game, games, doom, elder scrolls, the elder | game, games, storefront, com why, of |
| health | doktor, tedavisi, cerrahi, cerrahisi, tıbbi | doktor, medical, org, klinik, sağlık |
| shopping | giyim, elbise, aksesuar, ayakkabı, amazon | com tr, amazon, com why, shop, giyim |
| news | son dakika, dakika, yazarlar, abd, trump | hulu, 바로가기, yahoo, trump, haberleri |
| travel | uçak bileti, bileti, uçak, ucuz, otelleri | http www, flight, com why, homes, uçak bileti |
| ads | publishers, advertisers, advertiser, advertising, publisher | publishers, affiliate, marketing, advertising, brands |
| education | akademik, fakültesi, araştırma, koordinatörlüğü, öğrenci | üniversitesi, öğrenci, akademik, edu, study |
| other | domain, names, nasil, invalid, ensure that | por, exclusive, engine, domain, bitte |
| analytics | journeys, retention, analytics, mixpanel, splunk | analytics, http www, your data, retention, journeys |
| cdn | cdn, bunny, 404, ddos, dns | cdn, 109, access denied, denied, that |
| ai | kimi, models, deepseek, inference, ai | ai, models, character, kimi, deepseek |
| crash | performance monitoring, crash, firebase, monitoring, sentry | fix, crash, monitoring, performance monitoring, errors |
| transport | gönderi, modeller, fiyat listesi, kargo, maps | audi, maps, gönderi, kargo, reaching |
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
why.** `finance` used to be 68 examples with discriminative terms; at 2,532 it
is 55% of the sample, and chi-squared ranks by raw frequency association, so the
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

68 hosts where the model is confident (≥70%) but disagrees with the catalog
label. The list is out of fold, like the matrix, so these are the model's real
mistakes rather than the hosts it memorised — the previous in-sample list found
five, and it had also "recovered" all ten `other` hosts, which the matrix never
predicts. The five below are the shape of it, not the whole:

| Host | Catalog label | Predicted | Confidence | Top 3 predictions |
| :--- | :--- | :--- | ---: | :--- |
| display.ugc.bazaarvoice.com | software | finance | 82% | finance 82%, government 3%, software 2% |
| iqiyi.com | video | finance | 82% | finance 82%, government 3%, software 2% |
| googlesyndication.com | ads | search | 83% | search 83%, finance 5%, software 1% |
| ilbank.gov.tr | finance | government | 87% | government 87%, news 3%, finance 2% |

57 of the 68 predict `finance`, and the reason is the same in every case:
`finance` is over half the sample, so it is both the label the model falls back
on and the one it drifts away from. The five above are the readable ones; the
rest are mostly infrastructure hosts with thin pages and a dominant-class pull.
The full list is in `out/high-confidence-errors.md`.

- `bazaarvoice.com` — UGC review infrastructure. `software` looks right; a
  customer-review platform reads as finance to a model.
- `iqiyi.com` — a Chinese video platform. The `video` label is clearly right
  and the model is wrong; the top-3 shows the finance prior overriding it.
- `googlesyndication.com` — Google's ad-serving host; the page is thin and
  search-flavoured, so `ads` is predicted as `search`. Infrastructure again,
  with no `ads` vocabulary of its own.
- `ilbank.gov.tr` — a Turkish state bank. Read as government because the page
  is full of institutional language.

## What the matrix does and does not measure

It does **not** measure whether our labels are *correct* — there is no
independent ground truth. It measures **self-consistency**: given the page
text, can a model recover our label? High diagonal = our labels are
predictable from page content. Off-diagonal = our label disagrees with what
the text suggests (either the label is wrong, or the page is not
representative of the category).

Infrastructure hosts (CDNs, analytics, ads) have no meaningful page text,
so they are naturally filtered out by `--min-text`.

### The thinnest categories

Coverage is not uniform, and the gaps are not random — they follow the shape of
the page. A category whose hosts are apps or endpoints loses them to the text
floor:

- **`gaming` — 19% measured.** Game portals are canvas apps; the homepage has
  almost no prose.
- **`cdn` — 31%.** A delivery host answers with bytes, not words.
- **`software` — 35%.** Developer pages are code samples and app shells.

A category measured on a fifth of its rows is scored on a fifth of its rows, so
its recall and F1 describe the readable fifth, not the category. Part of the fix
is already in the repo: `fetch-pages.py --render-thin N` re-fetches a host whose
plain-HTML text is under `N` characters through the **same browser harness the
live sweep uses** — [`agent-browser`](https://github.com/vercel-labs/agent-browser)
with [Lightpanda](https://lightpanda.io) (`--engine lightpanda`) — so a JS shell
that `curl` sees as empty becomes a page with a title and prose. What that still
cannot fix is a host that never returns a document at all; those need a
different signal, not a different renderer. Read a thin category's score next to
its coverage, which [`../COVERAGE.md`](../COVERAGE.md) reports as its own column.

## Methodology

1. **Text extraction** (`fetch-pages.py`): Fetches each host's homepage and
   extracts `<title>`, meta description, meta keywords, headings (h1–h6),
   and body text. Title/meta/headings are placed first because they carry
   the strongest category signal. `--render-thin N` re-fetches a page whose
   plain-HTML text is under `N` characters through the **same browser harness
   the live sweep uses** (`agent-browser` + Lightpanda), which turns a JS shell
   into readable text; the longer of the two is kept.

2. **Model comparison** (`build-matrix.py`): nine models are evaluated with
   stratified cross-validation, at as many folds as the smallest category
   allows (3 today, because `maps` has 3 examples): eight heads on TF-IDF
   (1–2 grams, 20k features) — LinearSVC, logistic regression, ridge, SGD,
   multinomial naive Bayes, decision tree, random forest and k-nearest
   neighbours — and one on multilingual sentence embeddings
   (`paraphrase-multilingual-mpnet-base-v2`) with a logistic-regression head.

3. **Classification**: LinearSVC is kept for the confusion matrix, term weights
   and calibrated error review. Every host receives an out-of-fold prediction.

4. **Calibration**: `CalibratedClassifierCV` (sigmoid) provides probability
   estimates, and it is fitted **inside** the same cross-validation as the
   matrix, so a host's confidence comes from a model that never saw it. The
   earlier version read probabilities off a model fitted on all of `X`, which
   turned "confidence" into recall: it could name a host a high-confidence error
   while the per-host table predicted that same host correctly.

5. **Chi-squared test**: For each category, the 10 terms most strongly
   associated with that category are identified, revealing what drives
   each class and flagging potential miscategorizations.

6. **Model weight terms**: The fitted LinearSVC coefficients show which
   terms the model itself weighs most positively for each class — a
   complementary signal to chi-squared.

7. **Per-host predictions**: Each host's top-3 predicted categories with
   out-of-fold calibrated probabilities are recorded in `matrix-data.json` and
   shown in the high-confidence errors table.

8. **Owner-leakage check**: StratifiedKFold can scatter two hosts of the same
   owner across folds, letting the model memorise one to score the other. The
   same pipeline is re-run under `GroupKFold` with every host grouped by its
   registrable domain (eTLD+1), and both numbers land in `matrix-data.json` →
   `leakage`. The gap is small but real — balanced accuracy drops from 61% to
   55% once an owner is held out, while raw accuracy barely moves (89% → 88%),
   which is the majority class absorbing the difference. Read the balanced
   number as the one that includes a little owner signal.
 9. **Hand-read label precision** (`precision-sample.py`): a model's score is not
    evidence that a *label* is right — finance is half the catalog and its labels
    partly come from a bank list, so a model fitted on them is graded on the very
    signal that made them. A fixed, seeded sample of 300 hosts (200 finance, 100
    government) is read against its cached homepage text and judged independently
    of the classifier. Result in [`precision.md`](precision.md): finance
    **98.5%** (95.7–99.5%), government **100%** (96.3–100%); the three finance
    misses are a telecom validation page, a betting-spam page and a casino.
