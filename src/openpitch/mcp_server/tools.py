"""MCP tool logic (MCP-SPEC) — pure functions over the committed data.

Separated from the MCP wiring (server.py) so it's unit-testable without the SDK.
Read-only; makes ZERO LLM calls; never strips provenance; explicit no-data.
"""

from __future__ import annotations

from .. import serving_gate as gate
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


def _verdicts(company) -> dict:
    """Serving-gate verdicts for one company (empty when the gate is off, so no claims
    read). Never raises: one unreadable claims file must not fail a multi-company tool.
    A withheld figure never reaches a `value` key; see serving_gate.py."""
    return gate.guarded(company, store.read_claims)


def _gate_metric(dump: dict, v) -> dict:
    return gate.apply(dump, v) if v else dump


def _headline(company, verdicts: dict | None = None) -> dict:
    verdicts = verdicts or {}
    out = {}
    for k in ("valuation", "arr"):
        rv = company.metrics.get(k)
        if not rv:
            continue
        v = verdicts.get(k)
        if v and v.action == gate.WITHHOLD:
            out[k] = gate.cell(v, rv)
        else:
            out[k] = _gate_metric({"value": rv.value, "unit": rv.unit, "confidence": rv.confidence}, v)
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
    # Gate after the slice: claims are read only for the companies actually returned
    # (each read is a remote fetch on no-clone installs).
    return {
        "status": "ok",
        "companies": [
            {
                "id": c.id, "name": c.name, "category": c.category,
                "subcategory": c.subcategory, "specialty": c.specialty, "summary": c.summary,
                "segment": c.segment,
                "universe_rank": c.universe_rank, "vc_attention_score": c.vc_attention_score,
                "last_updated": str(c.last_updated), "headline_metrics": _headline(c, _verdicts(c)),
            }
            for c in comps[:limit]
        ],
    }


def get_company(id: str, include_sources: bool = True) -> dict:
    c = store.read_company(id)
    if not c:
        return _not_found(id)
    out = {"status": "ok", "company": c.model_dump(mode="json")}
    for m, v in _verdicts(c).items():
        out["company"]["metrics"][m] = gate.apply(out["company"]["metrics"][m], v)
    if include_sources:
        out["sources"] = {m: _sources_for(id, m) for m in c.metrics}
    return out


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
    v = _verdicts(c).get(metric)
    resp = {"status": "ok", "company_id": company_id,
            "metric": _gate_metric(rv.model_dump(mode="json"), v),
            "sources": _sources_for(company_id, metric)}
    if v and v.action == gate.WITHHOLD:
        resp["status"] = "withheld"
        resp["message"] = ("This figure failed a plausibility check and is withheld. You may "
                           "say a figure exists and why it was withheld, but do not state it "
                           f"as fact. Reason: {v.reason}")
        resp["next"] = f"get_provenance('{company_id}', '{metric}')"
    if with_history:
        hist = store.read_history(company_id, metric)
        resp["history"] = gate.mask_history(hist) if resp["status"] == "withheld" else hist
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
    resp = {"status": "ok", "company_id": company_id, "metric": metric,
            "claims": claims_out, "contradiction": c.metrics[metric].contradiction,
            "methodology_url": "docs/METHODOLOGY.md"}
    # The audit path stays complete: raw claims are returned even for a withheld figure,
    # with the verdict (including its numeric detail) attached. A withhold that names no
    # specific claim (a floor, a bound, a cross-metric conflict) flags every claim behind
    # the served figure, since any of them could be the one that is wrong.
    v = _verdicts(c).get(metric)
    if v:
        resp["gate"] = v.as_dict(detail=True)
        flag = set(v.evidence) or (set(c.metrics[metric].supporting_claims)
                                   if v.action == gate.WITHHOLD else set())
        for co in claims_out:
            if co["id"] in flag:
                co["gate_flag"] = v.rule
    return resp


def compare_companies(ids: list[str], metrics: list[str]) -> dict:
    rows = []
    for cid in ids:
        c = store.read_company(cid)
        if not c:
            rows.append({"company_id": cid, "status": "not_found"})
            continue
        cells = {}
        verdicts = _verdicts(c)
        for m in metrics:
            rv = c.metrics.get(m)
            v = verdicts.get(m)
            if not rv:
                cells[m] = None                      # None means no data, never "withheld"
            elif v and v.action == gate.WITHHOLD:
                cells[m] = gate.cell(v, rv)
            else:
                cells[m] = _gate_metric({"value": rv.value, "unit": rv.unit, "confidence": rv.confidence,
                                         "as_of": str(rv.as_of), "estimate_type": rv.estimate_type.value,
                                         "contradiction": rv.contradiction}, v)
        rows.append({"company_id": cid, "name": c.name, "metrics": cells})
    return {"status": "ok", "comparison": rows}


