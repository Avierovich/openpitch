"""LLM claim extraction (FRD §7 stage 4, §5.5).

`build_user_prompt` and `extract_claims` are pure given an injected LLMProvider,
so the whole stage is unit-tested with a MockLLM.
"""

from __future__ import annotations

import hashlib
from datetime import datetime

from ...models import Claim, Source, Speaker, SpeakerRole
from ..llm import LLMProvider
from ..sources.base import RawItem
from ...reconcile.confidence import base_confidence

# Output contract the LLM must satisfy (also used as the response schema).
EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["metric", "value", "raw_text"],
                "properties": {
                    "metric": {"type": "string"},
                    "value": {"type": "number"},
                    "unit": {"type": "string"},
                    "qualifiers": {"type": "array", "items": {"type": "string"}},
                    "speaker_role": {"type": "string"},
                    "raw_text": {"type": "string"},
                },
            },
        }
    },
    "required": ["claims"],
}

# Batched variant: one LLM call covers many source items (each claim tags its
# originating item_index). This is the key free-tier-quota lever (FRD §7).
BATCH_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["item_index", "metric", "value", "raw_text"],
                "properties": {
                    "item_index": {"type": "integer"},
                    "metric": {"type": "string"},
                    "value": {"type": "number"},
                    "unit": {"type": "string"},
                    "qualifiers": {"type": "array", "items": {"type": "string"}},
                    "speaker_role": {"type": "string"},
                    "raw_text": {"type": "string"},
                },
            },
        }
    },
    "required": ["claims"],
}

EXTRACTION_SYSTEM = (
    "You extract hard business metrics about a specific company from text. "
    "Return ONLY metrics that are explicitly stated about THAT company. Do not infer, "
    "guess, or include forward-looking targets as facts. Normalize values to base units: "
    "money in absolute USD (e.g. '$100M' -> 100000000), counts as integers, percentages as "
    "plain numbers (e.g. '40%' -> 40). Map each to one of the allowed metric keys; if a "
    "mention doesn't fit a key, omit it. Capture softening qualifiers (run_rate, rounded, "
    "approximate, forward_looking, unconfirmed) and the speaker's role "
    "(founder, exec, investor, journalist, unknown). Quote the exact source phrase in raw_text. "
    "If no metric is stated, return an empty claims array."
)


def build_user_prompt(raw_item: RawItem, company_name: str, metric_keys: list[str]) -> str:
    return (
        f"Company: {company_name}\n"
        f"Allowed metric keys: {', '.join(metric_keys)}\n"
        f"Source type: {raw_item.source_type.value}\n"
        f"Title: {raw_item.title or ''}\n\n"
        f"Text:\n{raw_item.text}"
    )


def build_batch_prompt(items: list[RawItem], company_name: str, metric_keys: list[str], *, per_item_chars: int = 1500) -> str:
    blocks = []
    for i, it in enumerate(items):
        blocks.append(
            f"[{i}] ({it.source_type.value}) {it.title or ''}\n{(it.text or '')[:per_item_chars]}"
        )
    return (
        f"Company: {company_name}\n"
        f"Allowed metric keys: {', '.join(metric_keys)}\n"
        f"Extract metrics about THIS company from the numbered sources below. "
        f"Tag every claim with the item_index it came from.\n\n"
        + "\n\n".join(blocks)
    )


def _role(value: str | None) -> SpeakerRole:
    try:
        return SpeakerRole(value) if value else SpeakerRole.UNKNOWN
    except ValueError:
        return SpeakerRole.UNKNOWN


def _claim_id(company_id: str, metric: str, value, source_name: str, published) -> str:
    basis = f"{company_id}|{metric}|{value}|{source_name}|{published}".encode()
    return "clm_" + hashlib.sha256(basis).hexdigest()[:10]


def extract_claims(
    raw_item: RawItem,
    company,
    *,
    llm: LLMProvider,
    metric_keys: list[str],
    now: datetime | None = None,
) -> list[Claim]:
    """Extract Claims from one RawItem. Unknown metric keys are dropped."""
    now = now or datetime.now()
    prompt = build_user_prompt(raw_item, company.name, metric_keys)
    data = llm.complete_json(EXTRACTION_SYSTEM, prompt, EXTRACTION_SCHEMA) or {}

    source = Source(
        type=raw_item.source_type,
        name=raw_item.source_name,
        url=raw_item.url,
        locator=raw_item.locator,
        published_at=raw_item.published_at,
    )

    claims: list[Claim] = []
    for rc in data.get("claims", []):
        metric = rc.get("metric")
        if metric not in metric_keys:
            continue  # never trust the model to invent metric keys
        speaker = Speaker(name=None, role=_role(rc.get("speaker_role")))
        claim = Claim(
            id=_claim_id(company.id, metric, rc.get("value"), source.name, source.published_at),
            company_id=company.id,
            metric=metric,
            value=rc.get("value"),
            unit=rc.get("unit"),
            raw_text=rc.get("raw_text", ""),
            qualifiers=rc.get("qualifiers", []) or [],
            speaker=speaker,
            source=source,
            extracted_at=now,
            extractor_model=llm.model,
            base_confidence=0.0,  # set below
        )
        claim.base_confidence = round(base_confidence(claim), 4)
        claims.append(claim)
    return claims


def extract_claims_batch(
    items: list[RawItem],
    company,
    *,
    llm: LLMProvider,
    metric_keys: list[str],
    now: datetime | None = None,
) -> list[Claim]:
    """Extract Claims from MANY RawItems in a single LLM call (quota-efficient).

    Each returned claim references the item_index it came from, so provenance is
    attached to the right source. Unknown metric keys / bad indices are dropped.
    """
    now = now or datetime.now()
    if not items:
        return []
    prompt = build_batch_prompt(items, company.name, metric_keys)
    data = llm.complete_json(EXTRACTION_SYSTEM, prompt, BATCH_EXTRACTION_SCHEMA) or {}

    claims: list[Claim] = []
    for rc in data.get("claims", []):
        metric = rc.get("metric")
        idx = rc.get("item_index")
        if metric not in metric_keys or not isinstance(idx, int) or not (0 <= idx < len(items)):
            continue
        it = items[idx]
        source = Source(
            type=it.source_type, name=it.source_name, url=it.url,
            locator=it.locator, published_at=it.published_at,
        )
        claim = Claim(
            id=_claim_id(company.id, metric, rc.get("value"), source.name, source.published_at),
            company_id=company.id, metric=metric, value=rc.get("value"), unit=rc.get("unit"),
            raw_text=rc.get("raw_text", ""), qualifiers=rc.get("qualifiers", []) or [],
            speaker=Speaker(role=_role(rc.get("speaker_role"))), source=source,
            extracted_at=now, extractor_model=llm.model, base_confidence=0.0,
        )
        claim.base_confidence = round(base_confidence(claim), 4)
        claims.append(claim)
    return claims
