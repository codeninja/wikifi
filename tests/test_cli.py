from typer.testing import CliRunner

from wikifi import __version__
from wikifi.cli import app
from wikifi.wiki import WikiLayout, initialize, write_section


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


def test_chat_command_is_registered():
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "chat" in result.output


def test_chat_command_errors_when_wiki_missing(tmp_path):
    runner = CliRunner()
    result = runner.invoke(app, ["chat", str(tmp_path)])
    assert result.exit_code == 1
    assert "No .wikifi/" in result.output


def test_report_command_errors_when_wiki_missing(tmp_path):
    runner = CliRunner()
    result = runner.invoke(app, ["report", str(tmp_path)])
    assert result.exit_code == 1
    assert "No .wikifi/" in result.output


def test_report_command_renders_table(tmp_path):
    layout = WikiLayout(root=tmp_path)
    initialize(layout, model="m", provider="ollama", ollama_host="http://h")
    write_section(layout, "intent", "Some intent body.")

    runner = CliRunner()
    result = runner.invoke(app, ["report", str(tmp_path)])
    assert result.exit_code == 0, result.output
    # Markdown rendered through rich; check for the header text.
    assert "wikifi coverage" in result.output.lower() or "section" in result.output.lower()


def test_walk_no_cache_flag_clears_cache_dir(tmp_path, monkeypatch):
    """`walk --no-cache` triggers the cache-reset path before the run starts."""
    layout = WikiLayout(root=tmp_path)
    initialize(layout, model="m", provider="ollama", ollama_host="http://h")
    cache_path = layout.wiki_dir / ".cache" / "extraction.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text('{"version": 1, "entries": {}}')

    captured = {}

    def fake_run_walk(*, root, settings, provider=None):
        captured["use_cache"] = settings.use_cache
        from wikifi.aggregator import AggregationStats
        from wikifi.deriver import DerivationStats
        from wikifi.extractor import ExtractionStats
        from wikifi.introspection import IntrospectionResult
        from wikifi.orchestrator import WalkReport

        return WalkReport(
            introspection=IntrospectionResult(),
            extraction=ExtractionStats(),
            aggregation=AggregationStats(),
            derivation=DerivationStats(),
        )

    monkeypatch.setattr("wikifi.cli.run_walk", fake_run_walk)
    runner = CliRunner()
    result = runner.invoke(app, ["walk", str(tmp_path), "--no-cache"])
    assert result.exit_code == 0, result.output
    assert captured["use_cache"] is False
    # Cache file was deleted by the flag.
    assert not cache_path.exists()


def test_chat_command_runs_repl(tmp_path, monkeypatch):
    layout = WikiLayout(root=tmp_path)
    initialize(layout, model="m", provider="ollama", ollama_host="http://h")
    layout.section_path("intent").write_text("# intent\n\nhello body\n")

    captured: dict = {}

    def fake_run_repl(*, layout, provider, console):
        captured["layout"] = layout
        captured["provider"] = provider

    fake_provider = object()
    monkeypatch.setattr("wikifi.cli.run_repl", fake_run_repl)
    monkeypatch.setattr("wikifi.cli.build_provider", lambda _settings: fake_provider)

    runner = CliRunner()
    result = runner.invoke(app, ["chat", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert captured["layout"].root == tmp_path
    assert captured["provider"] is fake_provider
