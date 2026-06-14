"""Extraction stage (FRD §7, stage 4).

Turns a RawItem's unstructured text into structured Claims via an LLM, then
stamps each with provenance (from the RawItem) and a base confidence (from the
confidence model). The LLM call is injected, so extraction is fully testable
with a MockLLM — no network, no key.
"""

from .extract import (
    BATCH_EXTRACTION_SCHEMA,
    EXTRACTION_SCHEMA,
    build_batch_prompt,
    build_user_prompt,
    extract_claims,
    extract_claims_batch,
)

__all__ = [
    "extract_claims", "extract_claims_batch", "build_user_prompt",
    "build_batch_prompt", "EXTRACTION_SCHEMA", "BATCH_EXTRACTION_SCHEMA",
]
