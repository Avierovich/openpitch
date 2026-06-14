"""Core data model for OpenPitch (FRD §3).

These Pydantic models are the spine of the system. Everything else — the
pipeline that produces them, the MCP server and dashboard that read them —
depends on these shapes. They mirror the published JSON Schemas in `schemas/`.

Design invariants (BRD NFR-06/07):
  * No numeric value exists without provenance (sources) and a confidence score.
  * Values are never overwritten in place — history is append-only (see history JSONL).
  * Confidence is always < 1.0; we never assert certainty.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field

SCHEMA_VERSION = "1.0"


# ── Enums ────────────────────────────────────────────────────────────────────


class SourceType(str, Enum):
    FILING = "filing"        # SEC EDGAR (Form D, S-1) — highest trust
    NEWS = "news"            # press / journalism
    PODCAST = "podcast"      # founder/operator interviews — the freshness edge
    WEB = "web"              # company site, careers page, traffic signals
    SOCIAL = "social"        # social posts / rumor — lowest trust
    DERIVED = "derived"      # computed from other claims (FRD §5.6); confidence is propagated


class SpeakerRole(str, Enum):
    FOUNDER = "founder"
    EXEC = "exec"
    INVESTOR = "investor"
    JOURNALIST = "journalist"
    UNKNOWN = "unknown"


class EstimateType(str, Enum):
    REPORTED = "reported"    # a source stated it directly
    CONSENSUS = "consensus"  # synthesized from multiple agreeing sources
    IMPLIED = "implied"      # derived from leading indicators (FRD §5.5)


class EventType(str, Enum):
    FUNDING_ROUND = "funding_round"
    VALUATION_UPDATE = "valuation_update"
    METRIC_UPDATE = "metric_update"
    METRIC_THRESHOLD_CROSSED = "metric_threshold_crossed"
    UNIVERSE_ENTRY = "universe_entry"
    UNIVERSE_EXIT = "universe_exit"
    CONTRADICTION_FLAGGED = "contradiction_flagged"
    NEW_NOTABLE_CUSTOMER = "new_notable_customer"
    LEADERSHIP_CHANGE = "leadership_change"


# ── Provenance ───────────────────────────────────────────────────────────────


class Speaker(BaseModel):
    name: str | None = None
    role: SpeakerRole = SpeakerRole.UNKNOWN


class Source(BaseModel):
    type: SourceType
    name: str
    url: str | None = None
    locator: str | None = None        # e.g. "ep1042@00:34:12" or a text anchor
    published_at: date | None = None


# ── Claim: the atomic extracted assertion (FRD §3.1) ─────────────────────────


class Derivation(BaseModel):
    """Provenance for a derived claim (FRD §5.6)."""

    kind: str                       # identity | benchmark | concordance | surge
    formula: str                    # e.g. "ARR = MRR × 12"
    inputs: list[str] = Field(default_factory=list)   # input claim ids


class Claim(BaseModel):
    id: str
    company_id: str
    metric: str
    value: float | str | dict | None = None
    unit: str | None = None
    raw_text: str
    qualifiers: list[str] = Field(default_factory=list)   # run_rate, rounded, ...
    speaker: Speaker = Field(default_factory=Speaker)
    source: Source
    extracted_at: datetime
    extractor_model: str
    base_confidence: float = Field(ge=0.0, le=1.0)
    derivation: Derivation | None = None                  # set for DERIVED claims


# ── ResolvedValue: the reconciled best estimate (FRD §3.2) ───────────────────


class Range(BaseModel):
    low: float | None = None
    high: float | None = None


class Delta(BaseModel):
    previous: float | None = None
    change_pct: float | None = None
    since: date | None = None


class ResolvedValue(BaseModel):
    metric: str
    value: float | str | dict | None = None
    unit: str | None = None
    range: Range | None = None
    as_of: date
    estimate_type: EstimateType
    confidence: float = Field(ge=0.0, le=0.97)            # never assert certainty
    supporting_claims: list[str] = Field(default_factory=list)
    contradiction: bool = False
    delta: Delta | None = None
    history_ref: str | None = None


# ── Company profile (FRD §3.3) ───────────────────────────────────────────────


class Company(BaseModel):
    id: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    website: str | None = None
    category: str | None = None
    in_universe: bool = True
    vc_attention_score: float | None = None
    universe_rank: int | None = None
    metrics: dict[str, ResolvedValue] = Field(default_factory=dict)
    last_updated: date


# ── Event: the push/integration layer (FRD §8.5) ─────────────────────────────


class EventPayload(BaseModel):
    metric: str | None = None
    previous: float | str | None = None
    current: float | str | None = None
    change_pct: float | None = None


class Event(BaseModel):
    id: str
    schema_version: str = SCHEMA_VERSION
    type: EventType
    company_id: str
    company_name: str | None = None
    summary: str
    payload: EventPayload = Field(default_factory=EventPayload)
    confidence: float = Field(ge=0.0, le=1.0)
    estimate_type: EstimateType | None = None
    sources: list[Source] = Field(default_factory=list)
    detected_at: datetime


# ── Source registry entry (FRD §3.6) — learned reliability ───────────────────


class SourceReliability(BaseModel):
    type: SourceType
    tier_prior: float = Field(ge=0.0, le=1.0)
    reliability: float = Field(default=0.5, ge=0.0, le=1.0)   # learned over time
    claims_made: int = 0
    claims_confirmed: int = 0
    claims_contradicted: int = 0
    last_updated: date | None = None
