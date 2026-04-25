from __future__ import annotations

from pathlib import Path

from wikifi.config import Settings, load_settings


def test_defaults_match_env_example():
    s = Settings()
    assert s.provider == "ollama"
    assert s.model.startswith("qwen3.6")
    assert s.max_file_bytes == 200_000
    assert s.min_content_bytes == 64
    assert s.think == "high"


def test_think_payload_translates():
    assert Settings(think="high").think_payload() == "high"
    assert Settings(think="true").think_payload() is True
    assert Settings(think="false").think_payload() is False


def test_load_settings_uses_target_env(tmp_path: Path, monkeypatch):
    # Ensure env doesn't leak into the test
    for key in ("WIKIFI_MODEL", "WIKIFI_PROVIDER", "WIKIFI_THINK"):
        monkeypatch.delenv(key, raising=False)
    (tmp_path / ".env").write_text("WIKIFI_MODEL=mock-model\nWIKIFI_THINK=low\n", encoding="utf-8")
    s = load_settings(tmp_path)
    assert s.model == "mock-model"
    assert s.think == "low"


def test_load_settings_no_env_file(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("WIKIFI_MODEL", raising=False)
    s = load_settings(tmp_path)
    assert s.model.startswith("qwen3.6")
