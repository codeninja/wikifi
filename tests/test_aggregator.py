from wikifi.aggregator import SectionBody, aggregate_all
from wikifi.sections import PRIMARY_SECTIONS
from wikifi.wiki import WikiLayout, append_note, initialize


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
