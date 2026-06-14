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


class GeminiLLM:
    """Google Gemini Flash via google-genai (reference impl; adjust schema as the SDK evolves)."""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        from google import genai  # imported lazily so consumers don't need the dep

        self._genai = genai
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def complete_json(self, system: str, user: str, schema: dict) -> Any:
        from google.genai import types

        resp = self.client.models.generate_content(
            model=self.model,
            contents=[user],
            config=types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
                response_schema=schema,
            ),
        )
        return json.loads(resp.text)


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
        return GeminiLLM(key)
    raise ValueError(f"Unknown OPENPITCH_LLM provider: {name!r}")
