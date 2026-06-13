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
