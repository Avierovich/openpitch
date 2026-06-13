"""OpenPitch — open, real-time, fully-sourced intelligence on top AI startups.

Package layout:
  models.py          core data model (the spine; FRD §3)
  pipeline/          the daily producer: collect → transcribe → extract → reconcile → publish
  reconcile/         confidence model + reconciliation engine (FRD §4–5)
  mcp_server/        the local read interface for AI coding agents (FRD §8)
"""

__version__ = "0.0.1"
