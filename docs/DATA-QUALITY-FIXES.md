# Data quality fixes and improvements

This is a standalone work list for OpenPitch. It assumes no prior conversation.

OpenPitch publishes valuations, revenue and funding for private AI companies. Every
figure is meant to carry its source, its date and a confidence score. A user installed
it on 18 November 2026 and reported obviously wrong numbers. I investigated and
confirmed the report with a direct scan of the published data.

Do not use `openpitch quality-report` to measure these errors. Its critical count (125 on
18 November) is almost entirely `funded_no_valuation`, which is a coverage gap: a company
with funding found but no valuation. It contains no check for implausible values, so a
wrong number passes it silently. Fix 10 below adds that missing check.

The sources are mostly fine. Almost every defect below happens after ingest, in
normalization and merging, which means the fixes are concentrated in a few places and
each one corrects many records at once.

Work through the fixes in the order given. Each one lists how to reproduce it.

## Fixes

### 1. The same company appears twice, both live

`deepseek` and `deepseek-ai` are the same company. Both are published, both sit in the
top ten, and their valuations disagree by a factor of eight.

| id | name | valuation | rank | in universe |
|---|---|---|---|---|
| `deepseek` | DeepSeek | 496,548,752,776 | 3 | yes |
| `deepseek-ai` | Deepseek AI | 61,572,032,292 | 7 | yes |

This is not isolated. `deepeval` and `deepeval-by-confident-ai` are also the same
product, both pointing at `confident-ai.com`.

The cause is that company identity is a slug derived from whatever name a source used,
so "DeepSeek" and "Deepseek AI" become separate records. Deduplication currently
compares ids, which cannot catch this.

Use the canonical domain as the identity key, falling back to a normalized name only
when no domain exists. Then backfill: find existing collisions, merge their claims, and
keep the record with the better corroborated figures.

Reproduce with `ls data/companies/ | grep -i deep` and compare the two JSON files.

### 2. Magnitude words in units are discarded

A stored claim for Yellow.ai reads `value: 500.0` with `unit: "million USD"`. The
reconciler kept the 500 and rewrote the unit to plain USD, so a 500 million dollar
valuation became 500 dollars. The same happened to that company's revenue and total
funding.

Parse the magnitude out of the unit string and multiply the value before storing, then
normalize the unit to a bare currency code.

Reproduce by reading `data/claims/yellow-ai.json` and comparing it against
`data/companies/yellow-ai.json`.

### 3. Foreign currencies are stored at face value and shown as dollars

There is no currency conversion anywhere in the pipeline. The claim corpus holds 37 EUR
claims, 13 CNY, plus HKD and KRW. Two examples:

| company | metric | stored value | currency | approximate USD |
|---|---|---|---|---|
| `biren-technology` | round_amount | 7,020,744,194 | HKD | about 900 million |
| `furiosaai` | valuation | 755,588,000 | KRW | about 550 thousand |

This is the most damaging defect in the list because it is silent. The number looks
plausible and is simply wrong, sometimes by three orders of magnitude.

Convert to USD at ingest using a rate for the claim's `as_of` date, and keep the
original value and currency alongside so the provenance stays honest. If a free rate
source is unavailable, the alternative is to store the currency explicitly and refuse
to render a non USD figure as a dollar amount.

### 4. Unit type is never checked against the metric

Cyera's revenue is recorded as `80.0` with `unit: "x"`. That is a revenue multiple
written into a dollar field. The same claim also populates Cyera's `revenue_multiple`,
which is where it belongs.

Add a type check at ingest. A money metric accepts only currency units. A ratio metric
accepts only `x`. A count metric accepts only `count`. Reject anything else into a
quarantine file rather than publishing it.

### 5. Non domain text is written into the website field

Field mapping is leaking. Three examples from the current data:

| company | stored website value |
|---|---|
| `deepseek-ai` | `AI research/development` |
| `deep-genomics` | `biotech` |
| `deepinfra` | the entire record as one string, beginning `deepinfra.com status private category ai-infra subcategory inference specialty ...` |

The `deepinfra` case shows a whole structured record being concatenated into a single
field, so this is a parsing failure rather than a bad source. Validate that `website`
looks like a hostname before writing it, and investigate how the concatenation happens.

This matters more than it looks, because fix 1 wants to use the domain as the identity
key, and that only works if the field is clean.

### 6. The latest_round metric is structurally broken

`latest_round` mixes three incompatible things: round names, counts and dollar amounts.
Cyera stores `7.0` with `unit: "object"`. Deepchecks stores `0.0`. Comp AI stores
`34,000,000`. Across the corpus there are 112 claims with unit `round`, 82 with
`series`, 50 with `series a`, and smaller counts for the later letters.

Split this into two fields. One holds the round name as a string, such as Series B. The
other holds the amount, which `round_amount` already covers. Then remove `latest_round`
from anything user facing until it means one thing.

### 7. Forty percent of claims carry no unit

Of roughly 9,300 claims, 3,716 have an empty unit. Any of those feeding a money metric
is an unchecked assumption that the figure is already in dollars.

Count how many empty unit claims actually reach a published metric, then decide whether
to infer the unit from the metric type or quarantine them. Do this after fixes 2, 3 and
4, because those will change the count.

### 8. Impossible figures reach publication

A scan for internally contradictory records found these. They are symptoms of the
fixes above rather than separate bugs, so use them to verify the fixes worked.

