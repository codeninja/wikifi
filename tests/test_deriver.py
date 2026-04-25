"""Stage 4 — derivative section synthesis tests."""

import re

from wikifi.deriver import DerivedSection, derive_all
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
