# Label precision — a hand-read sample

Independent of the classifier: each host's homepage text was read and its
label judged right or wrong. The gap to a model's score is the point.

| Category | Reviewed | Correct | Precision | 95% CI |
| :--- | ---: | ---: | ---: | :--- |
| finance | 200 | 197 | 98.5% | 95.7%–99.5% |
| government | 100 | 100 | 100.0% | 96.3%–100.0% |

Labels judged wrong, and why:

- `card-transfer.tele2.ru` — Tele2 (telecom) number-validation page, not a financial institution
- `ibk.ofkbank.ru` — a betting-bonus / micro-loan spam page, not the bank it is named after
- `xn--80aae3af7av6a7a.xn--p1ai` — JetTon casino — gambling, not finance

Seed 20261018, sample of 300 hosts with ≥100 characters of homepage text.
