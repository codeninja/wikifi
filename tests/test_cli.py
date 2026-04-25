from typer.testing import CliRunner

from wikifi import __version__
from wikifi.cli import app


def test_version_flag():
    runner = CliRunner()
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_init_creates_wiki_skeleton(tmp_path):
    runner = CliRunner()
    result = runner.invoke(app, ["init", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert (tmp_path / ".wikifi" / "config.toml").exists()
    assert (tmp_path / ".wikifi" / "personas.md").exists()


def test_init_rejects_missing_target(tmp_path):
    runner = CliRunner()
    missing = tmp_path / "ghost"
    result = runner.invoke(app, ["init", str(missing)])
    assert result.exit_code != 0


def test_no_subcommand_shows_help():
    runner = CliRunner()
    result = runner.invoke(app, [])
    # Click's no_args_is_help convention is exit 2 with usage on stderr/stdout.
    assert result.exit_code == 2
    assert "wikifi" in result.output.lower() or "Usage" in result.output
