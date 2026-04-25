from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from wikifi.notes_store import group_by_section, load_notes, write_note
from wikifi.schemas import ExtractionFinding, ExtractionNote


def _make_note(file_ref: str, *findings: tuple[str, str]) -> ExtractionNote:
    return ExtractionNote(
        timestamp=datetime.now(UTC),
        file_reference=file_ref,
        role_summary=f"role of {file_ref}",
        findings=[ExtractionFinding(section=s, finding=f) for s, f in findings],
    )


def test_write_and_load_round_trip(tmp_path: Path):
    note = _make_note("src/billing.py", ("capabilities", "Charges customers."))
    written = write_note(tmp_path, note)
    assert written.is_file()
    loaded = load_notes(tmp_path)
    assert len(loaded) == 1
    assert loaded[0].file_reference == "src/billing.py"
    assert loaded[0].findings[0].section == "capabilities"


def test_load_skips_invalid(tmp_path: Path):
    (tmp_path / "good.json").write_text(_make_note("a", ("intent", "i")).model_dump_json(), encoding="utf-8")
    (tmp_path / "broken.json").write_text("not json", encoding="utf-8")
    (tmp_path / "wrong.json").write_text("{}", encoding="utf-8")
    notes = load_notes(tmp_path)
    assert len(notes) == 1


def test_group_by_section_buckets():
    notes = [
        _make_note("a.py", ("capabilities", "x")),
        _make_note("b.py", ("capabilities", "y"), ("intent", "z")),
    ]
    grouped = group_by_section(notes)
    assert len(grouped["capabilities"]) == 2
    assert len(grouped["intent"]) == 1


def test_load_notes_missing_dir(tmp_path: Path):
    assert load_notes(tmp_path / "nope") == []
