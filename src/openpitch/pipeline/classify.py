"""Taxonomy classification — assign a controlled main category + subcategory + a
free-text specialty to every company in one LLM pass, written to config/taxonomy.yaml.

This normalizes the messy free-text categories auto-discovery injects ("Voice AI",
"World models", "AI chips") into the controlled vocab the rest of the pipeline expects,
and adds the subcategory the dashboard uses to differentiate (video vs voice vs music…).
ponytail: one batched complete_json call over all companies; re-runnable.
"""

from __future__ import annotations

import yaml

from ..paths import config_dir
from .llm import LLMProvider

# Controlled two-level vocabulary. Edit freely — the classifier is told to pick from it.
VOCAB: dict[str, list[str]] = {
    "foundation-model": ["llm", "world-model", "reasoning", "multimodal", "open-source", "sovereign"],
    "generative-media": ["video", "image", "voice", "music", "3d-spatial", "avatar"],
    "ai-infra": ["chips", "inference", "gpu-cloud", "vector-db", "data-platform", "mlops", "networking"],
    "coding-agent": ["code-generation", "code-review", "dev-environment"],
    "ai-agents": ["general", "agent-security", "agent-infra", "browser"],
    "enterprise-ai": ["search", "knowledge", "productivity", "sales-cx", "support"],
    "vertical-app": ["legal", "healthcare", "finance", "security", "education", "marketing", "hr", "other"],
    "robotics": ["humanoid", "autonomous-driving", "drones", "manipulation", "industrial", "surgical"],
    "defense-ai": ["autonomy", "maritime", "air", "c2", "sensing"],
    "data-eval": ["labeling", "evaluation", "rlhf", "synthetic-data"],
}

_SYS = (
    "You classify AI companies into a fixed two-level taxonomy. For EACH company pick the "
    "single best `category` from the allowed main categories, a `subcategory` from that "
    "category's allowed list, and write a short free-text `specialty` (<=8 words) describing "
    "what they specifically do. Use the company's current label and domain as hints. If a "
    "company fits no main category well, use 'vertical-app' + 'other'. Return every company id."
)


def _schema() -> dict:
    return {
        "type": "object",
        "properties": {"companies": {"type": "array", "items": {
            "type": "object", "required": ["id", "category", "subcategory"], "properties": {
                "id": {"type": "string"}, "category": {"type": "string"},
                "subcategory": {"type": "string"}, "specialty": {"type": "string"},
            }}}},
        "required": ["companies"],
    }


def _user_prompt(companies: list[dict]) -> str:
    vocab_lines = "\n".join(f"- {m}: {', '.join(subs)}" for m, subs in VOCAB.items())
    rows = "\n".join(
        f"{c['id']} | {c['name']} | current: {c.get('category') or '?'} | {c.get('domain') or ''}"
        for c in companies
    )
    return f"ALLOWED TAXONOMY (main: subs):\n{vocab_lines}\n\nCOMPANIES (id | name | current | domain):\n{rows}"


def _coerce(rec: dict) -> dict | None:
    """Snap an LLM record onto the controlled vocab; drop if id/category invalid."""
    cid = (rec.get("id") or "").strip()
    cat = (rec.get("category") or "").strip()
    if not cid or cat not in VOCAB:
        return None
    sub = (rec.get("subcategory") or "").strip()
    if sub not in VOCAB[cat]:
        sub = VOCAB[cat][-1]  # fall back to the catch-all/last sub rather than invent
    out = {"category": cat, "subcategory": sub}
    if rec.get("specialty"):
        out["specialty"] = str(rec["specialty"]).strip()[:80]
    return cid, out


def classify(companies: list[dict], *, llm: LLMProvider, batch: int = 60) -> dict[str, dict]:
    """Classify companies (each {id,name,category,domain}) → {id: {category,subcategory,specialty}}."""
    out: dict[str, dict] = {}
    for i in range(0, len(companies), batch):
        chunk = companies[i : i + batch]
        data = llm.complete_json(_SYS, _user_prompt(chunk), _schema()) or {}
        for rec in data.get("companies", []):
            coerced = _coerce(rec)
            if coerced:
                out[coerced[0]] = coerced[1]
    return out


def write_taxonomy(classified: dict[str, dict]) -> int:
    """Merge classifications into config/taxonomy.yaml (keeps vocab; updates companies)."""
    path = config_dir() / "taxonomy.yaml"
    data = (yaml.safe_load(path.read_text()) if path.exists() else None) or {}
    data["vocab"] = VOCAB
    companies = data.get("companies") or {}
    companies.update(classified)
    data["companies"] = companies
    path.write_text(yaml.safe_dump(data, sort_keys=True, allow_unicode=True))
    return len(classified)


if __name__ == "__main__":  # ponytail: vocab-coercion self-check, no network
    assert _coerce({"id": "x", "category": "generative-media", "subcategory": "voice"})[1]["subcategory"] == "voice"
    assert _coerce({"id": "x", "category": "generative-media", "subcategory": "bogus"})[1]["subcategory"] in VOCAB["generative-media"]
    assert _coerce({"id": "x", "category": "not-a-category", "subcategory": "voice"}) is None
    print("ok")