def _slim_event(e: dict) -> dict:
    """Compact an event for the stream tools: keep the delta + outlet names, drop the
    heavy per-source URL blobs (Google News redirects dominate the payload). Full source
    URLs are one `get_provenance` call away on any specific company/metric."""
    slim = {k: v for k, v in e.items() if k not in ("sources", "schema_version")}
    slim["sources"] = [s.get("name") for s in (e.get("sources") or []) if s.get("name")]
    return slim


def _gate_events(evs: list[dict]) -> list[dict]:
    """Mask events about currently withheld figures (payload numbers and the summary,
    which embeds them). Runs on the capped slice, so at most `limit` companies are read.
    Conservative: every event for a withheld company/metric is masked, including older
    ones, because the feed cannot tell which past value was the wrong one."""
    if not gate.enabled():
        return evs
    cache: dict[str, dict] = {}
    out = []
    for e in evs:
        cid, metric = e.get("company_id"), (e.get("payload") or {}).get("metric")
        if cid and metric:
            if cid not in cache:
                try:
                    cache[cid] = _verdicts(store.read_company(cid))
                except Exception:  # noqa: BLE001 — an unreadable company leaves its events as-is
                    cache[cid] = {}
            v = gate.withheld(cache[cid], metric)
            if v:
                e = gate.mask_event(e, v)
        out.append(e)
    return out


def _cap(rows: list, limit: int) -> tuple[list, int, bool]:
    """Newest-first slice to `limit`; return (rows, total, truncated). The event feed is
    stored oldest-first, so an agent wants the tail — and a named cap beats the client's
    silent truncation when the full feed overflows the tool-result limit."""
    total = len(rows)
    return rows[: max(0, limit)], total, total > max(0, limit)


def get_events(since: str | None = None, type: str | None = None,
               company_id: str | None = None, min_confidence: float = 0.0,
               limit: int = 50) -> dict:
    evs = store.read_events(since=since)
    if type:
        evs = [e for e in evs if e.get("type") == type]
    if company_id:
        evs = [e for e in evs if e.get("company_id") == company_id]
    evs = [e for e in evs if (e.get("confidence") or 0) >= min_confidence]
    evs.sort(key=lambda e: str(e.get("detected_at", "")), reverse=True)  # newest first
    evs, total, truncated = _cap(evs, limit)
    return {"status": "ok", "events": [_slim_event(e) for e in _gate_events(evs)],
            "total": total, "truncated": truncated}


def _default_since(days: int = 30) -> str | None:
    """A rolling window anchored to the FRESHEST event date (not a live clock, so the
    payload is deterministic/offline-safe). None if the feed is empty."""
    from datetime import date, timedelta
    dates = [str(e.get("detected_at", ""))[:10] for e in store.read_events()]
    dates = [d for d in dates if d]
    if not dates:
        return None
    return (date.fromisoformat(max(dates)) - timedelta(days=days)).isoformat()


def what_moved(since: str | None = None, min_confidence: float = 0.0,
               include_contradictions: bool = True, limit: int = 50) -> dict:
    # "what moved" means recent: default to a 30-day window so the first call is bounded.
    effective_since = since or _default_since()
    evs = store.read_events(since=effective_since)
    evs = [e for e in evs if (e.get("confidence") or 0) >= min_confidence]
    if not include_contradictions:
        evs = [e for e in evs if e.get("type") != "contradiction_flagged"]
    evs.sort(key=lambda e: str(e.get("detected_at", "")), reverse=True)
    evs, total, truncated = _cap(evs, limit)
    uni = store.read_universe() or {}
    return {"status": "ok", "since": effective_since, "events": [_slim_event(e) for e in _gate_events(evs)],
            "total": total, "truncated": truncated,
            "universe_entries": uni.get("entries", []), "universe_exits": uni.get("exits", [])}


def search(query: str, limit: int = 25) -> dict:
    q = query.lower()
    hits = []
    for c in store.read_all_companies():
        hay = " ".join([c.name, c.category or "", c.subcategory or "", c.specialty or "",
                        c.segment or "", *(c.aliases or []), *c.metrics.keys()]).lower()
        if any(tok in hay for tok in q.split()):
            hits.append({"id": c.id, "name": c.name, "category": c.category,
                         "subcategory": c.subcategory})
    results, total, truncated = _cap(hits, limit)
    return {"status": "ok", "query": query, "results": results,
            "total": total, "truncated": truncated}
