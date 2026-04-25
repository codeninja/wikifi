from pathlib import Path

from wikifi.extractor import FileFindings, SectionFinding, extract_repo
from wikifi.wiki import WikiLayout, initialize, read_notes


def _layout(tmp_path):
    layout = WikiLayout(root=tmp_path)
    initialize(layout, model="m", provider="ollama", ollama_host="http://h")
    return layout


def test_extract_repo_appends_findings_and_filters_invalid_section_ids(tmp_path, mock_provider_factory):
    layout = _layout(tmp_path)
    (tmp_path / "a.py").write_text("# fake\n")

    findings_a = FileFindings(
        summary="domain class",
        findings=[
            SectionFinding(section_id="entities", finding="Defines an Order entity."),
            SectionFinding(section_id="capabilities", finding="Lets users place orders."),
            SectionFinding(section_id="not_a_real_section", finding="should be dropped"),
        ],
    )
    provider = mock_provider_factory(json_responses={FileFindings: [findings_a]})

    stats = extract_repo(
        layout=layout,
        provider=provider,
        files=[Path("a.py")],
        repo_root=tmp_path,
    )

    assert stats.files_seen == 1
    assert stats.files_with_findings == 1
    assert stats.findings_total == 2  # invalid section filtered out
    notes = read_notes(layout, "entities")
    assert len(notes) == 1
    assert notes[0]["file"] == "a.py"
    assert "Order" in notes[0]["finding"]


def test_extract_repo_records_skipped_when_provider_raises(tmp_path, mock_provider_factory):
    layout = _layout(tmp_path)
    (tmp_path / "a.py").write_text("x = 1\n")

    def raiser(schema, system, user):
        raise RuntimeError("model unavailable")

    provider = mock_provider_factory(json_factory=raiser)

    stats = extract_repo(
        layout=layout,
        provider=provider,
        files=[Path("a.py")],
        repo_root=tmp_path,
    )

    assert stats.files_seen == 1
    assert stats.files_skipped == 1
    assert stats.findings_total == 0


def test_extract_repo_skips_unreadable_file(tmp_path, mock_provider_factory):
    layout = _layout(tmp_path)
    provider = mock_provider_factory(json_responses={FileFindings: []})

    stats = extract_repo(
        layout=layout,
        provider=provider,
        files=[Path("ghost.py")],
        repo_root=tmp_path,
    )
    assert stats.files_skipped == 1
    assert stats.findings_total == 0


def test_extract_repo_truncates_large_files(tmp_path, mock_provider_factory):
    layout = _layout(tmp_path)
    big = tmp_path / "big.py"
    big.write_text("a = 1\n" * 5_000)

    captured: list[str] = []

    def factory(schema, system, user):
        captured.append(user)
        return FileFindings()

    provider = mock_provider_factory(json_factory=factory)

    extract_repo(
        layout=layout,
        provider=provider,
        files=[Path("big.py")],
        repo_root=tmp_path,
        max_file_bytes=500,
    )
    assert "[truncated]" in captured[0]


def test_section_ids_documented_in_system_prompt():
    """Only primary section ids appear in the extractor prompt — derivatives are Stage 4."""
    from wikifi.extractor import EXTRACTION_SYSTEM_PROMPT
    from wikifi.sections import DERIVATIVE_SECTION_IDS, PRIMARY_SECTION_IDS

    for sid in PRIMARY_SECTION_IDS:
        assert sid in EXTRACTION_SYSTEM_PROMPT
    for sid in DERIVATIVE_SECTION_IDS:
        # Derivative ids must be absent so the model is never asked to
        # produce per-file findings for them.
        assert sid not in EXTRACTION_SYSTEM_PROMPT.split("Only emit findings for these section ids:")[1].split("\n")[0]


def test_extract_repo_drops_derivative_section_findings(tmp_path, mock_provider_factory):
    """Even if the model emits a derivative section id, the extractor filters it out."""
    from wikifi.sections import DERIVATIVE_SECTION_IDS
    from wikifi.wiki import WikiLayout, initialize, read_notes

    layout = WikiLayout(root=tmp_path)
    initialize(layout, model="m", provider="ollama", ollama_host="http://h")
    (tmp_path / "a.py").write_text("# fake\n")

    derivative_id = DERIVATIVE_SECTION_IDS[0]
    findings = FileFindings(
        summary="x",
        findings=[
            SectionFinding(section_id="entities", finding="Order entity."),
            SectionFinding(section_id=derivative_id, finding="Buyer persona (should be dropped)."),
        ],
    )
    provider = mock_provider_factory(json_responses={FileFindings: [findings]})

    extract_repo(
        layout=layout,
        provider=provider,
        files=[Path("a.py")],
        repo_root=tmp_path,
    )

    assert len(read_notes(layout, "entities")) == 1
    assert read_notes(layout, derivative_id) == []
