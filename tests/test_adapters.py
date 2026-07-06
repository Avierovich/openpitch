"""Tests for source-adapter parsers (pure, no network)."""

from __future__ import annotations

import feedparser

from openpitch.models import Company
from openpitch.pipeline.sources import edgar, news, podcast_rss
from openpitch.pipeline.sources.base import mentions, parse_date
from openpitch.pipeline.sources.company_site import careers_candidates, extract_text

ACME = Company(id="acme", name="Acme AI", aliases=["Acme"], website="acme.ai", last_updated="2026-06-13")


# ── base helpers ─────────────────────────────────────────────────────────────


def test_mentions_matches_name_and_alias():
    assert mentions(ACME, "Acme AI raises Series B")
    assert mentions(ACME, "interview with Acme founder")
    assert not mentions(ACME, "totally unrelated company")


def test_parse_date_formats():
    assert parse_date("2026-06-13").isoformat() == "2026-06-13"
    assert parse_date("Mon, 09 Jun 2026 12:00:00 +0000").isoformat() == "2026-06-09"
    assert parse_date("garbage") is None


# ── EDGAR ────────────────────────────────────────────────────────────────────


def test_edgar_parse_hits():
    payload = {
        "hits": {
            "hits": [
                {
                    "_id": "0000950170-26-000123:primary_doc.xml",
                    "_source": {
                        "display_names": ["Acme AI Inc. (CIK 0001999999)"],
                        "file_date": "2026-05-20",
                        "root_form": "D",
                    },
                }
            ]
        }
    }
    items = edgar.parse_hits(payload, "acme")
    assert len(items) == 1
    it = items[0]
    assert it.source_type.value == "filing"
    assert it.published_at.isoformat() == "2026-05-20"
    assert it.locator == "0000950170-26-000123"
    assert it.content_hash  # finalized


def test_edgar_empty():
    assert edgar.parse_hits({}, "acme") == []


def test_edgar_headers_use_env_user_agent(monkeypatch):
    monkeypatch.setenv("OPENPITCH_SEC_USER_AGENT", "OpenPitch/0.1 test@example.com")
    headers = edgar.sec_headers()
    assert headers["User-Agent"] == "OpenPitch/0.1 test@example.com"
    assert headers["Accept-Encoding"] == "gzip, deflate"


def test_edgar_fetch_sends_sec_headers(monkeypatch):
    monkeypatch.setenv("OPENPITCH_SEC_USER_AGENT", "OpenPitch/0.1 test@example.com")
    calls = []

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"hits": {"hits": []}}

    class FakeClient:
        def get(self, url, *, params=None, headers=None):
            calls.append({"url": url, "params": params, "headers": headers})
            return FakeResponse()

    assert edgar.fetch(ACME, client=FakeClient()) == []
    assert calls[0]["url"] == edgar.EFTS_URL
    assert calls[0]["params"] == {"q": '"Acme AI"', "forms": "D"}
    assert calls[0]["headers"]["User-Agent"] == "OpenPitch/0.1 test@example.com"


# ── News ─────────────────────────────────────────────────────────────────────


def test_news_query_url_quotes_name():
    url = news.build_query_url("Acme AI")
    assert "Acme" in url and "news.google.com" in url


def test_news_parse_feed():
    rss = """<?xml version="1.0"?>
    <rss version="2.0"><channel>
      <item>
        <title>Acme AI raises $200M Series B</title>
        <link>https://example.com/a</link>
        <description>The AI startup hit $50M ARR.</description>
        <pubDate>Mon, 09 Jun 2026 12:00:00 +0000</pubDate>
      </item>
    </channel></rss>"""
    parsed = feedparser.parse(rss)
    items = news.parse_feed(parsed, "acme")
    assert len(items) == 1
    assert items[0].source_type.value == "news"
    assert items[0].published_at.isoformat() == "2026-06-09"
    assert "Series B" in items[0].text


# ── Podcast ──────────────────────────────────────────────────────────────────


def test_podcast_only_matching_episodes_flagged_for_transcription():
    rss = """<?xml version="1.0"?>
    <rss version="2.0"><channel>
      <item>
        <title>Deep dive with Acme AI's founder</title>
        <link>https://pod.example/ep1</link>
        <description>We discuss growth and ARR.</description>
        <pubDate>Mon, 09 Jun 2026 12:00:00 +0000</pubDate>
        <enclosure url="https://pod.example/ep1.mp3" type="audio/mpeg"/>
      </item>
      <item>
        <title>An unrelated episode</title>
        <link>https://pod.example/ep2</link>
        <description>Nothing to see here.</description>
      </item>
    </channel></rss>"""
    parsed = feedparser.parse(rss)
    items = podcast_rss.episodes_mentioning(parsed, ACME, "20VC")
    assert len(items) == 1
    assert items[0].needs_transcription is True
    assert items[0].audio_url == "https://pod.example/ep1.mp3"


def test_podcast_load_feeds_skips_blank_urls(tmp_path):
    cfg = tmp_path / "podcasts.yaml"
    cfg.write_text("feeds:\n  - {name: A, feed_url: ''}\n  - {name: B, feed_url: 'http://x/rss'}\n")
    feeds = podcast_rss.load_feeds(cfg)
    assert [f["name"] for f in feeds] == ["B"]


# ── Company site ─────────────────────────────────────────────────────────────


def test_company_site_helpers():
    cands = careers_candidates("acme.ai")
    assert "https://acme.ai/careers" in cands
    assert extract_text("<h1>We are <b>hiring</b></h1>") == "We are hiring"


# ── news signal ranking (the anti-headline-lottery, Sierra failure) ──────────

SIERRA = Company(id="sierra", name="Sierra", website="sierra.ai", last_updated="2026-07-03")


