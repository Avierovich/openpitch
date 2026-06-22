# Product Requirements Document (PRD)

## Project: OpenPitch v0.1

| | |
|---|---|
| **Date** | 2026-06-13 |
| **Status** | Draft, implementation in progress |
| **Companions** | [BRD](BRD.md), [FRD](FRD.md), [LAUNCH-GATES](LAUNCH-GATES.md) |

## 1. Product Thesis

OpenPitch is a sourced, confidence-scored intelligence layer for AI startup metrics that AI agents can call directly. The v0.1 product should prove one narrow promise:

> An AI builder can install OpenPitch locally, ask their agent about a covered AI startup, and receive a current metric answer with sources, confidence, and provenance instead of a hallucinated number.

This PRD intentionally narrows the broader vision in the BRD/FRD into the first shippable product.

## 2. Primary User

**AI builders using Codex, Claude Code, or another MCP-compatible agent.**

They need grounded company facts inside their own tools, demos, agents, newsletters, internal workflows, or research products. They care less about a broad PitchBook replacement and more about not shipping agent answers that invent private-company numbers.

Secondary users are investors, founders, journalists, and analysts who browse the dashboard or use the data as a cited first look.

## 3. Jobs To Be Done

1. **Ground an agent answer.** When a user asks "what is Company X's ARR or latest valuation?", the agent should call OpenPitch and return a sourced answer.
2. **Inspect provenance.** When a user sees a number, they should be able to trace the source, date, confidence, and supporting claims.
3. **Resolve conflicting public claims.** When sources disagree, the product should show the conflict and the consensus/range instead of hiding it.
4. **Subscribe to movement.** When a tracked metric changes, downstream agents should be able to react through events.
5. **Correct public data.** When a user spots a bad or stale metric, they should have a clear public correction path.

## 4. v0.1 Scope

### Must Ship

- A credible seed dataset: 10 companies, 3+ metrics each, every value with source, confidence, and `as_of`.
- At least 2-3 strong public-source discrepancies, framed neutrally as contradictions or claim conflicts.
- Local MCP server with read-only tools for company lookup, metric lookup, provenance, and events.
- Static dashboard or static company-card pages generated from committed data.
- JSON data files committed in the repo.
- Methodology page explaining confidence, reconciliation, source policy, and corrections.
- Correction workflow using GitHub issues and public evidence.
- README with a working demo path and install instructions.
- Human-readable metric labels in product surfaces; implementation keys like `arr` should render as `ARR / revenue`.
- Top-50 company universe retained by rank tiers: Tier 1 ranks 1-10, Tier 2 ranks 11-25, Tier 3 ranks 26-50.

Current implementation status:

- Built: data model, reconciliation, derivation, source adapters, batched extraction, MCP tools, dashboard, event feed, daily workflow, Groq transcription, raw-GitHub data fetcher, and A2A agent card generation.
- Partial: 5-company seed exists and is suitable for software testing, but v0.1 launch still requires a 10-company human-audited seed and selected contradiction assets.
- Selected brand direction: **Terminal Proof** logo in `docs/brand/logo-options/05-terminal-proof.svg`.

### Should Ship

- `what_moved` event feed from seed data.
- Basic history JSONL for each seed metric.
- Proof-of-freshness benchmark with 5 examples.
- Shareable contradiction cards.
- Build-with-OpenPitch recipes for AI builders.

### Out Of Scope For v0.1

- Full 50-company coverage if it would be sparse.
- Paid or auth-walled data sources.
- Hosted user accounts or write UI.
- Investment recommendations.
- Cross-company headcount-to-ARR point estimates as a headline metric.
- Real-time or intra-day refresh.

## 5. Core User Flows

### Flow A: First Agent Answer

1. User installs MCP server.
2. User asks: "What is Anthropic's latest ARR estimate and sources?"
3. Agent calls `get_metric`.
4. OpenPitch returns value/range, confidence, estimate type, `as_of`, and source references.
5. Agent summarizes the answer and includes uncertainty.

Acceptance criteria:
- No API key required by the end user.
- Response includes provenance.
- Empty or unknown data returns a clear "not enough sourced data" response.

### Flow B: Provenance Inspection

1. User asks why a value is trusted.
2. Agent calls `get_provenance`.
3. OpenPitch returns supporting claims, source metadata, confidence factors, and contradiction state.

Acceptance criteria:
- Every numeric answer can be traced back to at least one source.
- Claims expose raw text excerpts only within copyright-safe limits.

### Flow C: Contradiction Review

1. User opens a company detail page or asks for contradictions.
2. Product shows claim clusters, source dates, and consensus/range.
3. User can open source links or file a correction.

Acceptance criteria:
- Language is neutral: "public-source discrepancy" or "claim conflict."
- The product never alleges deception or intent.

### Flow D: Correction

1. User opens a correction issue.
2. User provides company, metric, disputed value, and public evidence.
3. Maintainer reviews and commits accepted correction.
4. History records the change.

Acceptance criteria:
- Correction path is visible from README and methodology pages.
- Accepted corrections preserve audit history.

## 6. Product Principles

- **Receipts over certainty.** Confidence is visible; source links are mandatory.
- **Narrow and dense beats broad and thin.** A strong 10-company seed is better than a weak 50-company launch.
- **Contradictions are product features.** Disagreement is surfaced, not hidden.
- **No hidden data magic.** Users should understand how a number was produced.
- **Local first.** MCP reads committed data locally; no hosted backend is required.
- **Corrections improve trust.** Public correction history is a credibility asset.
- **Ranked, not random.** The product retains a dynamic top-50 universe grouped by tiers; the seed dataset is only the proof subset.

## 7. Success Metrics

### Activation
- Time from README to first agent answer: target under 60 seconds after package release.
- Clean-machine MCP install success.

### Trust
- 100% of displayed metrics have source, confidence, estimate type, and `as_of`.
- Number of correction issues resolved.
- Claims later confirmed vs contradicted.

### Usage
- MCP tool calls in demos/local testing.
- Event feed consumers or recipe usage.
- Dashboard/company-card visits.

### Community
- Stars from high-intent sources: HN, MCP directories, newsletters.
- PRs adding sources, companies, corrections, or adapters.

## 8. Open Questions

- Which 5 additional companies complete the v0.1 seed beyond the current 5?
- What exact threshold qualifies a contradiction as launch-worthy?
- Should v0.1 expose A2A only as the generated Agent Card, or add a fuller A2A task endpoint later?
- Is the current static dashboard sufficient for launch, or does it need filtering/search before launch?
- Which source excerpts can be stored safely without republishing copyrighted text?
