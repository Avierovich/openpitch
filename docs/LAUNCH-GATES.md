# Launch Gates

## Purpose

This document defines the readiness gates for public launch. It exists to prevent OpenPitch from getting attention before it has enough proof to survive scrutiny.

The default bias is: **delay launch until the proof is credible.**

## Gate Summary

| Gate | Required For Public Launch | Status |
|---|---:|---|
| Credible seed dataset | Yes | Not started |
| Working MCP read path | Yes | Scaffolded |
| Provenance on every metric | Yes | Not started |
| Strong contradictions | Yes | Not started |
| Correction workflow | Yes | Not started |
| Methodology/data policy | Yes | Drafted/planned |
| Static dashboard or company cards | Yes | Not started |
| README demo asset | Yes | Not started |
| Clean-machine install test | Yes | Not started |
| MCP directory submissions | Before campaign | Not started |

Update this table as the repo moves toward launch.

## 1. Data Readiness

Minimum acceptable launch dataset:

- 10 companies.
- 3+ sourced metrics per company.
- Every displayed metric has:
  - `value` or explicit "unknown/not enough data";
  - `unit`;
  - `estimate_type`;
  - `confidence`;
  - `as_of`;
  - source name;
  - source URL or durable locator;
  - supporting claim ID.
- No placeholder values shown as real values.
- No stale metric shown without decay/confidence context.

Full 50-company coverage is not required for v0.1 if it would be thin.

## 2. Contradiction Readiness

Minimum acceptable launch asset:

- 2-3 strong public-source discrepancies.
- Each discrepancy has at least two public sources.
- Each source has a date and link/locator.
- Each discrepancy is reproducible from committed data.
- Each discrepancy has neutral language:
  - allowed: "public-source discrepancy";
  - allowed: "claim conflict";
  - allowed: "filing and public statement differ";
  - disallowed: "caught lying";
  - disallowed: "fraud";
  - disallowed: claims about intent.

Contradictions should be surprising but defensible. If the best examples require over-explaining, delay launch.

## 3. MCP Readiness

Required:

- MCP server starts locally.
- Documented install command works on a clean machine.
- At minimum, these tools work:
  - `list_companies`;
  - `get_company`;
  - `get_metric`;
  - `get_provenance`;
  - `get_events` or clear stub saying events are not available yet.
- No MCP tool strips provenance from numeric answers.
- No-data responses are explicit and non-hallucinatory.

Acceptance test:

```text
Question: "What is [seed company]'s latest ARR estimate and why should I trust it?"
Expected: answer includes value/range, confidence, estimate type, as_of, source names, and uncertainty.
```

## 4. Trust And Safety Readiness

Required before naming real companies in launch assets:

- `docs/METHODOLOGY.md` published.
- `docs/DATA-POLICY.md` published.
- `docs/CORRECTIONS.md` or equivalent correction path published.
- GitHub issue template for corrections.
- Disclaimer: public-source probabilistic intelligence, not investment advice.
- Copyright posture: do not republish full articles or full transcripts.

## 5. Demo Readiness

Required:

- README demo GIF or screenshot sequence.
- Demo uses real committed data.
- Demo does not require maintainer secrets.
- Static dashboard or company cards open without local setup.
- Methodology and correction links visible from README.

## 6. Distribution Readiness

Required before running the 30-day growth plan:

- HN first comment drafted.
- X contradiction thread drafted.
- Product Hunt assets drafted.
- Press/newsletter email drafted.
- MCP directory submissions prepared.
- Contradiction cards generated.
- Proof-of-freshness benchmark published.

## 7. Kill Criteria

Do not launch if any of these are true:

- MCP install fails on a clean machine.
- Demo uses fake or placeholder data without labeling.
- Fewer than 2 strong contradictions exist.
- Any visible metric lacks source/confidence/as_of.
- Dashboard or company cards look empty.
- Correction path is missing.
- Contradiction copy implies deception or intent.
- Maintainer cannot answer "how was this number produced?" from committed data.

## 8. Post-Launch Health Checks

Track daily for the first 14 days:

- broken install reports;
- correction issues;
- source link failures;
- HN/Reddit skepticism themes;
- stars by referrer;
- repeat MCP usage or recipe adoption;
- PRs adding/correcting data.
