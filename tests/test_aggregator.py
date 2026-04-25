from wikifi.aggregator import SectionBody, aggregate_all
from wikifi.sections import SECTIONS
from wikifi.wiki import WikiLayout, append_note, initialize


def _setup(tmp_path):
    layout = WikiLayout(root=tmp_path)
    initialize(layout, model="m", provider="ollama", ollama_host="http://h")
    return layout


def test_aggregate_writes_body_for_section_with_notes(tmp_path, mock_provider_factory):
    layout = _setup(tmp_path)
    section = SECTIONS[0]  # personas
    append_note(layout, section, {"file": "a.py", "summary": "domain class", "finding": "Hosts the Buyer persona."})

    provider = mock_provider_factory(
        json_factory=lambda schema, system, user: SectionBody(body="A buyer purchases items.")
    )
    stats = aggregate_all(layout=layout, provider=provider)

    body = layout.section_path(section).read_text()
    assert "A buyer purchases items." in body
    assert stats.sections_written == 1
    assert stats.sections_empty == len(SECTIONS) - 1


def test_aggregate_writes_empty_body_when_no_notes(tmp_path, mock_provider_factory):
    layout = _setup(tmp_path)
    provider = mock_provider_factory()  # no responses; should not be called for empty sections
    stats = aggregate_all(layout=layout, provider=provider)
    assert stats.sections_written == 0
    assert stats.sections_empty == len(SECTIONS)
    body = layout.section_path(SECTIONS[0]).read_text()
    assert "No findings" in body


def test_aggregate_falls_back_when_provider_raises(tmp_path, mock_provider_factory):
    layout = _setup(tmp_path)
    section = SECTIONS[0]
    append_note(layout, section, {"file": "a.py", "summary": "x", "finding": "Buyer."})

    def raiser(schema, system, user):
        raise RuntimeError("kaboom")

    provider = mock_provider_factory(json_factory=raiser)
    aggregate_all(layout=layout, provider=provider)
    body = layout.section_path(section).read_text()
    assert "Aggregation failed" in body
    assert "Buyer." in body  # raw notes preserved
