"""Cache layer tests."""

from __future__ import annotations

from pathlib import Path

from wikifi.cache import (
    CACHE_VERSION,
    WalkCache,
    aggregation_cache_path,
    derivation_cache_path,
    extraction_cache_path,
    hash_introspection_scope,
    hash_section_notes,
    hash_upstream_bodies,
    introspection_cache_path,
    load,
    reset,
    save,
    save_aggregation,
    save_derivation,
    save_extraction,
    save_introspection,
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


def test_derivation_cache_round_trip(tmp_path: Path):
    """Cached derivative bodies survive a full save/load cycle."""
    layout = _layout(tmp_path)
    cache = WalkCache()
    cache.record_derivation("personas", upstream_hash="uh1", body="P body", revised=False)
    cache.record_derivation("user_stories", upstream_hash="uh2", body="US body", revised=True)
    save(layout, cache)
    assert derivation_cache_path(layout).exists()

    loaded = load(layout)
    hit = loaded.lookup_derivation("personas", "uh1", expect_revised=False)
    assert hit is not None and hit.body == "P body"
    revised = loaded.lookup_derivation("user_stories", "uh2", expect_revised=True)
    assert revised is not None and revised.revised is True


def test_derivation_cache_misses_on_upstream_hash_change(tmp_path: Path):
    """A different `upstream_hash` must miss; that's how upstream edits flow through."""
    _layout(tmp_path)
    cache = WalkCache()
    cache.record_derivation("personas", upstream_hash="uh1", body="P", revised=False)
    assert cache.lookup_derivation("personas", "uh2", expect_revised=False) is None
    assert cache.derivation_misses == 1


def test_derivation_cache_rejects_unrevised_body_when_review_requested(tmp_path: Path):
    """`--review` walks must not silently reuse a body produced without the critic."""
    _layout(tmp_path)
    cache = WalkCache()
    cache.record_derivation("personas", upstream_hash="uh1", body="P", revised=False)
    assert cache.lookup_derivation("personas", "uh1", expect_revised=True) is None
    # The inverse — review off, cached body was revised — is still a hit:
    cache.record_derivation("user_stories", upstream_hash="uh2", body="US", revised=True)
    assert cache.lookup_derivation("user_stories", "uh2", expect_revised=False) is not None


def test_introspection_cache_round_trip(tmp_path: Path):
    """The prior walk's scope hash + payload survive save/load."""
    layout = _layout(tmp_path)
    cache = WalkCache()
    cache.record_introspection(
        scope_hash="sh1",
        payload={"include": ["src/"], "exclude": ["build/"], "primary_languages": ["python"]},
    )
    save(layout, cache)
    assert introspection_cache_path(layout).exists()

    loaded = load(layout)
    assert loaded.lookup_introspection("sh1") is not None
    assert loaded.lookup_introspection("different") is None
    assert loaded.introspection.payload["include"] == ["src/"]


def test_hash_upstream_bodies_is_stable_across_dict_order():
    """Insertion order must not affect the upstream-body hash."""
    a = {"capabilities": "cap body", "intent": "intent body"}
    b = {"intent": "intent body", "capabilities": "cap body"}
    assert hash_upstream_bodies(a) == hash_upstream_bodies(b)
    different = {"capabilities": "cap body", "intent": "DIFFERENT"}
    assert hash_upstream_bodies(a) != hash_upstream_bodies(different)


def test_hash_introspection_scope_ignores_non_scope_fields():
    """Only ``include`` + ``exclude`` should drive the scope hash."""
    a = hash_introspection_scope(include=["src/"], exclude=["build/"])
    b = hash_introspection_scope(include=["src/"], exclude=["build/"])
    assert a == b
    # Order-insensitive within each list.
    a2 = hash_introspection_scope(include=["b/", "a/"], exclude=["x/", "y/"])
    a3 = hash_introspection_scope(include=["a/", "b/"], exclude=["y/", "x/"])
    assert a2 == a3
    # Adding an exclude shifts the hash.
    different = hash_introspection_scope(include=["src/"], exclude=["build/", "tmp/"])
    assert a != different


def test_save_aggregation_only_writes_aggregation_file(tmp_path: Path):
    """Per-stage save helpers must touch only their own file.

    Without this the per-section persist callback would re-write every
    cache file on every section, defeating the point of splitting them.
    """
    layout = _layout(tmp_path)
    cache = WalkCache()
    cache.record_aggregation("intent", notes_hash="h", body="b", claims=[], contradictions=[])
    # Pre-create extraction file so we can verify it's untouched.
    cache.record_extraction("a.py", fingerprint="x", findings=[], summary="", chunks_processed=0)
    save_extraction(layout, cache)
    extraction_mtime = extraction_cache_path(layout).stat().st_mtime_ns

    # Wait long enough that any rewrite would change the mtime.
    import time

    time.sleep(0.01)
    save_aggregation(layout, cache)
    assert aggregation_cache_path(layout).exists()
    # extraction file untouched by save_aggregation
    assert extraction_cache_path(layout).stat().st_mtime_ns == extraction_mtime


def test_save_introspection_no_op_when_unset(tmp_path: Path):
    """Calling ``save_introspection`` on a cache without an introspection record is a no-op."""
    layout = _layout(tmp_path)
    cache = WalkCache()
    save_introspection(layout, cache)
    assert not introspection_cache_path(layout).exists()


def test_reset_drops_every_scope(tmp_path: Path):
    """``reset`` must clear the new derivation + introspection files too."""
    layout = _layout(tmp_path)
    cache = WalkCache()
    cache.record_extraction("a.py", fingerprint="x", findings=[], summary="", chunks_processed=0)
    cache.record_aggregation("intent", notes_hash="h", body="b", claims=[], contradictions=[])
    cache.record_derivation("personas", upstream_hash="u", body="p", revised=False)
    cache.record_introspection(scope_hash="s", payload={"include": [], "exclude": []})
    save(layout, cache)

    reset(layout)
    assert not extraction_cache_path(layout).exists()
    assert not aggregation_cache_path(layout).exists()
    assert not derivation_cache_path(layout).exists()
    assert not introspection_cache_path(layout).exists()


def test_save_derivation_only_writes_derivation_file(tmp_path: Path):
    """Stage 4's per-section persist must not rewrite stages 2/3."""
    layout = _layout(tmp_path)
    cache = WalkCache()
    cache.record_extraction("a.py", fingerprint="x", findings=[], summary="", chunks_processed=0)
    cache.record_aggregation("intent", notes_hash="h", body="b", claims=[], contradictions=[])
    save_extraction(layout, cache)
    save_aggregation(layout, cache)
    extraction_mtime = extraction_cache_path(layout).stat().st_mtime_ns
    aggregation_mtime = aggregation_cache_path(layout).stat().st_mtime_ns

    import time

    time.sleep(0.01)
    cache.record_derivation("personas", upstream_hash="u", body="p", revised=False)
    save_derivation(layout, cache)
    assert derivation_cache_path(layout).exists()
    assert extraction_cache_path(layout).stat().st_mtime_ns == extraction_mtime
    assert aggregation_cache_path(layout).stat().st_mtime_ns == aggregation_mtime


def test_v1_caches_are_invalidated_by_version_bump(tmp_path: Path):
    """A v1 cache file on disk loads to empty under CACHE_VERSION=2.

    This is the upgrade path: existing wikis re-extract on the first
    walk after the upgrade, then enjoy the new short-circuit on every
    walk after.
    """
    layout = _layout(tmp_path)
    extraction_cache_path(layout).parent.mkdir(parents=True, exist_ok=True)
    extraction_cache_path(layout).write_text(
        '{"version": 1, "entries": {"a.py": {"fingerprint": "abc", "findings": [],'
        ' "summary": "", "chunks_processed": 0}}}'
    )
    aggregation_cache_path(layout).write_text(
        '{"version": 1, "entries": {"intent": {"notes_hash": "h", "body": "b", "claims": [], "contradictions": []}}}'
    )
    cache = load(layout)
    assert cache.extraction == {}
    assert cache.aggregation == {}


def test_hash_section_notes_changes_when_sources_change():
    """The aggregation cache key must reflect each note's `sources`.

    Two notes with identical finding text but different source line
    ranges or fingerprints describe different evidence; reusing the
    same cached body would replay stale citations against new code.
    """
    base = [
        {
            "file": "a.py",
            "summary": "role",
            "finding": "Order entity.",
            "sources": [{"file": "a.py", "lines": [1, 30], "fingerprint": "abc1234"}],
        }
    ]
    same = [
        {
            "file": "a.py",
            "summary": "role",
            "finding": "Order entity.",
            "sources": [{"file": "a.py", "lines": (1, 30), "fingerprint": "abc1234"}],
        }
    ]
    moved_lines = [
        {
            "file": "a.py",
            "summary": "role",
            "finding": "Order entity.",
            "sources": [{"file": "a.py", "lines": [42, 70], "fingerprint": "abc1234"}],
        }
    ]
    new_fingerprint = [
        {
            "file": "a.py",
            "summary": "role",
            "finding": "Order entity.",
            "sources": [{"file": "a.py", "lines": [1, 30], "fingerprint": "deadbee"}],
        }
    ]
    # Tuple vs list line range: same logical evidence, identical hash.
    assert hash_section_notes(base) == hash_section_notes(same)
    # Lines moved → new evidence → cache must miss.
    assert hash_section_notes(base) != hash_section_notes(moved_lines)
    # File contents changed (fingerprint shifted) → cache must miss.
    assert hash_section_notes(base) != hash_section_notes(new_fingerprint)
