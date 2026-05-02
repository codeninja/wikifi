from wikifi.config import Settings, get_settings


def test_defaults():
    s = Settings(_env_file=None)
    assert s.provider == "ollama"
    assert s.model == "qwen3.6:27b"
    assert s.ollama_host.startswith("http")


def test_env_override(monkeypatch):
    monkeypatch.setenv("WIKIFI_MODEL", "gemma4:latest")
    monkeypatch.setenv("WIKIFI_OLLAMA_HOST", "http://otherhost:11434")
    s = Settings(_env_file=None)
    assert s.model == "gemma4:latest"
    assert s.ollama_host == "http://otherhost:11434"


def test_get_settings_is_cached():
    a = get_settings()
    b = get_settings()
    assert a is b


def test_load_target_settings_reads_config_toml(tmp_path, monkeypatch):
    """`<target>/.wikifi/config.toml` overrides field defaults.

    A target wiki initialized with `provider = "anthropic"` should
    produce settings that say "anthropic" even when the calling shell
    has no WIKIFI_* env vars set.
    """
    from wikifi.config import load_target_settings, reset_settings_cache

    # ``Settings`` reads ``.env`` from CWD; chdir to tmp_path so the
    # project-root .env (which sets WIKIFI_PROVIDER=anthropic) doesn't
    # leak into the test.
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("WIKIFI_PROVIDER", raising=False)
    monkeypatch.delenv("WIKIFI_MODEL", raising=False)
    monkeypatch.delenv("WIKIFI_OLLAMA_HOST", raising=False)
    reset_settings_cache()

    wiki_dir = tmp_path / ".wikifi"
    wiki_dir.mkdir()
    (wiki_dir / "config.toml").write_text(
        'provider = "anthropic"\nmodel = "claude-opus-4-7"\nollama_host = "http://unused:11434"\n'
    )

    settings = load_target_settings(tmp_path)
    assert settings.provider == "anthropic"
    assert settings.model == "claude-opus-4-7"
    reset_settings_cache()


def test_load_target_settings_toml_wins_over_env(tmp_path, monkeypatch):
    """The target wiki's `config.toml` wins over per-session env vars.

    Matches the contract printed at the top of every scaffolded
    `config.toml`: "overrides WIKIFI_* environment variables when
    present". A wiki initialized for a hosted backend should keep
    using that backend even if the user happens to have
    `WIKIFI_PROVIDER=ollama` exported in their shell.
    """
    from wikifi.config import load_target_settings, reset_settings_cache

    monkeypatch.setenv("WIKIFI_PROVIDER", "ollama")
    monkeypatch.setenv("WIKIFI_MODEL", "qwen3.6:27b")
    reset_settings_cache()

    wiki_dir = tmp_path / ".wikifi"
    wiki_dir.mkdir()
    (wiki_dir / "config.toml").write_text(
        'provider = "anthropic"\nmodel = "claude-opus-4-7"\n',
    )

    settings = load_target_settings(tmp_path)
    assert settings.provider == "anthropic"
    assert settings.model == "claude-opus-4-7"
    reset_settings_cache()


def test_load_target_settings_handles_missing_config(tmp_path, monkeypatch):
    """No `.wikifi/config.toml` → fall back cleanly to env defaults."""
    from wikifi.config import load_target_settings, reset_settings_cache

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("WIKIFI_PROVIDER", raising=False)
    monkeypatch.delenv("WIKIFI_MODEL", raising=False)
    reset_settings_cache()

    settings = load_target_settings(tmp_path)
    assert settings.provider == "ollama"
    reset_settings_cache()


def test_load_target_settings_ignores_malformed_toml(tmp_path, monkeypatch, caplog):
    """A corrupt config.toml warns and falls back instead of raising."""
    import logging

    from wikifi.config import load_target_settings, reset_settings_cache

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("WIKIFI_PROVIDER", raising=False)
    reset_settings_cache()

    wiki_dir = tmp_path / ".wikifi"
    wiki_dir.mkdir()
    (wiki_dir / "config.toml").write_text("not = valid = toml = at all\n")

    with caplog.at_level(logging.WARNING, logger="wikifi.config"):
        settings = load_target_settings(tmp_path)

    assert settings.provider == "ollama"
    assert any("could not read" in record.message for record in caplog.records)
    reset_settings_cache()
