"""Plan B — surgical aggregation tests.

Three surfaces under test:

- ``classify_section_change`` — the diff classifier that routes
  unchanged / surgical / rewrite paths.
- ``surgical_aggregate`` — the LLM-driven surgical edit including
  citation re-anchoring (cached claims minus removed + new claims
  resolved against added findings).
- The aggregator's decision tree that dispatches to those paths and
  records ``finding_ids`` on every cache write.
"""

from __future__ import annotations

from wikifi.aggregator import aggregate_all
from wikifi.cache import (
    CachedSection,
    WalkCache,
    compute_finding_id,
    note_finding_ids,
)
from wikifi.sections import PRIMARY_SECTIONS
from wikifi.surgical import (
    SurgicalClaim,
    SurgicalContradiction,
    SurgicalEdit,
    classify_section_change,
    surgical_aggregate,
)
from wikifi.wiki import WikiLayout, append_note, initialize


def _layout(tmp_path):
    layout = WikiLayout(root=tmp_path)
    initialize(layout, model="m", provider="ollama", ollama_host="http://h")
    return layout


def _note(file: str, finding: str, summary: str = "x") -> dict:
    return {"file": file, "summary": summary, "finding": finding}


# ---------- compute_finding_id / note_finding_ids ----------


def test_compute_finding_id_is_deterministic_and_localized():
    """Same (file, section, finding) → same id; any change → new id."""
    base = compute_finding_id(file="a.py", section_id="entities", finding="Order entity.")
    assert base == compute_finding_id(file="a.py", section_id="entities", finding="Order entity.")
    assert base != compute_finding_id(file="b.py", section_id="entities", finding="Order entity.")
    assert base != compute_finding_id(file="a.py", section_id="capabilities", finding="Order entity.")
    assert base != compute_finding_id(file="a.py", section_id="entities", finding="Order entity reworded.")


def test_note_finding_ids_aligns_with_note_order():
    notes = [_note("a.py", "A1"), _note("b.py", "B1"), _note("a.py", "A2")]
    ids = note_finding_ids(notes, section_id="entities")
    assert len(ids) == 3
    assert ids[0] == compute_finding_id(file="a.py", section_id="entities", finding="A1")
    assert ids[1] == compute_finding_id(file="b.py", section_id="entities", finding="B1")
    assert ids[2] == compute_finding_id(file="a.py", section_id="entities", finding="A2")


# ---------- classify_section_change ----------


def test_classify_no_cache_routes_to_rewrite():
    live_ids = ["id1", "id2"]
    change = classify_section_change(cached=None, live_finding_ids=live_ids, surgical_threshold=0.3)
    assert change.decision == "rewrite"
    assert change.added_indices == [1, 2]
    assert change.removed_ids == []


def test_classify_legacy_v2_cache_with_no_finding_ids_routes_to_rewrite():
    """A cached entry from a pre-v3 cache has empty ``finding_ids`` — must rewrite."""
    cached = CachedSection(notes_hash="h", body="cached", finding_ids=[])
    change = classify_section_change(cached=cached, live_finding_ids=["id1"], surgical_threshold=0.3)
    assert change.decision == "rewrite"


def test_classify_identical_sets_routes_to_unchanged():
    cached = CachedSection(notes_hash="h", body="cached", finding_ids=["id1", "id2"])
    change = classify_section_change(cached=cached, live_finding_ids=["id1", "id2"], surgical_threshold=0.3)
    assert change.decision == "unchanged"
    assert change.added_indices == []
    assert change.removed_ids == []
    assert change.unchanged_count == 2


def test_classify_small_delta_routes_to_surgical():
    """1 added out of 5 → 0.2 churn ≤ 0.3 threshold → surgical."""
    cached = CachedSection(notes_hash="h", body="cached", finding_ids=["id1", "id2", "id3", "id4"])
    change = classify_section_change(
        cached=cached,
        live_finding_ids=["id1", "id2", "id3", "id4", "id5"],
        surgical_threshold=0.3,
    )
    assert change.decision == "surgical"
    assert change.added_indices == [5]
    assert change.removed_ids == []


def test_classify_large_delta_routes_to_rewrite():
    """3 added of 4 live → 0.75 churn > 0.3 threshold → rewrite."""
    cached = CachedSection(notes_hash="h", body="cached", finding_ids=["id1"])
    change = classify_section_change(
        cached=cached,
        live_finding_ids=["id1", "idA", "idB", "idC"],
        surgical_threshold=0.3,
    )
    assert change.decision == "rewrite"


