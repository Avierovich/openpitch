"""Confidence model (FRD §4).

Confidence is multiplicative over independent factors, then boosted by
corroboration across agreeing claims. It is always capped below 1.0 — we never
assert certainty (BRD NFR-06).

    base(claim)    = tier_prior × speaker_weight × qualifier_penalty
    current(claim) = base × decay(age, τ_metric)
    resolved       = corroborate({current(c) for agreeing claims})
"""

from __future__ import annotations

import math
from datetime import date

from ..models import Claim, SourceType, SpeakerRole

MAX_CONFIDENCE = 0.97

# §4.1 — source tier priors
TIER_PRIORS: dict[SourceType, float] = {
    SourceType.FILING: 0.95,
    SourceType.NEWS: 0.75,
    SourceType.PODCAST: 0.60,
    SourceType.WEB: 0.50,
    SourceType.SOCIAL: 0.30,
    SourceType.DERIVED: 0.50,  # placeholder; derived claims carry propagated confidence
}

# §4.2 — speaker authority
SPEAKER_WEIGHTS: dict[SpeakerRole, float] = {
    SpeakerRole.FOUNDER: 1.0,
    SpeakerRole.EXEC: 1.0,
    SpeakerRole.INVESTOR: 0.8,
    SpeakerRole.JOURNALIST: 0.7,
    SpeakerRole.UNKNOWN: 0.5,
}

# §4.3 — qualifier penalties (multiplicative softeners)
QUALIFIER_PENALTIES: dict[str, float] = {
    "run_rate": 0.9,
    "rounded": 0.9,
    "approximate": 0.85,
    "forward_looking": 0.7,
    "unconfirmed": 0.6,
}


def tier_prior(source_type: SourceType, reliability: float | None = None) -> float:
    """Source-type prior, optionally blended with a learned reliability (§5.4)."""
    prior = TIER_PRIORS.get(source_type, 0.4)
    if reliability is None:
        return prior
    return (prior + reliability) / 2.0


def speaker_weight(role: SpeakerRole) -> float:
    return SPEAKER_WEIGHTS.get(role, 0.5)


def qualifier_penalty(qualifiers: list[str]) -> float:
    factor = 1.0
    for q in qualifiers:
        factor *= QUALIFIER_PENALTIES.get(q, 1.0)
    return factor


def decay(age_days: float, tau: float) -> float:
    """Exponential confidence decay; fresher = higher (§4.4)."""
    if age_days <= 0:
        return 1.0
    return math.exp(-age_days / tau)


def base_confidence(claim: Claim, reliability: float | None = None) -> float:
    # Derived claims carry a confidence propagated from their inputs (FRD §5.6);
    # don't recompute it from source/speaker priors.
    if claim.source.type is SourceType.DERIVED:
        return claim.base_confidence
    return (
        tier_prior(claim.source.type, reliability)
        * speaker_weight(claim.speaker.role)
        * qualifier_penalty(claim.qualifiers)
    )


def current_confidence(
    claim: Claim,
    *,
    as_of: date,
    tau: float,
    reliability: float | None = None,
) -> float:
    """Decay-adjusted confidence of a single claim as of a given run date."""
    pub = claim.source.published_at
    age = (as_of - pub).days if pub else 0
    return min(base_confidence(claim, reliability) * decay(age, tau), MAX_CONFIDENCE)


def corroborate(confidences: list[float]) -> float:
    """Noisy-OR over agreeing claims — independent evidence compounds (§4.5)."""
    if not confidences:
        return 0.0
    product = 1.0
    for c in confidences:
        product *= 1.0 - max(0.0, min(c, 1.0))
    return min(1.0 - product, MAX_CONFIDENCE)
