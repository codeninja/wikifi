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
