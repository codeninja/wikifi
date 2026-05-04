"""Stage 4 — derivative section synthesis tests."""

import re

from wikifi.cache import WalkCache, hash_upstream_bodies
from wikifi.deriver import DerivedSection, derivation_fully_cached, derive_all
from wikifi.sections import DERIVATIVE_SECTIONS, SECTIONS_BY_ID
from wikifi.wiki import WikiLayout, initialize, write_section


def _setup(tmp_path):
    layout = WikiLayout(root=tmp_path)
    initialize(layout, model="m", provider="ollama", ollama_host="http://h")
    return layout


def _populate_upstreams(layout, section):
    """Write non-empty bodies for every upstream of `section`."""
    for upstream_id in section.derived_from:
        upstream = SECTIONS_BY_ID[upstream_id]
        write_section(layout, upstream, f"Synthetic {upstream_id} content.")


# The deriver's user prompt starts with `## Derivative section: <Title> (id: <id>)`.
# Matching against this (rather than a substring) avoids confusion when a
# section id also appears in upstream content.
_HEADING_RE = re.compile(r"## Derivative section: .+? \(id: ([a-z_]+)\)")


def _section_id_under_synthesis(prompt: str) -> str:
    match = _HEADING_RE.search(prompt)
    assert match, f"could not find derivative section heading in prompt: {prompt[:200]}"
    return match.group(1)


def test_derive_all_synthesizes_each_derivative(tmp_path, mock_provider_factory):
    layout = _setup(tmp_path)
    for section in DERIVATIVE_SECTIONS:
        _populate_upstreams(layout, section)

    calls: list[str] = []

    def factory(schema, system, user):
        sid = _section_id_under_synthesis(user)
        calls.append(sid)
        return DerivedSection(body=f"Body for {sid}.")

    provider = mock_provider_factory(json_factory=factory)
    stats = derive_all(layout=layout, provider=provider)

    assert stats.sections_derived == len(DERIVATIVE_SECTIONS)
    assert stats.sections_skipped == 0
    assert calls == [s.id for s in DERIVATIVE_SECTIONS]
    for section in DERIVATIVE_SECTIONS:
        body = layout.section_path(section).read_text()
        assert f"Body for {section.id}." in body


def test_derive_all_skips_when_upstreams_empty(tmp_path, mock_provider_factory):
    """If no upstream has content, the derivative is skipped (placeholder body)."""
    layout = _setup(tmp_path)
    # Note: no upstreams populated — they remain at the init placeholder body.
    provider = mock_provider_factory()  # would crash if called

    stats = derive_all(layout=layout, provider=provider)

    assert stats.sections_derived == 0
    assert stats.sections_skipped == len(DERIVATIVE_SECTIONS)
    for section in DERIVATIVE_SECTIONS:
        body = layout.section_path(section).read_text()
        assert "upstream sections required" in body.lower()


def test_derive_uses_partial_upstreams_when_some_are_populated(tmp_path, mock_provider_factory):
    layout = _setup(tmp_path)
    # Populate only one upstream of `personas`.
    personas = SECTIONS_BY_ID["personas"]
    first_upstream = SECTIONS_BY_ID[personas.derived_from[0]]
    write_section(layout, first_upstream, "Single upstream body.")

    seen: dict[str, str] = {}

    def factory(schema, system, user):
        sid = _section_id_under_synthesis(user)
        seen[sid] = user
        return DerivedSection(body=f"Partial-derive body for {sid}.")

    provider = mock_provider_factory(json_factory=factory)
    derive_all(layout=layout, provider=provider)

    body = layout.section_path(personas).read_text()
    assert "Partial-derive body for personas." in body
    assert "Single upstream body." in seen["personas"]


def test_derive_falls_back_when_provider_raises(tmp_path, mock_provider_factory):
    layout = _setup(tmp_path)
    section = DERIVATIVE_SECTIONS[0]
    _populate_upstreams(layout, section)

    def raiser(schema, system, user):
        raise RuntimeError("model unavailable")

    provider = mock_provider_factory(json_factory=raiser)
    derive_all(layout=layout, provider=provider)
    body = layout.section_path(section).read_text()
    assert "Derivation failed" in body
    # Upstream evidence is preserved verbatim in the fallback.
    for upstream_id in section.derived_from:
        assert f"Synthetic {upstream_id} content." in body


