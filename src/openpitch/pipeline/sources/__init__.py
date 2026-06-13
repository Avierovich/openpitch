"""Source adapters (FRD §7, stage 2).

Each adapter implements one interface so adding a source = one file:

    class SourceAdapter(Protocol):
        name: str
        def fetch(self, company: Company) -> list[RawItem]: ...

v1 adapters (to implement): podcast_rss, news, edgar, company_site.
Adapters MUST respect robots.txt / ToS and prefer official APIs and
already-published transcripts (BRD NFR-02).
"""
