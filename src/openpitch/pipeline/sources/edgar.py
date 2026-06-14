"""SEC EDGAR adapter — Form D private-placement filings (FRD §7).

Form D is filed when a company raises in an exempt private offering, so it's a
high-trust, official signal for funding rounds. Uses EDGAR full-text search
(free, official). SEC requires a descriptive User-Agent.

I/O (`fetch`) is thin; `parse_hits` is pure and unit-tested.
"""

from __future__ import annotations

import os

from .base import RawItem, parse_date
from ...models import Company, SourceType
from ...paths import load_dotenv

EFTS_URL = "https://efts.sec.gov/LATEST/search-index"
DEFAULT_USER_AGENT = "OpenPitch/0.1 (open-source AI-startup intelligence; contact via GitHub issues)"


def sec_headers() -> dict[str, str]:
    """Headers for SEC fair-access requests.

    SEC asks automated clients to identify the caller with app/org + contact.
    Set OPENPITCH_SEC_USER_AGENT in .env for production runs.
    """
    load_dotenv()
    user_agent = os.environ.get("OPENPITCH_SEC_USER_AGENT", DEFAULT_USER_AGENT).strip()
    return {
        "User-Agent": user_agent or DEFAULT_USER_AGENT,
        "Accept-Encoding": "gzip, deflate",
        "Accept": "application/json, text/plain, */*",
    }


def parse_hits(payload: dict, company_id: str) -> list[RawItem]:
    """Pure: turn an EDGAR full-text-search JSON response into RawItems."""
    items: list[RawItem] = []
    for hit in payload.get("hits", {}).get("hits", []):
        src = hit.get("_source", {})
        names = src.get("display_names") or []
        filed = parse_date(src.get("file_date"))
        form = src.get("root_form") or src.get("file_type") or "D"
        accession = (hit.get("_id") or "").split(":")[0]
        title = f"Form {form} filing" + (f" — {names[0]}" if names else "")
        url = (
            f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&filenum={accession}"
            if accession
            else "https://efts.sec.gov/LATEST/search-index"
        )
        items.append(
            RawItem(
                company_id=company_id,
                source_type=SourceType.FILING,
                source_name="SEC EDGAR",
                title=title,
                text=f"{title}. Filer(s): {', '.join(names)}.",
                url=url,
                locator=accession or None,
                published_at=filed,
            ).finalize()
        )
    return items


def fetch(company: Company, *, client=None, lookback_days: int = 400) -> list[RawItem]:
    """Query EDGAR for the company's recent Form D filings."""
    import httpx

    params = {"q": f'"{company.name}"', "forms": "D"}
    owns_client = client is None
    client = client or httpx.Client(timeout=20.0)
    try:
        resp = client.get(EFTS_URL, params=params, headers=sec_headers())
        resp.raise_for_status()
        return parse_hits(resp.json(), company.id)
    finally:
        if owns_client:
            client.close()
