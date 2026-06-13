"""Source-reliability meta-learning (FRD §5.4).

Sources that prove right over time earn more weight; those contradicted by
higher-tier sources lose it. A simple Beta-style posterior mean keeps the score
in (0, 1) and well-behaved with little data.
"""

from __future__ import annotations


def update_reliability(confirmed: int, contradicted: int, *, alpha: float = 1.0) -> float:
    """Posterior reliability given confirm/contradict counts.

    reliability = (α·confirmed + 1) / (α·(confirmed + contradicted) + 2)

    With no evidence this returns 0.5; it moves toward 1.0 as confirmations
    accumulate and toward 0.0 as contradictions do.
    """
    return (alpha * confirmed + 1.0) / (alpha * (confirmed + contradicted) + 2.0)