def test_user_stories_can_consume_derived_personas(tmp_path, mock_provider_factory):
    """Derivatives with derivative upstreams (user_stories ← personas) work end-to-end."""
    layout = _setup(tmp_path)
    # Populate every primary upstream so personas + user_stories + diagrams all
    # have evidence; the test then verifies that user_stories' prompt sees the
    # *derived* personas body (not its placeholder).
    for section in DERIVATIVE_SECTIONS:
        for upstream_id in section.derived_from:
            upstream = SECTIONS_BY_ID[upstream_id]
            if upstream.tier == "primary":
                write_section(layout, upstream, f"Primary {upstream_id}.")

    seen: dict[str, str] = {}

    def factory(schema, system, user):
        sid = _section_id_under_synthesis(user)
        seen[sid] = user
        return DerivedSection(body=f"Derived body for {sid}.")

    provider = mock_provider_factory(json_factory=factory)
    derive_all(layout=layout, provider=provider)

    personas_body = layout.section_path("personas").read_text()
    user_stories_body = layout.section_path("user_stories").read_text()
    assert "Derived body for personas." in personas_body
    assert "Derived body for user_stories." in user_stories_body
    # The user_stories prompt must include the *derived* personas content,
    # confirming Stage 4 cascades correctly.
    assert "Derived body for personas." in seen["user_stories"]


def test_derive_uses_cache_when_upstream_bodies_unchanged(tmp_path, mock_provider_factory):
    """A second derive run with identical upstreams replays the cached body, no LLM call."""
    layout = _setup(tmp_path)
    for section in DERIVATIVE_SECTIONS:
        _populate_upstreams(layout, section)

    cache = WalkCache()
    call_count = {"n": 0}

    def factory(schema, system, user):
        call_count["n"] += 1
        return DerivedSection(body="First-pass body.")

    provider = mock_provider_factory(json_factory=factory)
    derive_all(layout=layout, provider=provider, cache=cache)
    first_calls = call_count["n"]
    assert first_calls == len(DERIVATIVE_SECTIONS)

    # Second pass — same upstreams, same cache → zero LLM calls.
    derive_all(layout=layout, provider=provider, cache=cache)
    assert call_count["n"] == first_calls
    # Stats should reflect that this run cached every section.
    stats = derive_all(layout=layout, provider=provider, cache=cache)
    assert stats.sections_cached == len(DERIVATIVE_SECTIONS)
    assert call_count["n"] == first_calls  # still no new calls
    # ``sections_revised`` counts reviser work performed in this walk.
    # A pure cache replay does no critic work, so the counter must stay
    # at zero even if the cached entries went through review previously.
    assert stats.sections_revised == 0


def test_derive_cache_misses_when_upstream_changes(tmp_path, mock_provider_factory):
    """Editing an upstream body invalidates the derivative cache for that section."""
    layout = _setup(tmp_path)
    section = DERIVATIVE_SECTIONS[0]
    _populate_upstreams(layout, section)

    cache = WalkCache()
    upstream_bodies = {
        upstream_id: layout.section_path(upstream_id).read_text() for upstream_id in section.derived_from
    }
    cache.record_derivation(
        section.id,
        upstream_hash=hash_upstream_bodies(upstream_bodies),
        body="Cached body.",
        revised=False,
    )

    # Mutate one upstream — cache should miss and the LLM should be called.
    first_upstream = SECTIONS_BY_ID[section.derived_from[0]]
    write_section(layout, first_upstream, "Edited upstream content.")

    call_count = {"n": 0}

    def factory(schema, system, user):
        call_count["n"] += 1
        return DerivedSection(body="Re-synthesized body.")

    provider = mock_provider_factory(json_factory=factory)
    derive_all(layout=layout, provider=provider, cache=cache)
    assert call_count["n"] >= 1
    body = layout.section_path(section).read_text()
    assert "Re-synthesized body." in body


def test_derive_review_walk_does_not_reuse_unrevised_cached_body(tmp_path, mock_provider_factory):
    """``--review`` must not silently inherit a cache entry produced without the critic."""
    from wikifi.critic import Critique

    layout = _setup(tmp_path)
    section = DERIVATIVE_SECTIONS[0]
    _populate_upstreams(layout, section)
    upstream_bodies = {
        upstream_id: layout.section_path(upstream_id).read_text() for upstream_id in section.derived_from
    }

    cache = WalkCache()
    cache.record_derivation(
        section.id,
        upstream_hash=hash_upstream_bodies(upstream_bodies),
        body="Unrevised cached body.",
        revised=False,
    )

    call_count = {"n": 0}

    def factory(schema, system, user):
        call_count["n"] += 1
        if schema is Critique:
            return Critique(score=9, summary="ok")
        return DerivedSection(body="New body under review.")

    provider = mock_provider_factory(json_factory=factory)
    derive_all(layout=layout, provider=provider, cache=cache, review=True)
    # Review-mode walk forces re-synthesis even though the upstream hash
    # matches the cache.
    assert call_count["n"] >= 1


