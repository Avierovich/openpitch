# Corrections

## Purpose

OpenPitch is public-source, probabilistic intelligence. Corrections are expected and welcome. The goal is not to pretend the data is perfect; the goal is to improve it in public with an audit trail.

## What Can Be Corrected

You can request a correction for:

- wrong value;
- stale value;
- missing source;
- broken source link;
- incorrect source date;
- incorrect company identity or alias;
- overconfident estimate;
- missing contradiction;
- contradiction that is weak or misleading;
- source that should be excluded under [DATA-POLICY](DATA-POLICY.md).

## Evidence Standard

Correction requests must cite public evidence.

Accepted evidence:

- regulatory filings;
- official company or investor announcements;
- reputable news articles;
- public podcast episodes with timestamp;
- public company web pages;
- public reports or presentations.

Usually not enough by itself:

- anonymous social posts;
- private screenshots;
- unsourced claims;
- "I heard from someone";
- non-public documents.

## How To File A Correction

Open a GitHub issue with:

```text
Company:
Metric:
Current OpenPitch value:
Problem:
Proposed correction:
Public evidence URL:
Source date:
Notes:
```

If the issue concerns a public-source discrepancy, explain which sources conflict and why the current interpretation is wrong or incomplete.

## Review Process

1. Maintainer checks source availability and date.
2. Maintainer checks whether the correction changes value, confidence, contradiction state, or source reliability.
3. Accepted corrections are committed to data/history files.
4. Rejected corrections are closed with a reason.
5. Ambiguous corrections may remain open and lower confidence rather than changing the value.

## Correction Outcomes

A correction may:

- update a resolved value;
- add a new claim;
- mark a value as stale;
- lower confidence;
- raise confidence;
- add or remove a contradiction flag;
- update source reliability;
- fix a source link or locator.

## Public Changelog Format

Accepted corrections should be recorded in history and optionally summarized:

```text
2026-06-13 - anthropic / arr
Changed: confidence 0.62 -> 0.54
Reason: newer public source conflicts with previous claim
Evidence: https://example.com/source
```

## Language Policy

Use neutral language:

- "public-source discrepancy";
- "claim conflict";
- "source disagreement";
- "filing and public statement differ."

Avoid:

- "lying";
- "fraud";
- "misrepresentation";
- claims about intent.

OpenPitch describes source conflicts. It does not infer motive.

## Disclaimer

OpenPitch is not investment advice and does not provide audited financial data. Users should verify material figures before relying on them.