def test_classify_threshold_disabled_always_rewrites_when_changed():
    """Negative threshold (use_surgical_edits=False sentinel) disables surgical entirely."""
    cached = CachedSection(notes_hash="h", body="cached", finding_ids=["id1", "id2"])
    change = classify_section_change(
        cached=cached,
        live_finding_ids=["id1", "id3"],  # 1 add, 1 remove → would be 1.0 churn anyway
        surgical_threshold=-1.0,
    )
    assert change.decision == "rewrite"


def test_classify_churn_ratio_at_exactly_threshold_routes_to_surgical():
    """``churn_ratio == surgical_threshold`` is inclusive — surgical, not rewrite."""
    cached = CachedSection(notes_hash="h", body="cached", finding_ids=["id1", "id2", "id3"])
    change = classify_section_change(
        cached=cached,
        live_finding_ids=["id1", "id2", "id3", "id4"],
        surgical_threshold=0.25,
    )
    assert change.decision == "surgical"
    assert change.churn_ratio == 0.25


# ---------- surgical_aggregate ----------


def test_surgical_aggregate_merges_cached_and_new_claims(mock_provider_factory):
    """Cached claims survive minus removed; new claims attach to added notes."""
    section = PRIMARY_SECTIONS[0]
    cached = CachedSection(
        notes_hash="h",
        body="Original body paragraph one.\n\nOriginal body paragraph two.",
        claims=[
            {
                "text": "Cached claim A.",
                "sources": [{"file": "a.py", "lines": None, "fingerprint": ""}],
            },
            {
                "text": "Cached claim B (will be removed).",
                "sources": [{"file": "b.py", "lines": None, "fingerprint": ""}],
            },
        ],
        contradictions=[],
        finding_ids=[
            compute_finding_id(file="a.py", section_id=section.id, finding="A1"),
            compute_finding_id(file="b.py", section_id=section.id, finding="B1 (removed)"),
        ],
    )
    live_notes = [
        _note("a.py", "A1"),
        _note("c.py", "C1 (added)"),
    ]
    live_ids = note_finding_ids(live_notes, section_id=section.id)
    # 1 added + 1 removed out of 2 live = 1.0 churn — needs threshold ≥ 1.0
    # to route surgical. The merge logic itself is what's under test.
    change = classify_section_change(cached=cached, live_finding_ids=live_ids, surgical_threshold=1.0)
    assert change.decision == "surgical"

    edit = SurgicalEdit(
        body="Edited body — preserves A, drops B, adds C.",
        new_claims=[
            SurgicalClaim(text="New claim from C.", source_indices=[1]),
        ],
        removed_claim_indices=[2],  # drop "Cached claim B"
        contradictions=[],
    )

    provider = mock_provider_factory(json_factory=lambda schema, system, user: edit)
    bundle = surgical_aggregate(
        section=section,
        cached=cached,
        live_notes=live_notes,
        change=change,
        provider=provider,
    )
    assert bundle.body == "Edited body — preserves A, drops B, adds C."
    # Cached claim A survives, cached claim B was removed, new claim from C added.
    assert len(bundle.claims) == 2
    assert bundle.claims[0].text == "Cached claim A."
    assert bundle.claims[1].text == "New claim from C."
    # The new claim's source resolves to c.py (the added note), not a.py or b.py.
    assert any(ref.file == "c.py" for ref in bundle.claims[1].sources)


def test_surgical_aggregate_ignores_out_of_range_removed_indices(mock_provider_factory):
    """Bad indices from the model don't break the merge — they're silently dropped."""
    section = PRIMARY_SECTIONS[0]
    cached = CachedSection(
        notes_hash="h",
        body="Body.",
        claims=[{"text": "Only claim.", "sources": [{"file": "a.py", "lines": None, "fingerprint": ""}]}],
        contradictions=[],
        finding_ids=[compute_finding_id(file="a.py", section_id=section.id, finding="A1")],
    )
    live_notes = [_note("a.py", "A1"), _note("c.py", "C1")]
    live_ids = note_finding_ids(live_notes, section_id=section.id)
    change = classify_section_change(cached=cached, live_finding_ids=live_ids, surgical_threshold=1.0)

    edit = SurgicalEdit(
        body="Edited.",
        new_claims=[],
        removed_claim_indices=[42, -1, 0],  # all invalid
        contradictions=[],
    )
    provider = mock_provider_factory(json_factory=lambda schema, system, user: edit)
    bundle = surgical_aggregate(
        section=section,
        cached=cached,
        live_notes=live_notes,
        change=change,
        provider=provider,
    )
    assert len(bundle.claims) == 1
    assert bundle.claims[0].text == "Only claim."


