from __future__ import annotations

import pytest

from wikifi.config import ConfigError, load_settings


def test_local_config_overrides_environment(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    wiki_dir = tmp_path / ".wikifi"
    wiki_dir.mkdir()
    (wiki_dir / "config.toml").write_text(
        "\n".join(
            [
                "[wikifi]",
                'provider = "ollama"',
                'model = "local-model"',
                "max_file_bytes = 123",
                "allow_provider_fallback = false",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("WIKIFI_PROVIDER", "openai")
    monkeypatch.setenv("WIKIFI_MODEL", "cloud-model")
    monkeypatch.setenv("WIKIFI_MAX_FILE_BYTES", "999")
    monkeypatch.setenv("WIKIFI_ALLOW_PROVIDER_FALLBACK", "true")

    settings = load_settings(tmp_path)

    assert settings.provider == "ollama"
    assert settings.model == "local-model"
    assert settings.max_file_bytes == 123
    assert settings.allow_provider_fallback is False


def test_invalid_integer_config_fails_gracefully(tmp_path) -> None:
    wiki_dir = tmp_path / ".wikifi"
    wiki_dir.mkdir()
    (wiki_dir / "config.toml").write_text(
        '[wikifi]\nrequest_timeout = "slow"\n',
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="request_timeout must be an integer"):
        load_settings(tmp_path)
