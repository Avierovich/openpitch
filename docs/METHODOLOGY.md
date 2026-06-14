# Methodology

## Purpose

This page explains how OpenPitch turns public source material into confidence-scored startup intelligence. It is written for users, contributors, journalists, and skeptical readers.

OpenPitch is not a source of certainty. It is a public-source reconciliation system.

## 1. Core Objects

### Claim

A claim is one extracted assertion from one source.

Example:

```json
{
  "company_id": "acme",
  "metric": "arr",
  "value": 100000000,
  "unit": "USD",
  "raw_text": "we crossed $100M ARR",
  "source": {
    "type": "podcast",
    "name": "Example Podcast",
    "url": "https://example.com/episode",
    "locator": "00:34:12",
    "published_at": "2026-06-01"
  },
  "base_confidence": 0.6
}
```

### Resolved Value

A resolved value is OpenPitch's current best estimate for one company metric, computed from one or more claims.

It includes:

- value or range;
- confidence;
- estimate type;
- `as_of`;
- supporting claims;
- contradiction flag;
- history reference.

## 2. Source Types

| Source type | Typical role | Starting trust |
|---|---|---:|
| Filing | Official regulatory or legal source | Highest |
| News | Reported journalism or press | High |
| Podcast | Founder/operator interview | Medium |
| Web | Company site, careers, public pages | Medium-low |
| Social | Public posts or rumor-like material | Low |
| Derived | Computed from other claims | Propagated |

Starting trust is only a prior. It can change through source reliability over time.

## 3. Confidence Model

Claim confidence starts with:

```text
base_confidence =
  source_tier_prior
  * speaker_weight
  * qualifier_penalty
```

Then it decays with age:

```text
current_confidence = base_confidence * exp(-age_days / metric_tau)
```

Finally, agreeing independent claims compound through corroboration:

```text
resolved_confidence = 1 - product(1 - claim_confidence)
```

Confidence is capped below 1.0. OpenPitch never presents private-company estimates as certain.

## 4. Speaker Weights

| Speaker role | Weight |
|---|---:|
| Founder / CEO / exec | 1.0 |
| Investor | 0.8 |
| Journalist | 0.7 |
| Unknown | 0.5 |

A founder claim can be authoritative and biased at the same time. Confidence reflects authority, while corroboration and contradiction detection handle disagreement.

## 5. Qualifier Penalties

Soft language lowers confidence.

| Qualifier | Meaning |
|---|---|
| `run_rate` | Stated as run-rate rather than trailing actual |
| `rounded` | Rounded figure |
| `approximate` | "About", "around", "roughly" |
| `forward_looking` | Target or projection |
| `unconfirmed` | Not independently verified |

## 6. Reconciliation

For each company and metric:

1. Gather active numeric claims.
2. Compute current confidence for each claim.
3. Cluster claims that are close enough by metric tolerance.
4. Pick the cluster with the highest summed confidence.
5. Compute the value as a confidence-weighted average.
6. Compute range from credible claims.
7. Mark as consensus if multiple independent sources agree.
8. Mark contradiction if a rival cluster also has serious confidence.

The purpose is not to force agreement. The purpose is to make disagreement visible.

## 7. Estimate Types

| Type | Meaning |
|---|---|
| `reported` | One source directly stated the value |
| `consensus` | Multiple independent sources agree within tolerance |
| `implied` | Derived from other signals or history |

v0.1 should be conservative with implied values. Qualitative growth direction is safer than fabricated dollar estimates.

## 8. Contradictions

A contradiction is a high-confidence disagreement between public sources.

OpenPitch uses neutral framing:

- "public-source discrepancy";
- "claim conflict";
- "filing and public statement differ."

OpenPitch does not infer deception, intent, or wrongdoing.

## 9. Derived Claims

Hard identities can create derived claims:

- ARR = MRR x 12
- revenue multiple = valuation / ARR
- ARR = subscribers x ACV
- post-money valuation = round amount / equity sold percentage

Derived claims carry derivation metadata and propagated confidence.

Soft benchmark estimates, such as headcount x revenue-per-employee, are not appropriate as headline v0.1 values unless clearly labeled, wide-ranged, and low-confidence.

## 10. Corrections

Users can challenge metrics by opening a correction issue with public evidence. Accepted corrections are committed publicly and preserved in history.

Corrections may:

- update a value;
- lower or raise confidence;
- add a contradiction;
- mark a source as stale;
- change source reliability.

## 11. Limitations

- Private-company data is incomplete.
- Public statements can be stale, promotional, or ambiguous.
- Filings may imply funding data but not operating metrics.
- Podcasts and articles should not be treated as audited financial statements.
- OpenPitch is not investment advice.
