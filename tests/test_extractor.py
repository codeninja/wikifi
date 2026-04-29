from pathlib import Path

import pytest

from wikifi.extractor import (
    FileFindings,
    SectionFinding,
    _chunk_text,
    extract_repo,
)
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


def test_extract_repo_chunks_large_files(tmp_path, mock_provider_factory):
    """Files larger than the chunk size are split into multiple LLM calls,
    not truncated, so monolithic files are fully consumed."""
    layout = _layout(tmp_path)
    big = tmp_path / "big.py"
    # Unique per-line content so chunk positions are unambiguous.
    body = "".join(f"line_{i:05d}_with_unique_content_here\n" for i in range(800))
    big.write_text(body)

    captured: list[str] = []

    def factory(schema, system, user):
        captured.append(user)
        return FileFindings()

    provider = mock_provider_factory(json_factory=factory)

    stats = extract_repo(
        layout=layout,
        provider=provider,
        files=[Path("big.py")],
        repo_root=tmp_path,
        chunk_size_bytes=1_000,
        chunk_overlap_bytes=100,
    )

    assert len(captured) > 1, "large file must produce multiple chunked calls"
    assert stats.chunks_processed == len(captured)
    # Each chunk announces its position so the LLM knows it's seeing a slice.
    assert all("Chunk:" in prompt for prompt in captured)
    assert "Chunk: 1 of" in captured[0]
    # Together the chunks must cover the full file: each chunk is a slice of
    # `body`, the first slice starts at byte 0, and the last slice ends at
    # the final byte. Overlap means adjacent slices revisit some bytes, but
    # nothing is dropped.
    chunk_bodies = [prompt.split("```\n", 1)[1].rsplit("\n```", 1)[0] for prompt in captured]
    positions = [body.find(c) for c in chunk_bodies]
    assert all(p >= 0 for p in positions), "every chunk must be a slice of the original file"
    assert positions[0] == 0
    assert positions[-1] + len(chunk_bodies[-1]) == len(body)


def test_extract_repo_chunk_overlap_appears_in_adjacent_calls(tmp_path, mock_provider_factory):
    """Adjacent chunks share an overlap window so cross-boundary context survives."""
    layout = _layout(tmp_path)
    # 30 distinct lines; chunk at ~250 bytes with 80 bytes overlap forces
    # multi-chunk and a clearly identifiable shared region.
    lines = [f"line_{i:02d}_with_some_padding\n" for i in range(30)]
    body = "".join(lines)
    (tmp_path / "wide.py").write_text(body)

    captured: list[str] = []

    def factory(schema, system, user):
        captured.append(user)
        return FileFindings()

    provider = mock_provider_factory(json_factory=factory)

    extract_repo(
        layout=layout,
        provider=provider,
        files=[Path("wide.py")],
        repo_root=tmp_path,
        chunk_size_bytes=250,
        chunk_overlap_bytes=80,
    )

    assert len(captured) >= 2

    def chunk_body(prompt: str) -> str:
        return prompt.split("```\n", 1)[1].rsplit("\n```", 1)[0]

    a = chunk_body(captured[0])
    b = chunk_body(captured[1])
    # The tail of chunk A should reappear at the head of chunk B.
    overlap_marker = a[-40:]
    assert overlap_marker in b


def test_extract_repo_dedupes_findings_from_overlap(tmp_path, mock_provider_factory):
    """If two chunks of the same file produce the same finding (because the
    declaration sat in their overlap region), the finding is only stored once."""
    layout = _layout(tmp_path)
    body = "x = 1\n" * 1_000
    (tmp_path / "dup.py").write_text(body)

    duplicate_finding = FileFindings(
        summary="dup",
        findings=[SectionFinding(section_id="entities", finding="Defines an Order entity.")],
    )

    def factory(schema, system, user):
        # Every chunk reports the same finding.
        return duplicate_finding

    provider = mock_provider_factory(json_factory=factory)

    stats = extract_repo(
        layout=layout,
        provider=provider,
        files=[Path("dup.py")],
        repo_root=tmp_path,
        chunk_size_bytes=500,
        chunk_overlap_bytes=50,
    )

    assert stats.chunks_processed > 1
    assert stats.findings_total == 1
    notes = read_notes(layout, "entities")
    assert len(notes) == 1


