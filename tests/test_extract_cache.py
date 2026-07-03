"""Extraction cache: unchanged items are reused (no re-extraction), claims preserved."""

from __future__ import annotations

from datetime import date, datetime

from openpitch.models import Claim, Source, SourceType, Speaker, SpeakerRole
from openpitch.pipeline import extract_cache
from openpitch.pipeline.sources.base import RawItem


def _item(url, text):
    return RawItem(company_id="acme", source_type=SourceType.NEWS, source_name="TC",
                   title="t", text=text, url=url).finalize()


def _claim(url, value):
    return Claim(id=f"c{value}", company_id="acme", metric="arr", value=value, raw_text="x",
                 speaker=Speaker(role=SpeakerRole.JOURNALIST),
                 source=Source(type=SourceType.NEWS, name="TC", url=url, published_at=date(2026, 6, 1)),
                 extracted_at=datetime(2026, 6, 1), extractor_model="t", base_confidence=0.5)


def test_first_run_extracts_all_then_second_reuses():
    a, b = _item("https://a", "alpha"), _item("https://b", "beta")
    cache = {}

    # first run: nothing cached -> both need extraction
    reused, to_extract = extract_cache.split([a, b], "acme", cache)
    assert reused == [] and len(to_extract) == 2

    # a yields a claim, b yields nothing
    extract_cache.record(cache, "acme", to_extract, [_claim("https://a", 100)])
    assert len(cache) == 2                       # both items marked seen (b cached as [])

    # second run: both reused, no LLM needed, the claim is carried forward
    reused2, to_extract2 = extract_cache.split([a, b], "acme", cache)
    assert to_extract2 == []
    assert [c.value for c in reused2] == [100]


def test_changed_content_is_re_extracted():
    cache = {}
    old = _item("https://a", "old text")
    extract_cache.record(cache, "acme", [old], [])
    # same url, new text -> different content_hash -> not a cache hit
    new = _item("https://a", "NEW text")
    reused, to_extract = extract_cache.split([new], "acme", cache)
    assert reused == [] and to_extract == [new]


def test_cache_is_keyed_by_company():
    cache = {}
    it = _item("https://a", "shared article")
    extract_cache.record(cache, "acme", [it], [_claim("https://a", 100)])
    # a different company fetching the same article must NOT reuse acme's claims
    reused, to_extract = extract_cache.split([it], "beta", cache)
    assert reused == [] and to_extract == [it]


def test_urlless_items_are_not_cached_as_seen():
    # Claims match back to items by URL; a url-less item can't prove its claims were
    # captured, so it must re-extract next run instead of being cached as empty.
    cache = {}
    it = _item(None, "podcast transcript with no url")
    extract_cache.record(cache, "acme", [it], [_claim(None, 100)])
    reused, to_extract = extract_cache.split([it], "acme", cache)
    assert reused == [] and to_extract == [it]
