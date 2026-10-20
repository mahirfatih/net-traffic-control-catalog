# Finance in the high-confidence errors

The model's 68 high-confidence errors are lopsided: **57 of the 68 predict
`finance`**, and only 11 predict anything else. The audit flagged the 57 as worth
a triage, on the theory that a confident disagreement is where a wrong label
hides. Read in full, it is the opposite — the 57 are the model's dominant-class
pull, not catalog mistakes — and that is what makes them worth writing down.

Regenerate the set against the current analysis:

```sh
python3 - <<'PY'
import json
d = json.load(open("docs/analysis/out/matrix-data.json"))
for e in sorted(d["high_confidence_errors"], key=lambda x: -x["confidence"]):
    if e["predicted"] == "finance":
        print(f"{e['host']:42} true={e['true']:13} conf={e['confidence']:.2f}")
PY
```

## Why the error points at the model, not the catalog

`finance` is 53% of the measured sample, so it is the label the model both falls
back on and over-applies. The 57 are hosts whose label is not in doubt at all:

| Host | Catalog label | Predicted |
| :--- | :--- | :--- |
| `mediamarkt.com` | shopping | finance 91% |
| `hotels.com` | travel | finance 83% |
| `linkedin.com` | social | finance 81% |
| `baidu.com` | search | finance 85% |
| `battle.net` | gaming | finance 84% |
| `mailbox.org` | email | finance 88% |
| `cambridge.org` | encyclopedia | finance 79% |

No one would relabel `linkedin.com` as `finance` to satisfy the model. A
classifier that calls a social network, a search engine and a games portal
`finance` is reporting its own prior, and the reading is exactly what the
**balanced accuracy of 61%** already says: accuracy 89% is mostly the dominant
class predicting itself and its neighbours.

## The other direction is where a mislabel could hide

Ask the question the audit meant — *which `finance` hosts does the model read as
something else?* — and the set is small and quiet:

- **1** at confidence ≥ 0.7 (`ilbank.gov.tr` → government), not 57.
- **52** in total, but most at 0.2–0.3, which is the model hedging over a thin or
  login-only page, not a claim.

So the `finance` label is not quietly wrong 57 times; the model is quietly
`finance` 57 times. The two are easy to confuse and worth naming apart.

## What to do

1. **Nothing, from the 57.** They are the balanced-accuracy story made concrete,
   not a relabel queue. If the number ever needs to drop, the lever is class
   balancing in the analysis, not the catalog.
2. **One visit:** `ilbank.gov.tr` (the one confident `finance` host read
   otherwise). It is a state bank and the label stands. `guven.com.tr` was the
   other and it was wrong — the page is *Güven Hastanesi* — so it is now labelled
   `health`, not `finance`.

This is a snapshot of the committed analysis; it is rebuilt per release (see
[`README.md`](README.md)). Nothing here is a catalog change on its own.
