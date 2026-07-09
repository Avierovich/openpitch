# MCP Tool Specification

## Purpose

This document defines the read-only MCP interface for OpenPitch v0.1. The MCP server should expose committed OpenPitch data to a user's existing agent. It should not make LLM calls.

## Principles

- Read-only. All 8 tools declare MCP annotations `readOnlyHint=true`, `destructiveHint=false`,
  `idempotentHint=true`, `openWorldHint=false`, so clients know they are safe to call freely.
- Local-first.
- No user API key.
- Every numeric answer includes provenance.
- No-data responses must be explicit.
- Tool outputs should be stable enough for agents to reason over.

Company objects (in `list_companies` / `get_company`) carry the two-level taxonomy:
`category` (controlled main), `subcategory` (controlled), `specialty` (short tag), and
`summary` (1–2 sentence business description).

## Shared Response Rules

Any response containing a metric value must include:

- `metric`;
- `value` or `range`;
- `unit`;
- `estimate_type`;
- `confidence`;
- `as_of`;
- `supporting_claims`;
- source summaries;
- `contradiction`;
- `history_ref` when available;
- `unconfirmed`, with `confirmed_value` / `confirmed_as_of` when the headline figure is an
  "in talks"/rumored mark and a more recent confirmed figure exists (recency stays the headline;
  the confirmed number is the anchor).

If data is missing, return:

```json
{
  "status": "not_found",
  "message": "No sourced value is available for this company/metric.",
  "company_id": "example",
  "metric": "arr"
}
```

Do not fabricate values.

## Tool: `list_companies`

### Args

```json
{
  "filter": "optional text filter",
  "segment": "global|mena|all",
  "sort_by": "universe_rank|last_updated|name|vc_attention_score",
  "limit": 50
}
```

### Returns

```json
{
  "companies": [
    {
      "id": "anthropic",
      "name": "Anthropic",
      "category": "foundation-model",
      "universe_rank": 2,
      "vc_attention_score": 98.2,
      "last_updated": "2026-06-13",
      "headline_metrics": {
        "valuation": { "value": 60000000000, "unit": "USD", "confidence": 0.82 },
        "arr": { "value": 92000000, "unit": "USD", "confidence": 0.62 }
      }
    }
  ]
}
```

## Tool: `get_company`

### Args

```json
{
  "id": "anthropic",
  "include_sources": true
}
```

### Returns

Full company profile with all resolved metrics and source summaries.

## Tool: `get_metric`

### Args

```json
{
  "company_id": "anthropic",
  "metric": "arr",
  "with_history": true
}
```

### Returns

```json
{
  "company_id": "anthropic",
  "metric": {
    "metric": "arr",
    "value": 92000000,
    "unit": "USD",
    "range": { "low": 80000000, "high": 110000000 },
    "as_of": "2026-06-09",
    "estimate_type": "consensus",
    "confidence": 0.62,
    "supporting_claims": ["clm_1", "clm_2"],
    "contradiction": false,
    "history_ref": "history/anthropic/arr.jsonl"
  },
  "sources": [
    {
      "name": "Example Source",
      "type": "news",
      "url": "https://example.com",
      "published_at": "2026-06-09"
    }
  ],
  "history": []
}
```

## Tool: `get_provenance`

### Args

```json
{
  "company_id": "anthropic",
  "metric": "arr"
}
```

### Returns

Underlying claims and confidence factors.

```json
{
  "company_id": "anthropic",
  "metric": "arr",
  "claims": [
    {
      "id": "clm_1",
      "value": 100000000,
      "unit": "USD",
      "raw_text": "short supporting phrase",
      "qualifiers": ["rounded"],
      "speaker": { "role": "founder" },
      "source": {
        "type": "podcast",
        "name": "Example Podcast",
        "url": "https://example.com",
        "locator": "00:34:12",
        "published_at": "2026-06-01"
      },
      "base_confidence": 0.54,
      "current_confidence": 0.51
    }
  ],
  "contradiction": false,
  "methodology_url": "docs/METHODOLOGY.md"
}
```

## Tool: `compare_companies`

### Args

```json
{
  "ids": ["anthropic", "mistral", "perplexity"],
  "metrics": ["arr", "valuation", "latest_round"]
}
```

### Returns

Side-by-side metric table with confidence and `as_of`.

## Tool: `what_moved`

### Args

```json
{
  "since": "2026-06-01",
  "min_confidence": 0.5,
  "include_contradictions": true,
  "limit": 50
}
```

### Returns

Metric deltas, new rounds, universe entries/exits, and contradictions. Events are
**newest-first** and capped at `limit` (default 50). If `since` is omitted it defaults to a
30-day window anchored to the freshest event date, **echoed back** as `since`. The response
carries `total` (pre-cap count) and `truncated` (bool) — narrow via `since`/`min_confidence`
when `truncated` is true.

## Tool: `get_events`

### Args

```json
{
  "since": "2026-06-01",
  "type": "valuation_update",
  "company_id": "anthropic",
  "min_confidence": 0.8,
  "limit": 50
}
```

### Returns

Filtered events matching `schemas/event.schema.json`, **newest-first**, capped at `limit`
(default 50), with `total` and `truncated`. Narrow via `since`/`type`/`company_id`/
`min_confidence` when `truncated` is true.

## Tool: `search`

### Args

```json
{
  "query": "coding agents with ARR over 100M",
  "limit": 25
}
```

### v0.1 Behavior

`search` may be simple lexical search over company names, aliases, categories, source names, and metric keys. It should not promise semantic ranking until implemented. Results are capped at `limit` (default 25) with `total`/`truncated` reported.

## Error Behavior

Use structured statuses:

- `ok`;
- `not_found`;
- `invalid_metric`;
- `invalid_company`;
- `data_unavailable`;
- `server_error`.

Example:

```json
{
  "status": "invalid_metric",
  "message": "Metric 'vibes' is not in the metric registry.",
  "allowed_metrics": ["arr", "valuation", "headcount"]
}
```

## Implementation Priority

1. `list_companies`
2. `get_company`
3. `get_metric`
4. `get_provenance`
5. `what_moved`
6. `get_events`
7. `compare_companies`
8. `search`