| company | problem |
|---|---|
| `nscale` | revenue of 103 billion against a valuation of 14.6 billion |
| `1x-technologies` | valuation of 667.5 million below total raised of 1 billion |
| `prometheus` | valuation of 4 billion below total raised of 12 billion |
| `yellow-ai` | revenue 79.5, valuation 500, total funding 100 |
| `cyera` | revenue 80 |
| `comp-ai` | revenue 15 |
| `foodics` | revenue 20.8 |
| `hugging-face` | round amount 399 |
| `aiva` | revenue 2,400 |

### 9. Derived metrics inherit bad inputs without flagging

`revenue_multiple` for DeepSeek is 742.86, computed from the wrong valuation in fix 1.
Cyera's is 80, computed from the mis typed revenue in fix 4. A derived figure currently
looks as trustworthy as a sourced one.

Cap a derived metric's confidence at the lowest confidence among its inputs, and
suppress it entirely when any input is quarantined.

### 10. The quality report has no plausibility check

Done on 18 November 2026. The report now lists every figure the serving gate withholds as
implausible, and counts the malformed values per metric. On that date it listed 53
implausible figures, and the critical count rose from 125 to 178 as a result.

### 11. Universe ranking still uses withheld figures

`src/openpitch/pipeline/score.py` ranks the universe from raw valuations, upstream of the
serving gate. The MCP `list_companies` default sort is `universe_rank`, so a company whose
valuation is withheld can still sit high in the list. The `deepseek` record ranked 3rd on
its unconverted CNY figure. The dashboard is not affected, because it sorts by gated
values.

Make `_signal` in `score.py` skip a valuation that `serving_gate.assess` withholds. This
changes stored data (`data/universe.json` and each company's rank), so it belongs with
the backfill rather than at serving time.

## Improvements

These are not defects. They are the changes that buy the most credibility for the least
work, in the order I would do them.

### Gate implausible figures at serving time

Done on 18 November 2026, in `src/openpitch/serving_gate.py` with thresholds in
`config/serving_gate.yaml`. It withholds 435 of 1,925 published figures (53 implausible,
382 malformed), catches 14 of the 17 known bad figures, and hides none of the known good
ones. The 3 it misses are Cyera's reported 80x multiple (genuinely sourced), 1X's valuation
(fix 1, an identity problem) and FuriosaAI's valuation (correctly converted with a stale
label, so it is cautioned rather than withheld). The contract is in `docs/MCP-SPEC.md`
under Withheld figures. It is a mitigation: every fix above is still needed, and the
gate's withhold list in the quality report is the measure of how much is left.

A plain confidence floor does not work, and an earlier version of this document
recommended one, so the reasoning is worth keeping.

Confidence measures how reliable and corroborated the sources are. It does not measure
whether a number is plausible, so a unit error reported by one reputable outlet still
scores in the middle. Of 17 known bad figures, only 4 sit below 0.2. Yellow.ai's 500
dollar valuation scores 0.51 and Cyera's `latest_round` of 7 scores 0.83. A 0.2 floor
would also hide 42 percent of all published metrics.

The gate therefore needs plausibility rules alongside any floor: evidence of a unit
problem in the supporting claims, money figures too small to be real, and figures that
contradict each other within one company. It runs where data is served (the MCP tools
and the dashboard) and touches no extraction code.

### Add the invariants to CI as a gate

Once the fixes land, encode them as assertions that run in the daily job: no money
metric with a non currency unit, no valuation below total funding, no money value under
100,000 dollars, no two published companies sharing a domain. Quarantine the offending
record rather than failing the build, so a bad source never blocks a refresh.

This is what stops wrong numbers reaching publication again once the fixes have cleared
the current ones.

### Backfill the existing data

Every fix above changes only new ingests. The wrong values are already committed and
served. Plan a one off recompute from the stored claims after the normalization changes,
and expect the universe ranking to move, since the DeepSeek duplicate and the inflated
valuations currently distort it.

### Use the adoption data that started collecting today

`data/traffic/github.jsonl` began accumulating on 18 November 2026 from the daily job.
It records views, clones, referrers, stars and PyPI installs once a day. GitHub keeps
traffic for only 14 days and offers no export, which is why it is being snapshotted.

Two cautions when reading it. Clone counts are dominated by the project's own CI and by
directory scrapers, so they are not an adoption signal. PyPI installs are the real one,
currently around 125 a month.

One open question worth ten minutes: `aocr.org` is the largest single referrer to the
repository, ahead of Google. Nobody has established what that site is.

## Glossary

Terms in the order they appear.

Claim: one extracted statement about a company from a single source, stored under
`data/claims/`, before any merging.

Reconciler: the stage that merges multiple claims about the same metric into one
published figure with a confidence score.

Normalization: converting a raw extracted value into a comparable stored form, covering
units, currencies and magnitudes.

Confidence: a score from 0 to 1 combining source reliability, corroboration and
freshness. Decays as a figure ages.

Quarantine: holding a suspect claim out of publication while keeping it on disk for
inspection, rather than discarding it.

Derived metric: a figure computed from other metrics rather than taken from a source,
such as `revenue_multiple`.

Universe: the ranked subset of companies published at any one time, selected by an
attention score.

Backfill: recomputing already published records after a pipeline change, so old data
gets the benefit of the fix.

Invariant: a rule the data must always satisfy, checked automatically.
