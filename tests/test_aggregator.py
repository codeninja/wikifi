from wikifi.aggregator import (
    AggregatedClaim,
    AggregatedContradiction,
    SectionBody,
    aggregate_all,
)
from wikifi.cache import WalkCache, hash_section_notes
from wikifi.sections import PRIMARY_SECTIONS
from wikifi.wiki import WikiLayout, append_note, initialize, read_notes


def _setup(tmp_path):
    layout = WikiLayout(root=tmp_path)
    initialize(layout, model="m", provider="ollama", ollama_host="http://h")
    return layout


def test_aggregate_writes_body_for_section_with_notes(tmp_path, mock_provider_factory):
    layout = _setup(tmp_path)
    section = PRIMARY_SECTIONS[0]
    append_note(layout, section, {"file": "a.py", "summary": "domain class", "finding": "Defines the Order entity."})

    provider = mock_provider_factory(
        json_factory=lambda schema, system, user: SectionBody(body="An Order has line items.")
    )
    stats = aggregate_all(layout=layout, provider=provider)

    body = layout.section_path(section).read_text()
    assert "An Order has line items." in body
    assert stats.sections_written == 1
    assert stats.sections_empty == len(PRIMARY_SECTIONS) - 1


def test_aggregate_writes_empty_body_when_no_notes(tmp_path, mock_provider_factory):
    layout = _setup(tmp_path)
    provider = mock_provider_factory()  # no responses; should not be called for empty sections
    stats = aggregate_all(layout=layout, provider=provider)
    assert stats.sections_written == 0
    assert stats.sections_empty == len(PRIMARY_SECTIONS)
    body = layout.section_path(PRIMARY_SECTIONS[0]).read_text()
    assert "No findings" in body


def test_aggregate_skips_derivative_sections(tmp_path, mock_provider_factory):
    """Derivative sections are not aggregated from notes — Stage 4 handles them."""
    from wikifi.sections import DERIVATIVE_SECTIONS

    layout = _setup(tmp_path)
    derivative = DERIVATIVE_SECTIONS[0]
    # Even if someone slipped a note into a derivative jsonl, aggregate_all
    # must not touch it — that prevents accidental per-file synthesis of
    # personas/user_stories/diagrams.
    append_note(layout, derivative, {"file": "a.py", "finding": "should be ignored"})

    provider = mock_provider_factory()  # any call would crash
    aggregate_all(layout=layout, provider=provider)

    body = layout.section_path(derivative).read_text()
    # The derivative section's file is still the empty placeholder from init,
    # not a synthesized body.
    assert "Not yet populated" in body or "Run `wikifi walk`" in body


def test_aggregate_falls_back_when_provider_raises(tmp_path, mock_provider_factory):
    layout = _setup(tmp_path)
    section = PRIMARY_SECTIONS[0]
    append_note(layout, section, {"file": "a.py", "summary": "x", "finding": "Order line item."})

    def raiser(schema, system, user):
        raise RuntimeError("kaboom")

    provider = mock_provider_factory(json_factory=raiser)
    aggregate_all(layout=layout, provider=provider)
    body = layout.section_path(section).read_text()
    assert "Aggregation failed" in body
    assert "Order line item." in body  # raw notes preserved


def test_aggregate_renders_citations_and_contradictions(tmp_path, mock_provider_factory):
    layout = _setup(tmp_path)
    section = PRIMARY_SECTIONS[0]
    append_note(
        layout,
        section,
        {
            "file": "a.py",
            "summary": "domain",
            "finding": "Tax computed at order time.",
            "sources": [{"file": "src/order.py", "lines": [10, 25], "fingerprint": "abc"}],
        },
    )
    append_note(
        layout,
        section,
        {
            "file": "b.py",
            "summary": "domain",
            "finding": "Tax computed at invoice time.",
            "sources": [{"file": "src/invoice.py", "lines": [5, 12], "fingerprint": "def"}],
        },
    )

    structured = SectionBody(
        body="The system computes tax somewhere.",
        claims=[AggregatedClaim(text="Tax computation lives at the boundary.", source_indices=[1, 2])],
        contradictions=[
            AggregatedContradiction(
                summary="Where tax is computed.",
                positions=[
                    AggregatedClaim(text="At order time.", source_indices=[1]),
                    AggregatedClaim(text="At invoice time.", source_indices=[2]),
                ],
            )
        ],
    )

    provider = mock_provider_factory(
        json_factory=lambda schema, system, user: structured,
    )
    aggregate_all(layout=layout, provider=provider)
    body = layout.section_path(section).read_text()
    assert "Conflicts in source" in body
    assert "src/order.py:10-25" in body
    assert "src/invoice.py:5-12" in body
    assert "## Sources" in body


