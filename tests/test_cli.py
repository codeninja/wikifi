from __future__ import annotations

from wikifi.cli import main


def test_init_command_creates_workspace(tmp_path) -> None:
    code = main(["init", str(tmp_path)])

    assert code == 0
    assert (tmp_path / ".wikifi" / "config.toml").exists()
    assert (tmp_path / ".wikifi" / "sections" / "domains.md").exists()
    assert (tmp_path / ".wikifi" / "derivatives" / "user_stories.md").exists()
    assert "/notes/" in (tmp_path / ".wikifi" / ".gitignore").read_text(encoding="utf-8")


def test_unsupported_provider_returns_clear_error(tmp_path, capsys) -> None:
    wiki_dir = tmp_path / ".wikifi"
    wiki_dir.mkdir()
    (wiki_dir / "config.toml").write_text('[wikifi]\nprovider = "openai"\n', encoding="utf-8")

    code = main(["walk", str(tmp_path)])

    captured = capsys.readouterr()
    assert code == 2
    assert "Unsupported provider 'openai'" in captured.err
