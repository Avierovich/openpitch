"""LLM provider abstraction (FRD §2, §13 Decision 2).

Default: Gemini Flash (free tier, long context, native JSON output). Swappable —
contributors can drop in Groq/Ollama by implementing `LLMProvider`. A MockLLM is
provided so the pipeline is fully testable without network or keys.

Only the pipeline uses this; the MCP server makes ZERO LLM calls (FRD §8.6).
"""

from __future__ import annotations

import json
import os
from typing import Any, Callable, Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    model: str

    def complete_json(self, system: str, user: str, schema: dict) -> Any:
        """Return parsed JSON conforming to `schema`."""
        ...


class MockLLM:
    """Deterministic stand-in for tests. `response` is a dict or user->dict callable."""

    model = "mock"

    def __init__(self, response: dict | Callable[[str], dict]):
        self._response = response

    def complete_json(self, system: str, user: str, schema: dict) -> Any:
        return self._response(user) if callable(self._response) else self._response


# Default free-tier model rotation: each model has its OWN daily free quota, so
# rotating multiplies free capacity. Ordered best-first.
DEFAULT_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.5-flash-lite"]


class GeminiLLM:
    """Gemini via google-genai with per-minute backoff and daily-quota model rotation.

    On a per-MINUTE 429 it backs off and retries the same model; on a per-DAY quota
    exhaustion it marks that model done for the run and rotates to the next.
    """

    def __init__(self, api_key: str, models: list[str] | None = None):
        from google import genai  # imported lazily so consumers don't need the dep

        self.client = genai.Client(api_key=api_key)
        self.models = models or list(DEFAULT_MODELS)
        self._exhausted: set[str] = set()

    @property
    def model(self) -> str:
        for m in self.models:
            if m not in self._exhausted:
                return m
        return self.models[-1]

    def complete_json(self, system: str, user: str, schema: dict) -> Any:
        import time

        from google.genai import types

        cfg = types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_schema=schema,
        )
        last: Exception | None = None
        for m in self.models:
            if m in self._exhausted:
                continue
            for attempt in range(3):
                try:
                    resp = self.client.models.generate_content(model=m, contents=[user], config=cfg)
                    return json.loads(resp.text)
                except Exception as exc:  # noqa: BLE001
                    last = exc
                    msg = str(exc)
                    rate = "429" in msg or "RESOURCE_EXHAUSTED" in msg or "503" in msg
                    daily = "PerDay" in msg or "per day" in msg.lower()
                    if rate and daily:
                        self._exhausted.add(m)  # rotate to next model
                        break
                    if rate:
                        time.sleep(2 * (attempt + 1))  # per-minute backoff
                        continue
                    raise
        raise last  # type: ignore[misc]


def get_provider() -> LLMProvider:
    """Build the configured provider from the environment.

    OPENPITCH_LLM selects the provider (default: gemini); LLM_API_KEY supplies the key.
    """
    from ...paths import load_dotenv
    load_dotenv()  # pick up a local .env (gitignored) if present

    name = os.environ.get("OPENPITCH_LLM", "gemini").lower()
    if name == "gemini":
        key = os.environ.get("LLM_API_KEY")
        if not key:
            raise RuntimeError("LLM_API_KEY is not set (see README — a free Gemini key).")
        override = os.environ.get("OPENPITCH_LLM_MODELS")
        models = [m.strip() for m in override.split(",") if m.strip()] if override else None
        return GeminiLLM(key, models=models)
    raise ValueError(f"Unknown OPENPITCH_LLM provider: {name!r}")