def test_surgical_aggregate_replaces_contradictions_with_new_set(mock_provider_factory):
    """``edit.contradictions`` is the FULL post-edit set — cached contradictions are replaced."""
    section = PRIMARY_SECTIONS[0]
    cached = CachedSection(
        notes_hash="h",
        body="Body.",
        claims=[],
        contradictions=[
            {
                "summary": "Old conflict.",
                "positions": [{"text": "stale", "sources": []}],
            }
        ],
        finding_ids=[compute_finding_id(file="a.py", section_id=section.id, finding="A1")],
    )
    live_notes = [_note("a.py", "A1"), _note("c.py", "C1")]
    live_ids = note_finding_ids(live_notes, section_id=section.id)
    change = classify_section_change(cached=cached, live_finding_ids=live_ids, surgical_threshold=1.0)

    edit = SurgicalEdit(
        body="Edited.",
        new_claims=[],
        removed_claim_indices=[],
        contradictions=[
            SurgicalContradiction(
                summary="Fresh conflict.",
                positions=[SurgicalClaim(text="position from added", source_indices=[1])],
            )
        ],
    )
    provider = mock_provider_factory(json_factory=lambda schema, system, user: edit)
    bundle = surgical_aggregate(
        section=section,
        cached=cached,
        live_notes=live_notes,
        change=change,
        provider=provider,
    )
    assert len(bundle.contradictions) == 1
    assert bundle.contradictions[0].summary == "Fresh conflict."


# ---------- aggregator decision tree ----------


def test_aggregate_records_finding_ids_on_cache_write(tmp_path, mock_provider_factory):
    """Every aggregation cache write must include finding_ids — the diff cornerstone."""
    from wikifi.aggregator import SectionBody

    layout = _layout(tmp_path)
    section = PRIMARY_SECTIONS[0]
    append_note(layout, section, _note("a.py", "Order entity."))

    cache = WalkCache()
    provider = mock_provider_factory(
        json_factory=lambda schema, system, user: SectionBody(body="Synthesized."),
    )
    aggregate_all(layout=layout, provider=provider, cache=cache)
    entry = cache.aggregation[section.id]
    assert entry.finding_ids == [compute_finding_id(file="a.py", section_id=section.id, finding="Order entity.")]


def test_aggregate_takes_unchanged_path_when_only_notes_hash_differs(tmp_path, mock_provider_factory):
    """Same finding ids, different ``notes_hash`` (e.g. line range moved) → no LLM call."""
    from wikifi.aggregator import SectionBody

    layout = _layout(tmp_path)
    section = PRIMARY_SECTIONS[0]
    # Note has a source ref; we'll change the lines to invalidate notes_hash
    # while keeping finding_id stable.
    append_note(
        layout,
        section,
        {
            "file": "a.py",
            "summary": "x",
            "finding": "Order entity.",
            "sources": [{"file": "a.py", "lines": [10, 20], "fingerprint": "abc"}],
        },
    )

    cache = WalkCache()
    cache.record_aggregation(
        section.id,
        notes_hash="stale-hash-from-prior-walk",
        body="Cached body that should survive.",
        claims=[{"text": "Claim.", "sources": [{"file": "a.py", "lines": None, "fingerprint": ""}]}],
        contradictions=[],
        finding_ids=[compute_finding_id(file="a.py", section_id=section.id, finding="Order entity.")],
    )

    call_count = {"n": 0}

    def factory(schema, system, user):
        call_count["n"] += 1
        return SectionBody(body="should not be called")

    provider = mock_provider_factory(json_factory=factory)
    stats = aggregate_all(layout=layout, provider=provider, cache=cache)

    assert call_count["n"] == 0, "unchanged-finding-ids path must not call the LLM"
    assert stats.sections_cached == 1
    body = layout.section_path(section).read_text()
    assert "Cached body that should survive." in body
    # Cache key is *not* refreshed here. The cached claims still carry
    # SourceRefs from the prior walk's notes (e.g. lines=[10, 20] when
    # current lines could be [12, 22]); refreshing notes_hash to match
    # live notes would let ``aggregation_fully_cached`` flag the entry
    # as fresh and let the orchestrator's short-circuit lock those
    # stale citations in place. Leaving the key alone keeps the
    # predicate honest until a real Path 4 rewrite refreshes citations.
    assert cache.aggregation[section.id].notes_hash == "stale-hash-from-prior-walk"