def test_derive_persist_cache_called_after_each_section(tmp_path, mock_provider_factory):
    """Stage 4's persist callback fires once per derivative cache update."""
    layout = _setup(tmp_path)
    for section in DERIVATIVE_SECTIONS:
        _populate_upstreams(layout, section)

    cache = WalkCache()
    persist_calls = {"n": 0}

    def persist():
        persist_calls["n"] += 1

    provider = mock_provider_factory(
        json_factory=lambda schema, system, user: DerivedSection(body="body"),
    )
    derive_all(layout=layout, provider=provider, cache=cache, persist_cache=persist)
    assert persist_calls["n"] == len(DERIVATIVE_SECTIONS)


def test_derive_does_not_cache_when_provider_raises(tmp_path, mock_provider_factory):
    """A failed derivation must not poison the cache with the error body.

    Without this guard, a transient stage-4 outage gets recorded as the
    cached result for the section's current upstream hash, and later
    walks would replay (or short-circuit around) the error message
    until the upstream bodies themselves change.
    """
    layout = _setup(tmp_path)
    section = DERIVATIVE_SECTIONS[0]
    _populate_upstreams(layout, section)

    def raiser(schema, system, user):
        raise RuntimeError("model unavailable")

    cache = WalkCache()
    provider = mock_provider_factory(json_factory=raiser)
    derive_all(layout=layout, provider=provider, cache=cache)

    body_on_disk = layout.section_path(section).read_text()
    assert "Derivation failed" in body_on_disk
    assert section.id not in cache.derivation, "an error body must not be persisted as the cached derivation"


def test_derive_review_records_reviewed_flag_even_when_critic_accepts(tmp_path, mock_provider_factory):
    """A ``--review`` walk where the critic accepts unchanged still counts as reviewed.

    The cached ``revised`` field is the predicate that distinguishes
    "this body has been through the critic loop" from "this body never
    saw a reviewer." Tying it to whether the reviser changed text would
    make every ``--review`` walk redo the loop on a clean draft, which
    defeats the cache for the most common case.
    """
    from wikifi.critic import Critique

    layout = _setup(tmp_path)
    section = DERIVATIVE_SECTIONS[0]
    _populate_upstreams(layout, section)

    def factory(schema, system, user):
        if schema is Critique:
            # Score above the threshold → critic accepts, reviser doesn't run.
            return Critique(score=9, summary="ok")
        return DerivedSection(body="A clean draft the critic likes.")

    cache = WalkCache()
    provider = mock_provider_factory(json_factory=factory)
    derive_all(layout=layout, provider=provider, cache=cache, review=True, review_min_score=7)

    entry = cache.derivation[section.id]
    assert entry.revised is True, (
        "a body that went through the critic loop must be flagged as reviewed "
        "even when the critic accepted without changes"
    )


def test_derivation_fully_cached_rejects_uncached_empty_section(tmp_path):
    """A derivative with no upstream content and no cache entry must defeat the short-circuit.

    Mirrors the aggregator's empty-state guard: a stage-4 crash before
    the first walk wrote the empty placeholder, or an aggregation that
    drained a derivative's upstreams between walks, would otherwise let
    the orchestrator skip stage 4 with stale prose still on disk.
    """
    layout = _setup(tmp_path)
    cache = WalkCache()
    assert not derivation_fully_cached(layout, cache, review=False)


def test_derivation_fully_cached_accepts_cached_empty_state(tmp_path, mock_provider_factory):
    """Once stage 4 records the empty-upstream state, the predicate flips to True."""
    layout = _setup(tmp_path)
    cache = WalkCache()
    # No upstreams populated → every derivative goes down the empty path.
    provider = mock_provider_factory()  # would crash if called
    derive_all(layout=layout, provider=provider, cache=cache)
    assert derivation_fully_cached(layout, cache, review=False)
