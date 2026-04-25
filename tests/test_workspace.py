from __future__ import annotations

from pathlib import Path

from wikifi.workspace import all_section_paths, provision_workspace, reset_notes


def test_provision_creates_layout(tmp_path: Path):
    ws = provision_workspace(tmp_path)
    assert ws.wiki_dir.is_dir()
    assert ws.notes_dir.is_dir()
    assert (ws.notes_dir / ".gitignore").is_file()
    assert (ws.wiki_dir / ".gitignore").is_file()


def test_provision_idempotent(tmp_path: Path):
    ws1 = provision_workspace(tmp_path)
    (ws1.wiki_dir / "intent.md").write_text("## hello\n", encoding="utf-8")
    ws2 = provision_workspace(tmp_path)
    assert ws1.wiki_dir == ws2.wiki_dir
    assert (ws2.wiki_dir / "intent.md").read_text() == "## hello\n"


def test_reset_notes_removes_jsons(tmp_path: Path):
    ws = provision_workspace(tmp_path)
    (ws.notes_dir / "a.json").write_text("{}", encoding="utf-8")
    (ws.notes_dir / "b.json").write_text("{}", encoding="utf-8")
    (ws.notes_dir / "keep.txt").write_text("not a note", encoding="utf-8")
    removed = reset_notes(ws)
    assert removed == 2
    assert not (ws.notes_dir / "a.json").exists()
    assert (ws.notes_dir / "keep.txt").exists()


def test_reset_notes_missing_dir_safe(tmp_path: Path):
    from wikifi.workspace import Workspace

    ws = Workspace(root=tmp_path, wiki_dir=tmp_path / "x", notes_dir=tmp_path / "x" / ".notes")
    assert reset_notes(ws) == 0


def test_all_section_paths(tmp_path: Path):
    ws = provision_workspace(tmp_path)
    paths = all_section_paths(ws)
    assert "intent" in paths
    assert paths["intent"].name == "intent.md"
    assert "personas" in paths
