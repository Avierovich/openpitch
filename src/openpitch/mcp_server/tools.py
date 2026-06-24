"""MCP tool logic (MCP-SPEC) — pure functions over the committed data.

Separated from the MCP wiring (server.py) so it's unit-testable without the SDK.
Read-only; makes ZERO LLM calls; never strips provenance; explicit no-data.
"""

from __future__ import annotations

from .. import store
from ..config import load_metrics, metric_keys
from ..reconcile.confidence import base_confidence, current_confidence

_TODAY = None  # injected for deterministic tests via _today()


def _today():
    from datetime import date
    return _TODAY or date.today()


def _not_found(company_id: str, metric: str | None = None) -> dict:
    return {
        "status": "not_found",
        "message": "No sourced value is available for this company/metric.",
        "company_id": company_id,
        **({"metric": metric} if metric else {}),
    }


def _headline(company) -> dict:
    out = {}
    for k in ("valuation", "arr"):
        rv = company.metrics.get(k)
        if rv:
            out[k] = {"value": rv.value, "unit": rv.unit, "confidence": rv.confidence}
    return out


def list_companies(filter: str | None = None, segment: str = "all",
                   sort_by: str = "universe_rank", limit: int = 50) -> dict:
    comps = store.read_all_companies()
    if segment in ("global", "mena"):
        comps = [c for c in comps if (c.segment or "global") == segment]
    if filter:
        f = filter.lower()
        comps = [c for c in comps if f in c.name.lower() or f in (c.category or "").lower()
                 or f in (c.subcategory or "").lower() or f in (c.specialty or "").lower()]
    keyers = {
        "universe_rank": lambda c: (c.universe_rank is None, c.universe_rank or 1e9),
        "name": lambda c: c.name.lower(),
        "last_updated": lambda c: str(c.last_updated),
        "vc_attention_score": lambda c: -(c.vc_attention_score or 0),
    }
    comps.sort(key=keyers.get(sort_by, keyers["universe_rank"]))
    return {
        "status": "ok",
        "companies": [
            {
                "id": c.id, "name": c.name, "category": c.category,
                "subcategory": c.subcategory, "specialty": c.specialty, "segment": c.segment,
                "universe_rank": c.universe_rank, "vc_attention_score": c.vc_attention_score,
                "last_updated": str(c.last_updated), "headline_metrics": _headline(c),
            }
            for c in comps[:limit]
        ],
    }


def get_company(id: str, include_sources: bool = True) -> dict:
    c = store.read_company(id)
    if not c:
        return _not_found(id)
    return {"status": "ok", "company": c.model_dump(mode="json")}


def _sources_for(company_id: str, metric: str) -> list[dict]:
    out = []
    for cl in store.read_claims(company_id):
        if cl.metric == metric and cl.source.type.value != "derived":
            out.append({"name": cl.source.name, "type": cl.source.type.value,
                        "url": cl.source.url, "published_at": str(cl.source.published_at) if cl.source.published_at else None})
    return out


def get_metric(company_id: str, metric: str, with_history: bool = False) -> dict:
    if metric not in metric_keys():
        return {"status": "invalid_metric", "message": f"Metric '{metric}' is not in the registry.",
                "allowed_metrics": metric_keys()}
    c = store.read_company(company_id)
    if not c:
        return _not_found(company_id, metric)
    rv = c.metrics.get(metric)
    if not rv:
        return _not_found(company_id, metric)
    resp = {"status": "ok", "company_id": company_id, "metric": rv.model_dump(mode="json"),
            "sources": _sources_for(company_id, metric)}
    if with_history:
        resp["history"] = store.read_history(company_id, metric)
    return resp


def get_provenance(company_id: str, metric: str) -> dict:
    c = store.read_company(company_id)
    if not c or metric not in c.metrics:
        return _not_found(company_id, metric)
    defs = load_metrics()
    tau = defs[metric].tau if metric in defs else 180
    claims_out = []
    for cl in store.read_claims(company_id):
        if cl.metric != metric:
            continue
        claims_out.append({
            "id": cl.id, "value": cl.value, "unit": cl.unit, "raw_text": cl.raw_text,
            "qualifiers": cl.qualifiers, "speaker": {"role": cl.speaker.role.value},
            "source": cl.source.model_dump(mode="json"),
            "base_confidence": round(base_confidence(cl), 4),
            "current_confidence": round(current_confidence(cl, as_of=_today(), tau=tau), 4),
            "derivation": cl.derivation.model_dump(mode="json") if cl.derivation else None,
        })
    return {"status": "ok", "company_id": company_id, "metric": metric,
            "claims": claims_out, "contradiction": c.metrics[metric].contradiction,
            "methodology_url": "docs/METHODOLOGY.md"}


def compare_companies(ids: list[str], metrics: list[str]) -> dict:
    rows = []
    for cid in ids:
        c = store.read_company(cid)
        if not c:
            rows.append({"company_id": cid, "status": "not_found"})
            continue
        cells = {}
        for m in metrics:
            rv = c.metrics.get(m)
            cells[m] = ({"value": rv.value, "unit": rv.unit, "confidence": rv.confidence,
                         "as_of": str(rv.as_of), "estimate_type": rv.estimate_type.value,
                         "contradiction": rv.contradiction} if rv else None)
        rows.append({"company_id": cid, "name": c.name, "metrics": cells})
    return {"status": "ok", "comparison": rows}


def get_events(since: str | None = None, type: str | None = None,
               company_id: str | None = None, min_confidence: float = 0.0) -> dict:
    evs = store.read_events(since=since)
    if type:
        evs = [e for e in evs if e.get("type") == type]
    if company_id:
        evs = [e for e in evs if e.get("company_id") == company_id]
    evs = [e for e in evs if (e.get("confidence") or 0) >= min_confidence]
    return {"status": "ok", "events": evs}


def what_moved(since: str | None = None, min_confidence: float = 0.0,
               include_contradictions: bool = True) -> dict:
    evs = get_events(since=since, min_confidence=min_confidence)["events"]
    if not include_contradictions:
        evs = [e for e in evs if e.get("type") != "contradiction_flagged"]
    uni = store.read_universe() or {}
    return {"status": "ok", "events": evs,
            "universe_entries": uni.get("entries", []), "universe_exits": uni.get("exits", [])}


def search(query: str) -> dict:
    q = query.lower()
    hits = []
    for c in store.read_all_companies():
        hay = " ".join([c.name, c.category or "", c.subcategory or "", c.specialty or "",
                        c.segment or "", *(c.aliases or []), *c.metrics.keys()]).lower()
        if any(tok in hay for tok in q.split()):
            hits.append({"id": c.id, "name": c.name, "category": c.category,
                         "subcategory": c.subcategory})
    return {"status": "ok", "query": query, "results": hits}