def test_aggregate_takes_surgical_path_for_small_delta(tmp_path, mock_provider_factory):
    """1 added finding out of 4 live → surgical edit, not rewrite."""
    from wikifi.aggregator import SectionBody
    from wikifi.cache import hash_section_notes

    layout = _layout(tmp_path)
    section = PRIMARY_SECTIONS[0]
    findings_text = ["A1", "A2", "A3"]
    for f in findings_text:
        append_note(layout, section, _note("a.py", f))

    cache = WalkCache()
    cache.record_aggregation(
        section.id,
        notes_hash=hash_section_notes(
            [{"file": "a.py", "summary": "x", "finding": f, "sources": []} for f in findings_text]
        ),
        body="Original body.",
        claims=[],
        contradictions=[],
        finding_ids=[compute_finding_id(file="a.py", section_id=section.id, finding=f) for f in findings_text],
    )
    # Add a fourth note — 1/4 churn = 0.25 ≤ 0.3 → surgical.
    append_note(layout, section, _note("a.py", "A4_added"))

    call_log = {"surgical": 0, "rewrite": 0}

    def factory(schema, system, user):
        if schema is SurgicalEdit:
            call_log["surgical"] += 1
            return SurgicalEdit(body="Edited body with A4.")
        if schema is SectionBody:
            call_log["rewrite"] += 1
            return SectionBody(body="rewrite body")
        raise AssertionError(f"unexpected schema {schema}")

    provider = mock_provider_factory(json_factory=factory)
    stats = aggregate_all(layout=layout, provider=provider, cache=cache, surgical_threshold=0.3)
    assert call_log["surgical"] == 1
    assert call_log["rewrite"] == 0
    assert stats.sections_edited == 1
    assert stats.sections_rewritten == 0
    body = layout.section_path(section).read_text()
    assert "Edited body with A4." in body


def test_aggregate_takes_rewrite_path_when_churn_above_threshold(tmp_path, mock_provider_factory):
    from wikifi.aggregator import SectionBody
    from wikifi.cache import hash_section_notes

    layout = _layout(tmp_path)
    section = PRIMARY_SECTIONS[0]
    cache = WalkCache()
    # Cache says one finding existed; live notes have four entirely different findings.
    cache.record_aggregation(
        section.id,
        notes_hash=hash_section_notes([{"file": "a.py", "summary": "x", "finding": "old", "sources": []}]),
        body="Old body.",
        claims=[],
        contradictions=[],
        finding_ids=[compute_finding_id(file="a.py", section_id=section.id, finding="old")],
    )
    for finding in ("new1", "new2", "new3", "new4"):
        append_note(layout, section, _note("a.py", finding))

    call_log = {"surgical": 0, "rewrite": 0}

    def factory(schema, system, user):
        if schema is SurgicalEdit:
            call_log["surgical"] += 1
            return SurgicalEdit(body="surgical")
        if schema is SectionBody:
            call_log["rewrite"] += 1
            return SectionBody(body="Full rewrite body.")
        raise AssertionError(f"unexpected schema {schema}")

    provider = mock_provider_factory(json_factory=factory)
    stats = aggregate_all(layout=layout, provider=provider, cache=cache, surgical_threshold=0.3)
    assert call_log["surgical"] == 0
    assert call_log["rewrite"] == 1
    assert stats.sections_rewritten == 1
    assert stats.sections_edited == 0


def test_aggregate_use_surgical_false_skips_surgical_path(tmp_path, mock_provider_factory):
    """``use_surgical_edits=False`` disables the surgical path entirely (Plan A behavior)."""
    from wikifi.aggregator import SectionBody
    from wikifi.cache import hash_section_notes

    layout = _layout(tmp_path)
    section = PRIMARY_SECTIONS[0]
    findings_text = ["A1", "A2", "A3"]
    for f in findings_text:
        append_note(layout, section, _note("a.py", f))

    cache = WalkCache()
    cache.record_aggregation(
        section.id,
        notes_hash=hash_section_notes(
            [{"file": "a.py", "summary": "x", "finding": f, "sources": []} for f in findings_text]
        ),
        body="Original.",
        claims=[],
        contradictions=[],
        finding_ids=[compute_finding_id(file="a.py", section_id=section.id, finding=f) for f in findings_text],
    )
    append_note(layout, section, _note("a.py", "A4_added"))

    call_log = {"surgical": 0, "rewrite": 0}

    def factory(schema, system, user):
        if schema is SurgicalEdit:
            call_log["surgical"] += 1
            return SurgicalEdit(body="surgical")
        if schema is SectionBody:
            call_log["rewrite"] += 1
            return SectionBody(body="rewrite")
        raise AssertionError(f"unexpected schema {schema}")

    provider = mock_provider_factory(json_factory=factory)
    aggregate_all(
        layout=layout,
        provider=provider,
        cache=cache,
        use_surgical_edits=False,
    )
    assert call_log["surgical"] == 0
    assert call_log["rewrite"] == 1


