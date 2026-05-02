from wikifi.sections import SECTIONS, Section
from wikifi.wiki import (
    WIKI_DIRNAME,
    WikiLayout,
    append_note,
    initialize,
    read_notes,
    reset_notes,
    write_section,
)


def _layout(tmp_path):
    return WikiLayout(root=tmp_path)


def test_initialize_creates_full_skeleton(tmp_path):
    layout = _layout(tmp_path)
    paths = initialize(layout, model="m", provider="ollama", ollama_host="http://h")
    wiki_dir = tmp_path / WIKI_DIRNAME
    assert wiki_dir.is_dir()
    assert layout.config_path.exists()
    assert layout.gitignore_path.exists()
    assert layout.notes_dir.is_dir()
    for section in SECTIONS:
        assert layout.section_path(section).exists()
    assert wiki_dir in paths
    assert layout.config_path in paths


def test_initialize_is_idempotent(tmp_path):
    layout = _layout(tmp_path)
    initialize(layout, model="m", provider="ollama", ollama_host="http://h")
    layout.config_path.write_text("# user-edited\n")
    initialize(layout, model="m", provider="ollama", ollama_host="http://h")
    assert layout.config_path.read_text() == "# user-edited\n"


def test_write_section_replaces_body(tmp_path):
    layout = _layout(tmp_path)
    initialize(layout, model="m", provider="ollama", ollama_host="http://h")
    section = SECTIONS[0]
    path = write_section(layout, section, "Hello world.")
    contents = path.read_text()
    assert contents.startswith(f"# {section.title}")
    assert "Hello world." in contents


def test_append_and_read_notes_round_trip(tmp_path):
    layout = _layout(tmp_path)
    initialize(layout, model="m", provider="ollama", ollama_host="http://h")
    section = SECTIONS[0]
    append_note(layout, section, {"file": "a.py", "finding": "first"})
    append_note(layout, section, {"file": "b.py", "finding": "second"})
    notes = read_notes(layout, section)
    assert [n["finding"] for n in notes] == ["first", "second"]
    assert all("timestamp" in n for n in notes)


def test_read_notes_missing_file_returns_empty(tmp_path):
    layout = _layout(tmp_path)
    initialize(layout, model="m", provider="ollama", ollama_host="http://h")
    assert read_notes(layout, SECTIONS[0]) == []


def test_reset_notes_clears_jsonl(tmp_path):
    layout = _layout(tmp_path)
    initialize(layout, model="m", provider="ollama", ollama_host="http://h")
    section = SECTIONS[0]
    append_note(layout, section, {"file": "a.py", "finding": "x"})
    reset_notes(layout)
    assert read_notes(layout, section) == []


def test_section_path_accepts_string_id(tmp_path):
    layout = _layout(tmp_path)
    section = SECTIONS[0]
    assert layout.section_path(section.id) == layout.section_path(section)


def test_reset_notes_no_op_if_dir_missing(tmp_path):
    # initialize() was never called; should not raise
    reset_notes(_layout(tmp_path))


def test_write_section_with_section_object(tmp_path):
    layout = _layout(tmp_path)
    initialize(layout, model="m", provider="ollama", ollama_host="http://h")
    section: Section = SECTIONS[1]
    body = "Some **bold** content."
    path = write_section(layout, section, body)
    assert section.title in path.read_text()


def test_initialize_gitignore_includes_cache_dir(tmp_path):
    """Fresh init must ignore both `.notes/` AND `.cache/`.

    The cache layer writes to `.wikifi/.cache/`; if the gitignore
    template misses it, every walk leaves untracked files in the
    target repo — exactly the noise the wiki contract promises to
    avoid.
    """
    from wikifi.wiki import CACHE_DIRNAME, NOTES_DIRNAME

    layout = _layout(tmp_path)
    initialize(layout, model="m", provider="ollama", ollama_host="http://h")
    contents = layout.gitignore_path.read_text()
    assert f"{NOTES_DIRNAME}/" in contents
    assert f"{CACHE_DIRNAME}/" in contents


def test_initialize_backfills_cache_into_legacy_gitignore(tmp_path):
    """An older wiki's `.gitignore` (only `.notes/`) gains `.cache/` on re-init.

    Wikis created before the cache layer landed have a `.gitignore`
    missing the new entry. Re-running `wikifi init` against them must
    append the missing line in place rather than leaving the older
    config silently incomplete.
    """
    from wikifi.wiki import CACHE_DIRNAME

    layout = _layout(tmp_path)
    layout.wiki_dir.mkdir(parents=True)
    # Simulate the pre-cache-era gitignore — comment + .notes/ only.
    legacy = "# wikifi local working state — section markdown is committed, notes are not.\n.notes/\n"
    layout.gitignore_path.write_text(legacy)

    initialize(layout, model="m", provider="ollama", ollama_host="http://h")

    contents = layout.gitignore_path.read_text()
    # The original line is preserved unchanged.
    assert ".notes/" in contents
    # The missing entry is appended.
    assert f"{CACHE_DIRNAME}/" in contents
    # No duplication on a second init.
    initialize(layout, model="m", provider="ollama", ollama_host="http://h")
    after_second = layout.gitignore_path.read_text()
    assert after_second.count(f"{CACHE_DIRNAME}/") == 1


def test_initialize_preserves_user_extra_lines_in_gitignore(tmp_path):
    """User-added entries in `.wikifi/.gitignore` survive re-init.

    Backfill must only *append* missing required entries — it must
    never rewrite, reorder, or strip lines the user added themselves
    (e.g. `local-notes/`, `*.draft`, etc.).
    """
    from wikifi.wiki import CACHE_DIRNAME

    layout = _layout(tmp_path)
    layout.wiki_dir.mkdir(parents=True)
    # User-customized: includes the standard .notes/ plus an extra entry,
    # but is missing the new .cache/ line.
    user_authored = "# my custom comment\n.notes/\nlocal-notes/\n*.draft\n"
    layout.gitignore_path.write_text(user_authored)

    initialize(layout, model="m", provider="ollama", ollama_host="http://h")
    contents = layout.gitignore_path.read_text()

    # User content unchanged.
    assert "# my custom comment" in contents
    assert "local-notes/" in contents
    assert "*.draft" in contents
    # Required entry appended.
    assert f"{CACHE_DIRNAME}/" in contents
