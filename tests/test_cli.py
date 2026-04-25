"""CLI smoke tests using Click's CliRunner."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from wikifi.cli import cli


def test_version():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "wikifi" in result.output


def test_init_provisions_workspace(sample_repo: Path):
    runner = CliRunner()
    result = runner.invoke(cli, ["init", "--target", str(sample_repo)])
    assert result.exit_code == 0, result.output
    assert (sample_repo / ".wikifi").is_dir()
    assert (sample_repo / ".wikifi" / ".notes").is_dir()


def test_config_dumps_json(sample_repo: Path):
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "--target", str(sample_repo)])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["model"]
    assert payload["provider"] in {"ollama", "fake"}


def test_walk_propagates_provider_error(monkeypatch, sample_repo: Path):
    runner = CliRunner()

    from wikifi.providers.base import ProviderError

    def _explode(_settings):
        raise ProviderError("misconfigured")

    monkeypatch.setattr("wikifi.cli.build_provider", _explode)
    result = runner.invoke(cli, ["walk", "--target", str(sample_repo)])
    assert result.exit_code == 2
    assert "misconfigured" in result.output