def test_aggregate_uses_cache_to_skip_unchanged_notes(tmp_path, mock_provider_factory):
    layout = _setup(tmp_path)
    section = PRIMARY_SECTIONS[0]
    append_note(layout, section, {"file": "a.py", "summary": "x", "finding": "Order entity."})

    cache = WalkCache()
    notes_hash = hash_section_notes(read_notes(layout, section))
    cache.record_aggregation(
        section.id,
        notes_hash=notes_hash,
        body="Cached body for the section.",
        claims=[],
        contradictions=[],
    )

    provider = mock_provider_factory()  # no responses queued — must not be called
    stats = aggregate_all(layout=layout, provider=provider, cache=cache)

    body = layout.section_path(section).read_text()
    assert "Cached body for the section." in body
    assert stats.sections_cached == 1


def test_aggregate_records_cache_entry_after_synthesis(tmp_path, mock_provider_factory):
    layout = _setup(tmp_path)
    section = PRIMARY_SECTIONS[0]
    append_note(layout, section, {"file": "a.py", "summary": "x", "finding": "Order."})

    cache = WalkCache()
    provider = mock_provider_factory(
        json_factory=lambda schema, system, user: SectionBody(body="Synthesized body."),
    )
    aggregate_all(layout=layout, provider=provider, cache=cache)
    assert section.id in cache.aggregation


def test_aggregate_persist_cache_called_after_each_section(tmp_path, mock_provider_factory):
    """The persist callback fires once per cache update.

    This is the contract that turns a Ctrl-C mid-stage-3 into a
    survivable event — without per-section persistence, every
    aggregation entry computed in this stage would be lost if anything
    raised before the final walk-end save.
    """
    layout = _setup(tmp_path)
    # Populate two primary sections so we get two persist invocations.
    s1, s2 = PRIMARY_SECTIONS[0], PRIMARY_SECTIONS[1]
    append_note(layout, s1, {"file": "a.py", "summary": "x", "finding": "Entity A."})
    append_note(layout, s2, {"file": "b.py", "summary": "x", "finding": "Capability B."})

    cache = WalkCache()
    persist_calls = {"n": 0}

    def persist():
        persist_calls["n"] += 1

    provider = mock_provider_factory(
        json_factory=lambda schema, system, user: SectionBody(body="body"),
    )
    aggregate_all(layout=layout, provider=provider, cache=cache, persist_cache=persist)
    assert persist_calls["n"] == 2  # one per section that got a cache update


def test_aggregate_persist_cache_survives_mid_stage_failure(tmp_path, mock_provider_factory):
    """Sections that *did* aggregate before a crash must still be on disk.

    Simulate the deriver-stage Ctrl-C scenario: after section 1 succeeds
    and persists, section 2's LLM call raises. The cache file on disk
    should contain section 1's entry — that's the resumability gain.
    """
    from wikifi.cache import load as load_cache
    from wikifi.cache import save_aggregation

    layout = _setup(tmp_path)
    s1, s2 = PRIMARY_SECTIONS[0], PRIMARY_SECTIONS[1]
    append_note(layout, s1, {"file": "a.py", "summary": "x", "finding": "Entity A."})
    append_note(layout, s2, {"file": "b.py", "summary": "x", "finding": "Capability B."})

    cache = WalkCache()
    call_count = {"n": 0}

    def factory(schema, system, user):
        call_count["n"] += 1
        if call_count["n"] >= 2:
            raise RuntimeError("simulated mid-stage-3 crash")
        return SectionBody(body="Synthesized.")

    provider = mock_provider_factory(json_factory=factory)
    aggregate_all(
        layout=layout,
        provider=provider,
        cache=cache,
        persist_cache=lambda: save_aggregation(layout, cache),
    )

    # Reload from disk to confirm section 1's body persisted before the
    # second section's failure rolled the in-memory cache back.
    on_disk = load_cache(layout)
    assert s1.id in on_disk.aggregation
    # Section 2's per-section catch wrote a fallback body, so its cache
    # entry was never recorded.
    assert s2.id not in on_disk.aggregation
