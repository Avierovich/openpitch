# Events Specification

## Purpose

Events are OpenPitch's push layer. They tell downstream agents that something material changed: a new round, a metric update, a contradiction, or a universe entry/exit.

Events should be stable, filterable, and safe for automation.

## Event Contract

Events follow [schemas/event.schema.json](../schemas/event.schema.json).

Required fields:

- `id`;
- `schema_version`;
- `type`;
- `company_id`;
- `summary`;
- `confidence`;
- `detected_at`.

Events should also include sources whenever the event depends on a sourced claim.

## Event Types

| Type | Fires when |
|---|---|
| `funding_round` | A new funding round is detected |
| `valuation_update` | Valuation materially changes |
| `metric_update` | Any tracked metric materially changes |
| `metric_threshold_crossed` | A metric crosses a configured threshold |
| `universe_entry` | A company enters the tracked top-N universe |
| `universe_exit` | A company exits the tracked top-N universe |
| `contradiction_flagged` | High-confidence claim clusters conflict |
| `new_notable_customer` | A notable customer/logo is detected |
| `leadership_change` | A key hire/departure is detected |

## Materiality Thresholds

Suggested v0.1 defaults:

| Metric | Event threshold |
|---|---|
| ARR / revenue | Change >= 15% or crosses $10M/$50M/$100M/$250M |
| Valuation | Change >= 20% or new round valuation |
| Funding | Any new round or material extension |
| Headcount | Change >= 10% or crosses 100/500/1000 |
| Subscribers/customers | Change >= 25% |
| Contradiction | Rival cluster summed confidence >= 0.50 |

Thresholds should live in config once implemented.

## Dedupe Rules

Avoid event spam:

- Same company + metric + current value should not emit repeatedly.
- A changed confidence score alone should not emit unless it crosses a meaningful band.
- Multiple raw claims from the same article/feed item should collapse into one event.
- Corrections should emit only if they materially change a resolved value, contradiction state, or confidence band.

## Confidence Bands

For user-facing event summaries:

| Band | Confidence |
|---|---:|
| Low | < 0.50 |
| Medium | 0.50-0.74 |
| High | >= 0.75 |

Automation recipes should usually require medium or high confidence. Press workflows should default to high confidence.

## Example Event

```json
{
  "id": "evt_20260613_anthropic_valuation",
  "schema_version": "1.0",
  "type": "valuation_update",
  "company_id": "anthropic",
  "company_name": "Anthropic",
  "summary": "Anthropic valuation changed from $40B to $60B",
  "payload": {
    "metric": "valuation",
    "previous": 40000000000,
    "current": 60000000000,
    "change_pct": 50.0
  },
  "confidence": 0.82,
  "estimate_type": "reported",
  "sources": [
    {
      "name": "Example Source",
      "url": "https://example.com",
      "published_at": "2026-06-13"
    }
  ],
  "detected_at": "2026-06-13T05:00:00Z"
}
```

## Consumer Recipes

### Newsletter Agent

Filter:

```text
type in metric_update, valuation_update, funding_round, contradiction_flagged
confidence >= 0.50
```

Action: draft a short update with sources and uncertainty.

### Press Workflow

Filter:

```text
type in funding_round, valuation_update, contradiction_flagged
confidence >= 0.80
```

Action: alert a journalist to verify and contact the company.

### VC Scout Agent

Filter:

```text
type in universe_entry, metric_threshold_crossed
confidence >= 0.60
```

Action: add company to research queue and fetch full provenance.

## Event Channels

v0.1 target channels:

- MCP `get_events`;
- committed JSONL feed;
- RSS/Atom once dashboard publishing exists.

Future:

- GitHub release/commit webhooks;
- A2A agent task notifications.
