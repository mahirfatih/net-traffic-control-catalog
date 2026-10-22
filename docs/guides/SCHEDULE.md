# Schedule — when each sweep runs

The three sweeps in [`PIPELINE.md`](PIPELINE.md) are independent, and they decay
at different rates. A domain that stops resolving is worth catching in days; a
name that quietly changes owner matters in months. Running all three on every
commit would be slow and mostly wasted; running none is how a catalog rots. This
page sets a cadence, so "when do we re-check?" has an answer that is not "when
someone remembers".

None of this blocks a pull request. The sweeps need the network and a browser,
and `test/test.sh` deliberately never calls them — see [`SOURCES.md`](../reference/SOURCES.md).

| Sweep | Cadence | Round gap | What it catches | Cost of being late |
| :--- | :--- | :--- | :--- | :--- |
| **1 · DNS** (`probe-dead.py`) | **weekly** | ≥ 10 min, two rounds | a domain that no longer resolves | a dead row ships for up to a week |
| **2 · Live** (`sweep-live.py`) | **monthly** | ≥ 10 min, two rounds | a name that resolves but serves nothing (parked, lapsed) | a recycled name keeps an old label for a month |
| **3 · Registration** (`verify-registrations.py`) | **quarterly** | ≥ 10 min, two rounds | a name that changed hands | a lapsed name inherits the previous owner's category |

The order reflects how fast the underlying fact can change. DNS is the cheapest
and the most volatile, so it runs most often; registration changes are slow and
the sweep is the most expensive, so it runs least. Live sits between them because
a parked page is a person's decision that can happen any day.

## Why these periods

- **Weekly DNS.** A dead host is a wrong answer the app gives every day until it
  is removed. Weekly bounds that at seven days without a daily network dependency.
- **Monthly live.** A parked page is rarer than a dead domain and the sweep costs
  a real browser per host, so a month is the balance between freshness and load.
- **Quarterly registration.** Registrations lapse on a yearly clock; a quarter is
  frequent enough to catch a lapse before the name is re-registered and reused.

These are starting points, not law. If the app starts shipping more often, tighten
the DNS sweep; if a recycled name ever reaches a device, the gap was too long and
that is the signal to shorten it.

## How to run a cycle

Every sweep has the same shape — two rounds that must agree, a summary that
proposes and changes nothing, and an `--apply` that is a separate, deliberate
step. The commands are in [`SOURCES.md`](../reference/SOURCES.md), and the policy that makes a
proposal safe is in [`PIPELINE.md`](PIPELINE.md).

```sh
python3 scripts/catalog/probe-dead.py --round 1
python3 scripts/catalog/probe-dead.py --round 2
python3 scripts/catalog/probe-dead.py --summary      # proposal only
python3 scripts/catalog/probe-dead.py --apply        # only after you read it
```

## Automating it

The DNS sweep can be automated with a GitHub Actions workflow — create
`.github/workflows/sweep.yml` from the template in `scripts/catalog/README.md`
to run weekly on Monday with a manual dispatch option. It probes two rounds ten
minutes apart and files or updates one tracking issue with the proposal. It is
**non-blocking** — never a required check — and it cannot touch catalog data: the
result of a sweep is a human decision (the four rules in `PIPELINE.md`), and a
job that could auto-delete a live host because a resolver hiccuped is the failure
this page is arranged to avoid. The live and registration sweeps stay a manual
checklist too: they need a real browser, so they run from [`SOURCES.md`](../reference/SOURCES.md)
on the cadence above.
