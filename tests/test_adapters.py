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
