"""Transcribe stage (FRD §7 stage 3) — podcast audio → text for extraction.

DATA-POLICY §3 is binding: prefer already-published transcripts; store only the
SHORT supporting phrases needed for a claim (the extractor does that), never full
copyrighted transcripts. Transcription is used purely to *find* claims.

Order of preference (hosted-first, no local model required):
  1. Already-published transcript / show notes (free, instant) — keep item.text.
  2. Groq Whisper Large v3 Turbo (hosted, free tier ~2k/day, 216x realtime, multilingual).
  3. Local faster-whisper/whisper.cpp (optional offline fallback).
"""

from __future__ import annotations

import os

from ..sources.base import RawItem

GROQ_STT_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
GROQ_STT_MODEL = "whisper-large-v3-turbo"
MAX_AUDIO_BYTES = 25 * 1024 * 1024  # free-tier file ceiling; chunking is a follow-up


def transcribe(item: RawItem) -> RawItem:
    """Ensure a RawItem has text to extract from (hosted Groq Whisper preferred)."""
    if item.text and not item.needs_transcription:
        return item
    if item.needs_transcription and item.audio_url:
        text = _groq_transcribe(item.audio_url) or _whisper(item.audio_url)
        if text:
            item.text = text
            item.needs_transcription = False
    return item


def _groq_transcribe(audio_url: str) -> str | None:
    """Hosted transcription via Groq's free Whisper tier (no local model)."""
    from ...paths import load_dotenv

    load_dotenv()
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return None
    import httpx

    try:
        audio = httpx.get(audio_url, timeout=180, follow_redirects=True).content
    except Exception:  # noqa: BLE001
        return None
    if not audio or len(audio) > MAX_AUDIO_BYTES:
        return None  # oversized for the free tier; chunking TODO
    try:
        r = httpx.post(
            GROQ_STT_URL,
            headers={"Authorization": f"Bearer {key}"},
            files={"file": ("audio.mp3", audio, "audio/mpeg")},
            data={"model": GROQ_STT_MODEL, "response_format": "text"},
            timeout=300,
        )
        if r.status_code == 200:
            return (r.text or "").strip() or None
    except Exception:  # noqa: BLE001
        return None
    return None


def _whisper(audio_url: str) -> str | None:
    """Optional local fallback (faster-whisper / whisper.cpp). Off unless installed."""
    try:
        import faster_whisper  # noqa: F401
    except Exception:  # noqa: BLE001
        return None
    # Real impl: download audio, transcribe with a small model, return text.
    # Extraction stores only short phrases (DATA-POLICY §3). Kept minimal here.
    return None