def test_extract_repo_records_chunk_metadata_when_chunked(tmp_path, mock_provider_factory):
    """Notes from chunked files carry chunk index/total so debugging is possible."""
    layout = _layout(tmp_path)
    body = "x = 1\n" * 1_000
    (tmp_path / "tagged.py").write_text(body)

    findings_per_chunk = [
        FileFindings(findings=[SectionFinding(section_id="entities", finding=f"chunk-{i}-entity")]) for i in range(50)
    ]

    iterator = iter(findings_per_chunk)

    def factory(schema, system, user):
        return next(iterator)

    provider = mock_provider_factory(json_factory=factory)

    extract_repo(
        layout=layout,
        provider=provider,
        files=[Path("tagged.py")],
        repo_root=tmp_path,
        chunk_size_bytes=500,
        chunk_overlap_bytes=50,
    )

    notes = read_notes(layout, "entities")
    assert len(notes) >= 2
    assert all("chunk" in n and "chunks" in n for n in notes)
    assert {n["chunk"] for n in notes} == set(range(len(notes)))


def test_extract_repo_single_call_for_small_file(tmp_path, mock_provider_factory):
    """Files within chunk_size_bytes still take exactly one LLM call and
    omit chunk metadata from notes."""
    layout = _layout(tmp_path)
    (tmp_path / "small.py").write_text("class Order: ...\n")

    findings = FileFindings(
        summary="small",
        findings=[SectionFinding(section_id="entities", finding="Order entity.")],
    )
    provider = mock_provider_factory(json_responses={FileFindings: [findings]})

    extract_repo(
        layout=layout,
        provider=provider,
        files=[Path("small.py")],
        repo_root=tmp_path,
        chunk_size_bytes=10_000,
        chunk_overlap_bytes=200,
    )

    notes = read_notes(layout, "entities")
    assert len(notes) == 1
    assert "chunk" not in notes[0]
    assert "chunks" not in notes[0]


# ---------------------------------------------------------------------------
# Recursive splitter unit tests
# ---------------------------------------------------------------------------


def test_chunk_text_returns_single_chunk_when_under_size():
    assert _chunk_text("hello world", chunk_size=100, overlap=10) == ["hello world"]


def test_chunk_text_handles_empty_text():
    assert _chunk_text("", chunk_size=100, overlap=10) == [""]


def test_chunk_text_exact_size_is_single_chunk():
    text = "a" * 100
    assert _chunk_text(text, chunk_size=100, overlap=10) == [text]


def test_chunk_text_splits_on_paragraphs_first():
    text = "paragraph one\n\nparagraph two\n\nparagraph three\n\nparagraph four"
    chunks = _chunk_text(text, chunk_size=30, overlap=0)
    assert len(chunks) >= 2
    assert "".join(chunks) == text


def test_chunk_text_falls_back_to_byte_split_on_monolithic_input():
    """A single line with no whitespace must still be chunked end-to-end so
    monolithic files (minified bundles, JSON dumps) are fully consumed."""
    text = "x" * 1000
    chunks = _chunk_text(text, chunk_size=100, overlap=0)
    assert len(chunks) == 10
    assert "".join(chunks) == text
    assert all(len(c) <= 100 for c in chunks)


def test_chunk_text_overlap_appears_between_adjacent_chunks():
    text = "line\n" * 200  # 1000 bytes
    chunks = _chunk_text(text, chunk_size=200, overlap=40)
    assert len(chunks) >= 2
    assert all(len(c) <= 200 for c in chunks)
    # Each successor starts with a tail of its predecessor.
    for prev, curr in zip(chunks, chunks[1:], strict=False):
        tail = prev[-40:]
        assert curr.startswith(tail)


def test_chunk_text_rejects_invalid_overlap():
    with pytest.raises(ValueError):
        _chunk_text("text", chunk_size=10, overlap=10)
    with pytest.raises(ValueError):
        _chunk_text("text", chunk_size=10, overlap=-1)


def test_chunk_text_zero_overlap_means_no_shared_bytes():
    text = "abcdefghij" * 20  # 200 bytes
    chunks = _chunk_text(text, chunk_size=50, overlap=0)
    assert "".join(chunks) == text
    assert all(len(c) <= 50 for c in chunks)


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
