"""Extraction stage (FRD §7, stage 4).

Turns a RawItem's unstructured text into structured Claims via an LLM, then
stamps each with provenance (from the RawItem) and a base confidence (from the
confidence model). The LLM call is injected, so extraction is fully testable
with a MockLLM — no network, no key.
"""

from .extract import EXTRACTION_SCHEMA, build_user_prompt, extract_claims

__all__ = ["extract_claims", "build_user_prompt", "EXTRACTION_SCHEMA"]