def test_aggregate_falls_back_to_rewrite_when_surgical_raises(tmp_path, mock_provider_factory):
    """A surgical-path LLM failure must not leave the section empty — fall back to rewrite."""
    from wikifi.aggregator import SectionBody
    from wikifi.cache import hash_section_notes

    layout = _layout(tmp_path)
    section = PRIMARY_SECTIONS[0]
    findings_text = ["A1", "A2", "A3"]
    for f in findings_text:
        append_note(layout, section, _note("a.py", f))

    cache = WalkCache()
    cache.record_aggregation(
        section.id,
        notes_hash=hash_section_notes(
            [{"file": "a.py", "summary": "x", "finding": f, "sources": []} for f in findings_text]
        ),
        body="Cached.",
        claims=[],
        contradictions=[],
        finding_ids=[compute_finding_id(file="a.py", section_id=section.id, finding=f) for f in findings_text],
    )
    append_note(layout, section, _note("a.py", "A4_added"))

    def factory(schema, system, user):
        if schema is SurgicalEdit:
            raise RuntimeError("surgical model unavailable")
        if schema is SectionBody:
            return SectionBody(body="Recovered via rewrite.")
        raise AssertionError(f"unexpected schema {schema}")

    provider = mock_provider_factory(json_factory=factory)
    stats = aggregate_all(layout=layout, provider=provider, cache=cache, surgical_threshold=0.5)
    body = layout.section_path(section).read_text()
    assert "Recovered via rewrite." in body
    # Counted as rewrite, not edit, because the fallback path won.
    assert stats.sections_rewritten == 1
    assert stats.sections_edited == 0


# ---------- stability test (the load-bearing assertion) ----------


def test_surgical_edit_preserves_unchanged_paragraphs_when_model_honors_contract(
    mock_provider_factory,
):
    """If the LLM honors the prompt and returns the input body verbatim plus an addition,
    the surgical pipeline preserves every byte of the unchanged content.

    This is the contract Plan B is built on. The test mocks the LLM
    response to be a *literal* good citizen — input body unchanged, one
    sentence appended — and verifies the merged output preserves the
    original prose. Real-world stability depends on prompt quality + a
    follow-up critic; this test guards the *mechanism* (no rendering
    pass mangles the unchanged region).
    """
    section = PRIMARY_SECTIONS[0]
    original = "First paragraph that should survive verbatim.\n\nSecond paragraph that should also survive verbatim."
    cached = CachedSection(
        notes_hash="h",
        body=original,
        claims=[],
        contradictions=[],
        finding_ids=[
            compute_finding_id(file="a.py", section_id=section.id, finding="A1"),
            compute_finding_id(file="b.py", section_id=section.id, finding="B1"),
        ],
    )
    live_notes = [
        _note("a.py", "A1"),
        _note("b.py", "B1"),
        _note("c.py", "C1 added"),
    ]
    live_ids = note_finding_ids(live_notes, section_id=section.id)
    change = classify_section_change(cached=cached, live_finding_ids=live_ids, surgical_threshold=0.5)
    assert change.decision == "surgical"

    edited_body = original + "\n\nThird paragraph integrating the added finding."
    edit = SurgicalEdit(
        body=edited_body,
        new_claims=[SurgicalClaim(text="C1 claim.", source_indices=[1])],
        removed_claim_indices=[],
        contradictions=[],
    )
    provider = mock_provider_factory(json_factory=lambda schema, system, user: edit)
    bundle = surgical_aggregate(section=section, cached=cached, live_notes=live_notes, change=change, provider=provider)
    # The original two paragraphs survive the merge byte-for-byte.
    assert original in bundle.body
    # And the new content is present.
    assert "Third paragraph integrating the added finding." in bundle.body


# ---------- PR review regressions ----------


