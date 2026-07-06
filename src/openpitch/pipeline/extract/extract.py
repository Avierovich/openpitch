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
    "mention doesn't fit a key, omit it. "
    "CRITICAL: revenue metrics (arr, mrr, acv) mean the company's OWN recurring revenue. "
    "GMV, gross merchandise value, TPV, total payment/transaction volume, bookings, AUM, and "
    "deposits are NOT revenue — never map a volume figure to arr/mrr/acv (a $6B GMV is not $6B ARR). "
    "Capture softening qualifiers (run_rate, rounded, "
    "approximate, forward_looking, unconfirmed) and the speaker's role. "
    "Qualifier rules: a valuation described as 'in talks', 'rumored', 'reportedly raising', "
    "'seeking', or 'could be valued at' -> add 'unconfirmed'. A revenue/ARR figure that is a "
    "future TARGET ('on track to reach', 'targeting', 'by 2027', 'aiming for') -> add "
    "'forward_looking' (it is a projection, not current revenue). Capture the speaker's role "
    "(founder, exec, investor, journalist, unknown). Quote the exact source phrase in raw_text. "
    "When company context (website, category, description) is provided, extract only for that "
    "specific company — different entities can share a name; omit metrics about same-named "
    "other organizations. "
    "If no metric is stated, return an empty claims array."
)

# Deterministic backstop for the GMV-as-revenue mislabel (the LLM, esp. weaker
# fallback models, sometimes ignores the prompt rule above). A revenue metric whose
# quoted phrase names a transaction VOLUME but not recurring revenue is dropped.
REVENUE_METRICS = {"arr", "mrr", "acv"}
_VOLUME_TERMS = (
    "gmv", "gross merchandise", "tpv", "total payment volume", "payment volume",
    "transaction volume", "transactions processed", "gross transaction", "bookings",
    "assets under management", "aum", "deposits", "throughput",
)
# Wording that genuinely denotes recurring revenue — rescues a claim that also
# mentions volume. Note "revenue growth" is NOT here: a % growth doesn't validate an
# absolute revenue figure, which is exactly the Foodics "$6B GMV and 29% revenue growth" trap.
_RECURRING_TERMS = (
    "arr", "annual recurring", "recurring revenue", "mrr", "acv", "run rate", "run-rate",
    "in revenue", "revenue of", "revenue reached", "revenue hit", "revenue was", "revenue is",
)


def is_volume_mislabel(metric: str, raw_text: str) -> bool:
    t = (raw_text or "").lower()
    return (
        metric in REVENUE_METRICS
        and any(v in t for v in _VOLUME_TERMS)
        and not any(r in t for r in _RECURRING_TERMS)
    )


def build_user_prompt(raw_item: RawItem, company_name: str, metric_keys: list[str]) -> str:
    return (
        f"Company: {company_name}\n"
        f"Allowed metric keys: {', '.join(metric_keys)}\n"
        f"Source type: {raw_item.source_type.value}\n"
        f"Title: {raw_item.title or ''}\n\n"
        f"Text:\n{raw_item.text}"
    )


def build_batch_prompt(items: list[RawItem], company, metric_keys: list[str], *, per_item_chars: int = 1500) -> str:
    blocks = []
    for i, it in enumerate(items):
        blocks.append(
            f"[{i}] ({it.source_type.value}) {it.title or ''}\n{(it.text or '')[:per_item_chars]}"
        )
    # Company context disambiguates same-named entities (Sierra the AI company vs
    # Sierra Space / Sierra Leone) — without it the LLM can only guess from the name.
    about = "; ".join(p for p in (
        f"website {company.website}" if getattr(company, "website", None) else None,
        getattr(company, "category", None),
        getattr(company, "summary", None),
    ) if p)
    context = (f"About this company: {about}\n"
               "Only extract metrics about THIS company; other organizations may share "
               "the name — skip those.\n") if about else ""
    return (
        f"Company: {company.name}\n"
        f"{context}"
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
        if is_volume_mislabel(metric, rc.get("raw_text", "")):
            continue  # GMV/TPV/etc. mislabeled as revenue
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
    per_item_chars: int = 1500,
) -> list[Claim]:
    """Extract Claims from MANY RawItems in a single LLM call (quota-efficient).

    Each returned claim references the item_index it came from, so provenance is
    attached to the right source. Unknown metric keys / bad indices are dropped.
    `per_item_chars` bounds each item's text in the prompt — gap-fill passes full
    article bodies with a larger budget (a valuation sentence can sit mid-article).
    """
    now = now or datetime.now()
    if not items:
        return []
    prompt = build_batch_prompt(items, company, metric_keys, per_item_chars=per_item_chars)
    data = llm.complete_json(EXTRACTION_SYSTEM, prompt, BATCH_EXTRACTION_SCHEMA) or {}

    claims: list[Claim] = []
    for rc in data.get("claims", []):
        metric = rc.get("metric")
        idx = rc.get("item_index")
        if metric not in metric_keys or not isinstance(idx, int) or not (0 <= idx < len(items)):
            continue
        if is_volume_mislabel(metric, rc.get("raw_text", "")):
            continue  # GMV/TPV/etc. mislabeled as revenue
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
