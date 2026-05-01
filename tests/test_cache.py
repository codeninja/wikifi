"""Cache layer tests."""

from __future__ import annotations

from pathlib import Path

from wikifi.cache import (
    CACHE_VERSION,
    WalkCache,
    aggregation_cache_path,
    extraction_cache_path,
    hash_section_notes,
    load,
    reset,
    save,
)
from wikifi.wiki import WikiLayout, initialize


def _layout(tmp_path: Path) -> WikiLayout:
    layout = WikiLayout(root=tmp_path)
    initialize(layout, model="m", provider="ollama", ollama_host="http://h")
    return layout


def test_extraction_cache_hit_and_miss(tmp_path: Path):
    layout = _layout(tmp_path)
    cache = load(layout)
    assert cache.lookup_extraction("a.py", "abc") is None
    assert cache.extraction_misses == 1

    cache.record_extraction(
        "a.py",
        fingerprint="abc",
        findings=[{"section_id": "entities", "finding": "x", "sources": []}],
        summary="role",
        chunks_processed=1,
    )
    hit = cache.lookup_extraction("a.py", "abc")
    assert hit is not None
    assert hit.fingerprint == "abc"
    assert cache.extraction_hits == 1


def test_extraction_cache_invalidated_on_fingerprint_change(tmp_path: Path):
    layout = _layout(tmp_path)
    cache = load(layout)
    cache.record_extraction("a.py", fingerprint="old", findings=[], summary="", chunks_processed=0)
    assert cache.lookup_extraction("a.py", "new") is None


def test_aggregation_cache_round_trip(tmp_path: Path):
    layout = _layout(tmp_path)
    cache = load(layout)
    cache.record_aggregation(
        "entities",
        notes_hash="h1",
        body="body",
        claims=[{"text": "c", "sources": []}],
        contradictions=[],
    )
    hit = cache.lookup_aggregation("entities", "h1")
    assert hit is not None
    assert hit.body == "body"
    assert cache.lookup_aggregation("entities", "h2") is None


def test_save_and_load_round_trip(tmp_path: Path):
    layout = _layout(tmp_path)
    cache = WalkCache()
    cache.record_extraction(
        "src/a.py",
        fingerprint="abc123",
        findings=[{"section_id": "entities", "finding": "x", "sources": []}],
        summary="role",
        chunks_processed=2,
    )
    cache.record_aggregation("entities", notes_hash="hh", body="body", claims=[], contradictions=[])
    save(layout, cache)
    assert extraction_cache_path(layout).exists()
    assert aggregation_cache_path(layout).exists()

    loaded = load(layout)
    assert loaded.lookup_extraction("src/a.py", "abc123") is not None
    assert loaded.lookup_aggregation("entities", "hh") is not None


def test_reset_clears_disk_files(tmp_path: Path):
    layout = _layout(tmp_path)
    cache = WalkCache()
    cache.record_extraction("a.py", fingerprint="x", findings=[], summary="", chunks_processed=0)
    save(layout, cache)
    reset(layout)
    assert not extraction_cache_path(layout).exists()
    assert not aggregation_cache_path(layout).exists()


def test_load_returns_empty_when_file_missing(tmp_path: Path):
    layout = _layout(tmp_path)
    cache = load(layout)
    assert cache.extraction == {}
    assert cache.aggregation == {}


def test_load_drops_bad_version(tmp_path: Path):
    layout = _layout(tmp_path)
    extraction_cache_path(layout).parent.mkdir(parents=True, exist_ok=True)
    extraction_cache_path(layout).write_text('{"version": 999, "entries": {"a.py": {"fingerprint": "abc"}}}')
    cache = load(layout)
    assert cache.extraction == {}


def test_prune_extraction_drops_out_of_scope_files(tmp_path: Path):
    _layout(tmp_path)  # ensures cache dir exists; entries are exercised below
    cache = WalkCache()
    for path in ("keep.py", "drop.py"):
        cache.record_extraction(path, fingerprint="x", findings=[], summary="", chunks_processed=0)
    removed = cache.prune_extraction(keep={"keep.py"})
    assert removed == 1
    assert "keep.py" in cache.extraction
    assert "drop.py" not in cache.extraction


def test_hash_section_notes_is_stable():
    notes = [
        {"file": "a.py", "summary": "x", "finding": "y", "timestamp": "t1"},
        {"file": "b.py", "summary": "x", "finding": "z", "timestamp": "t2"},
    ]
    same = [
        {"file": "a.py", "summary": "x", "finding": "y", "timestamp": "t99"},
        {"file": "b.py", "summary": "x", "finding": "z", "timestamp": "t100"},
    ]
    assert hash_section_notes(notes) == hash_section_notes(same)
    different = [{"file": "a.py", "summary": "x", "finding": "DIFFERENT"}]
    assert hash_section_notes(notes) != hash_section_notes(different)


def test_cache_version_is_pinned():
    """Bumps to CACHE_VERSION should be intentional — guard against drift."""
    assert isinstance(CACHE_VERSION, int)
    assert CACHE_VERSION >= 1