def test_note_finding_ids_returns_empty_for_malformed_notes():
    """Notes missing ``file`` or ``finding`` get an empty-string id.

    Without this, hashing empty strings via :func:`compute_finding_id`
    produces a deterministic non-empty id that would let two malformed
    notes from different walks compare equal as "unchanged" findings —
    routing a section onto the cache/surgical paths despite having no
    real identity to anchor on.
    """
    notes = [
        _note("a.py", "real finding"),
        {"file": "", "summary": "x", "finding": "no file"},
        {"file": "b.py", "summary": "x", "finding": ""},
        {"summary": "x"},  # neither file nor finding present
        {"file": "c.py", "summary": "x", "finding": None},  # null finding
    ]
    ids = note_finding_ids(notes, section_id="entities")
    assert ids[0] != ""
    assert ids[1] == ""
    assert ids[2] == ""
    assert ids[3] == ""
    assert ids[4] == ""


def test_classify_force_rewrites_when_any_finding_id_is_empty():
    """A malformed/legacy note (empty id) in either set forces a rewrite.

    Two empty-string ids would otherwise compare equal in the
    set-symmetric-difference computation and let the section land on
    the cache/surgical paths. The classifier must short-circuit to
    rewrite when it detects any empty id.
    """
    cached = CachedSection(notes_hash="h", body="cached", finding_ids=["real_id_a", ""])
    change = classify_section_change(cached=cached, live_finding_ids=["real_id_a", ""], surgical_threshold=0.3)
    assert change.decision == "rewrite", (
        "empty finding_id on either side must force rewrite, even when cached and live look superficially identical"
    )


def test_section_change_churn_ratio_max_when_everything_removed():
    """``total_live == 0`` plus removed_ids → max churn (1.0), not 0.0.

    Mirrors the classifier's ``max(total_live, 1)`` guard. Without
    this, downstream code reading ``churn_ratio`` for a "removed
    everything" section would see 0.0 and treat it as a no-change
    case.
    """
    from wikifi.surgical import SectionChange

    removed_only = SectionChange(
        decision="rewrite",
        added_indices=[],
        removed_ids=["a", "b"],
        unchanged_count=0,
        total_live=0,
    )
    assert removed_only.churn_ratio == 1.0

    # Truly empty section (no cached, no live) stays at 0.0.
    empty = SectionChange(
        decision="rewrite",
        added_indices=[],
        removed_ids=[],
        unchanged_count=0,
        total_live=0,
    )
    assert empty.churn_ratio == 0.0


def test_aggregate_path2_does_not_refresh_cache_key(tmp_path, mock_provider_factory):
    """The unchanged-finding-ids path must leave the cache entry alone.

    Refreshing ``notes_hash`` to match live notes would let
    :func:`aggregation_fully_cached` think the section is fresh and
    skip stage 3 on the next walk — locking in cached citations whose
    line ranges / fingerprints have drifted since the prior walk.
    Leaving the cache key unchanged keeps the orchestrator's
    short-circuit honest until a real Path 4 rewrite refreshes
    citations.
    """
    from wikifi.aggregator import SectionBody, aggregation_fully_cached

    layout = _layout(tmp_path)
    section = PRIMARY_SECTIONS[0]
    append_note(
        layout,
        section,
        {
            "file": "a.py",
            "summary": "x",
            "finding": "Order entity.",
            "sources": [{"file": "a.py", "lines": [10, 20], "fingerprint": "abc"}],
        },
    )
    cache = WalkCache()
    cache.record_aggregation(
        section.id,
        notes_hash="prior-walk-hash",
        body="Cached body.",
        claims=[],
        contradictions=[],
        finding_ids=[compute_finding_id(file="a.py", section_id=section.id, finding="Order entity.")],
    )
    # Empty cache entries on every other primary section so the
    # aggregator doesn't crash trying to look them up.
    for other in PRIMARY_SECTIONS[1:]:
        from wikifi.cache import hash_section_notes

        cache.record_aggregation(
            other.id,
            notes_hash=hash_section_notes([]),
            body="",
            claims=[],
            contradictions=[],
        )

    provider = mock_provider_factory(
        json_factory=lambda schema, system, user: SectionBody(body="x"),
    )
    aggregate_all(layout=layout, provider=provider, cache=cache)

    # Cache key untouched.
    assert cache.aggregation[section.id].notes_hash == "prior-walk-hash"
    # And aggregation_fully_cached refuses to flag the section as fresh.
    assert not aggregation_fully_cached(layout, cache), (
        "Path 2 must not be reachable as 'fully cached' until a real Path 4 rewrite refreshes citations"
    )