def test_news_entity_mismatch_cases():
    # demote: name is part of a larger proper-noun entity (a different company/place)
    assert news.entity_mismatch("Sierra Space wins NASA contract", "Sierra")
    assert news.entity_mismatch("Sierra Space Raises $290M At $5.3B Valuation", "Sierra")
    assert news.entity_mismatch("American Sierra Gold Corp. Announces results", "Sierra")
    assert news.entity_mismatch("Sierra Nevada Ballet's summer series begins", "Sierra")
    assert news.entity_mismatch("Sierra Leone receives $50M in IMF funding", "Sierra")
    # keep: the name stands alone (allowlist, connectors incl. Title Case, possessive,
    # punctuation, end-of-string, lowercase verb)
    assert not news.entity_mismatch("Sierra AI hits $100M ARR", "Sierra")
    assert not news.entity_mismatch("Sierra raises $350M at a $10B valuation", "Sierra")
    assert not news.entity_mismatch("Sierra Raises $350M At $10B Valuation", "Sierra")
    assert not news.entity_mismatch("Bret Taylor's Sierra valued at $10B", "Sierra")
    assert not news.entity_mismatch("Sierra's valuation doubles", "Sierra")
    assert not news.entity_mismatch("Sierra, the AI agent startup, expands", "Sierra")
    # one standalone occurrence rescues a text that also has a compound one
    assert not news.entity_mismatch("Unlike Sierra Space, Sierra is an AI startup", "Sierra")
    # aliases extend the allowlist
    assert not news.entity_mismatch("Anysphere Cursor hits $500M ARR", "Anysphere", ["Cursor"])


def _feed_xml(titles: list[str]) -> str:
    items = "".join(
        f"<item><title>{t}</title><link>https://example.com/{i}</link></item>"
        for i, t in enumerate(titles)
    )
    return f'<?xml version="1.0"?><rss version="2.0"><channel>{items}</channel></rss>'


def test_news_signal_rank_promotes_valuation_headline():
    # 17 generic raise-echoes ahead of the ONE headline stating the valuation —
    # recency order would drop it at limit=15; ranking must surface it first.
    titles = [f"Sierra raises $950M round, say sources ({i})" for i in range(17)]
    titles.append("Sierra hits $15.8B valuation in latest round")
    parsed = feedparser.parse(_feed_xml(titles))
    items = news.parse_feed(parsed, "sierra")
    ranked = news.rank_items(items, SIERRA)
    assert "15.8B valuation" in ranked[0].title
    assert any("15.8B valuation" in (it.title or "") for it in ranked[:15])


def test_news_rank_demotes_compound_entities():
    parsed = feedparser.parse(_feed_xml([
        "Sierra Space raises $290M at $5.3B valuation",
        "Sierra raises $350M at a $10B valuation",
    ]))
    items = news.parse_feed(parsed, "sierra")
    ranked = news.rank_items(items, SIERRA)
    assert ranked[0].title.startswith("Sierra raises")


def test_news_text_drops_google_stub_summary():
    # Google News summaries are anchor-tag stubs echoing the title — text collapses
    # to title-only; a REAL description (extra facts) is still appended.
    rss = """<?xml version="1.0"?><rss version="2.0"><channel>
      <item><title>Sierra raises $950M</title>
        <description>&lt;a href="https://news.google.com/x"&gt;Sierra raises $950M&lt;/a&gt;</description>
        <link>https://news.google.com/a</link></item>
    </channel></rss>"""
    it = news.parse_feed(feedparser.parse(rss), "sierra")[0]
    assert it.text == "Sierra raises $950M"


def test_company_site_extract_text_strips_script_and_style():
    html = ('<html><head><style>.x{color:red}</style>'
            '<script>var junk = "slick theme css";</script></head>'
            '<body><p>Sierra was valued at $4.5 billion.</p></body></html>')
    text = extract_text(html)
    assert "valued at $4.5 billion" in text
    assert "junk" not in text and "color:red" not in text


# ── article source (gap-fill, Bing-based) ────────────────────────────────────


def test_article_publisher_url_unwraps_apiclick():
    from openpitch.pipeline.sources import article
    wrapped = ("http://www.bing.com/news/apiclick.aspx?ref=FexRss&aid="
               "&url=https%3a%2f%2ftechcrunch.com%2fsierra-raise&cc=us")
    assert article.publisher_url(wrapped) == "https://techcrunch.com/sierra-raise"
    assert article.publisher_url("https://techcrunch.com/direct") == "https://techcrunch.com/direct"
    assert article.publisher_url("http://www.bing.com/news/apiclick.aspx?ref=x") is None
    assert article.publisher_url(None) is None


def test_article_parse_feed_filters_mismatch_and_hashes_url_title():
    import hashlib
    from openpitch.pipeline.sources import article
    rss = """<?xml version="1.0"?><rss version="2.0"><channel>
      <item><title>Sierra hits $15.8B valuation</title>
        <link>http://www.bing.com/news/apiclick.aspx?url=https%3a%2f%2ftc.com%2fa</link>
        <description>Bret Taylor's AI startup...</description></item>
      <item><title>Sierra Space wins NASA contract</title>
        <link>http://www.bing.com/news/apiclick.aspx?url=https%3a%2f%2fsn.com%2fb</link></item>
    </channel></rss>"""
    items = article.parse_feed(feedparser.parse(rss), SIERRA)
    assert len(items) == 1 and items[0].url == "https://tc.com/a"
    expected = hashlib.sha256("https://tc.com/a|Sierra hits $15.8B valuation".encode()).hexdigest()[:16]
    assert items[0].content_hash == expected
    # hash is url|title — body churn must NOT change it (cache stability)
    items[0].text = "totally different body"
    assert items[0].finalize().content_hash == expected
