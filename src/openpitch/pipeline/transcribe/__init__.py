"""Transcribe stage (FRD §7 stage 3) — podcast audio → text for extraction.

DATA-POLICY §3 is binding: prefer already-published transcripts; store only the
SHORT supporting phrases needed for a claim, never full copyrighted transcripts.
This module hands text to extraction; the extractor keeps only short `raw_text`
excerpts. Local whisper.cpp transcription is an optional fallback (lazy import)
used purely to *find* claims, not to republish source text.
"""

from __future__ import annotations

from ..sources.base import RawItem


def transcribe(item: RawItem) -> RawItem:
    """Ensure a RawItem has text to extract from.

    If it already has text (a published transcript/description), use it as-is.
    If it needs transcription and has audio, attempt whisper.cpp; on any failure
    (no dep / offline), leave it flagged so the run skips it gracefully.
    """
    if item.text and not item.needs_transcription:
        return item
    if item.needs_transcription and item.audio_url:
        text = _whisper(item.audio_url)
        if text:
            item.text = text
            item.needs_transcription = False
    return item


def _whisper(audio_url: str) -> str | None:
    try:
        import pywhispercpp.model as wcpp  # noqa: F401  (optional, heavy)
    except Exception:
        return None
    # Real implementation: download audio, transcribe, return text. Kept minimal
    # here — extraction stores only short phrases (DATA-POLICY §3), never the full text.
    return None
