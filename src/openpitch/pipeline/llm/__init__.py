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
        if last:
            raise last
        raise RuntimeError("All configured Gemini models are exhausted or unavailable.")


class GroqLLM:
    """Groq chat-completions JSON extractor.

    Groq is useful for bulk sourcing runs when Gemini free quota is exhausted.
    It uses Groq's OpenAI-compatible endpoint and asks for JSON-object output.
    """

    def __init__(self, api_key: str, model: str | None = None):
        self.api_key = api_key
        self.model = model or os.environ.get("OPENPITCH_GROQ_MODEL", "llama-3.3-70b-versatile")

    def complete_json(self, system: str, user: str, schema: dict) -> Any:
        import httpx

        json_system = f"{system}\nRespond with a valid JSON object."
        resp = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.model,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": json_system},
                    {"role": "user", "content": user},
                ],
            },
            timeout=60.0,
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"Groq error {resp.status_code}: {resp.text[:500]}")
        content = resp.json()["choices"][0]["message"]["content"]
        return json.loads(content)


def _is_quota(msg: str) -> bool:
    return "429" in msg or "RESOURCE_EXHAUSTED" in msg or "exhausted" in msg.lower()


class FallbackLLM:
    """Try providers in order; on quota exhaustion fall through to the next.

    This is what multiplies free capacity: each Gemini key has its own daily
    quota (and rotates 3 models internally), and Groq's quota is separate again.
    A run only stops extracting when EVERY provider is drained.
    """

    def __init__(self, providers: list[LLMProvider]):
        self.providers = providers

    @property
    def model(self) -> str:
        return self.providers[0].model

    def complete_json(self, system: str, user: str, schema: dict) -> Any:
        last: Exception | None = None
        for p in self.providers:
            try:
                return p.complete_json(system, user, schema)
            except Exception as exc:  # noqa: BLE001
                last = exc
                if _is_quota(str(exc)):
                    continue  # this provider is spent — try the next
                raise
        raise last or RuntimeError("No LLM providers configured.")


def get_provider() -> LLMProvider:
    """Build the configured provider chain from the environment.

    OPENPITCH_LLM selects the primary provider (default: gemini). LLM_API_KEY may
    be a comma-separated list of Gemini keys (each its own daily quota). When a
    GROQ_API_KEY is also present it's appended as a final fallback, so a run keeps
    going after Gemini's free quota is exhausted.
    """
    from ...paths import load_dotenv
    load_dotenv()  # pick up a local .env (gitignored) if present

    name = os.environ.get("OPENPITCH_LLM", "gemini").lower()
    override = os.environ.get("OPENPITCH_LLM_MODELS")
    models = [m.strip() for m in override.split(",") if m.strip()] if override else None
    groq_key = os.environ.get("GROQ_API_KEY")

    providers: list[LLMProvider] = []
    if name == "gemini":
        raw = os.environ.get("LLM_API_KEY")
        if not raw:
            raise RuntimeError("LLM_API_KEY is not set (see README — a free Gemini key).")
        for key in [k.strip() for k in raw.split(",") if k.strip()]:
            providers.append(GeminiLLM(key, models=models))
        if groq_key:
            providers.append(GroqLLM(groq_key))  # separate free quota — final fallback
    elif name == "groq":
        if not groq_key:
            raise RuntimeError("GROQ_API_KEY is not set.")
        providers.append(GroqLLM(groq_key))
    else:
        raise ValueError(f"Unknown OPENPITCH_LLM provider: {name!r}")

    return providers[0] if len(providers) == 1 else FallbackLLM(providers)
