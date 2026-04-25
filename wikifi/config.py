from __future__ import annotations

import os
import tomllib
from dataclasses import replace
from pathlib import Path
from typing import Any

from wikifi.models import Settings

ENV_KEYS = {
    "provider": "WIKIFI_PROVIDER",
    "model": "WIKIFI_MODEL",
    "ollama_host": "WIKIFI_OLLAMA_HOST",
    "request_timeout": "WIKIFI_REQUEST_TIMEOUT",
    "max_file_bytes": "WIKIFI_MAX_FILE_BYTES",
    "min_content_bytes": "WIKIFI_MIN_CONTENT_BYTES",
    "introspection_depth": "WIKIFI_INTROSPECTION_DEPTH",
    "think": "WIKIFI_THINK",
    "output_dir": "WIKIFI_OUTPUT_DIR",
    "allow_provider_fallback": "WIKIFI_ALLOW_PROVIDER_FALLBACK",
    "exclude_patterns": "WIKIFI_EXCLUDE_PATTERNS",
}

INT_FIELDS = {"request_timeout", "max_file_bytes", "min_content_bytes", "introspection_depth"}
BOOL_FIELDS = {"allow_provider_fallback"}
TUPLE_FIELDS = {"exclude_patterns"}


class ConfigError(ValueError):
    pass


def load_settings(root: Path | str) -> Settings:
    root_path = Path(root).resolve()
    settings = Settings()
    settings = _apply_values(settings, _read_env())

    local_path = root_path / settings.output_dir / "config.toml"
    if local_path.exists():
        settings = _apply_values(settings, _read_local_config(local_path))

    _validate_settings(settings)
    return settings


def _read_env() -> dict[str, Any]:
    values: dict[str, Any] = {}
    for field_name, env_name in ENV_KEYS.items():
        value = os.getenv(env_name)
        if value is not None and value != "":
            values[field_name] = value
    return values


def _read_local_config(path: Path) -> dict[str, Any]:
    try:
        parsed = tomllib.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"Unable to read local config at {path}: {exc}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Invalid local config at {path}: {exc}") from exc

    raw = parsed.get("wikifi", parsed)
    if not isinstance(raw, dict):
        raise ConfigError(f"Local config at {path} must contain a [wikifi] table or top-level keys.")
    return raw


def _apply_values(settings: Settings, values: dict[str, Any]) -> Settings:
    normalized: dict[str, Any] = {}
    valid_fields = settings.as_config().keys()
    for field_name, value in values.items():
        if field_name not in valid_fields:
            continue
        normalized[field_name] = _coerce(field_name, value)
    return replace(settings, **normalized)


def _coerce(field_name: str, value: Any) -> Any:
    if field_name in INT_FIELDS:
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise ConfigError(f"{field_name} must be an integer.") from exc
    if field_name in BOOL_FIELDS:
        if isinstance(value, bool):
            return value
        lowered = str(value).strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
        raise ConfigError(f"{field_name} must be a boolean.")
    if field_name in TUPLE_FIELDS:
        if isinstance(value, str):
            return tuple(item.strip() for item in value.split(",") if item.strip())
        if isinstance(value, list | tuple):
            return tuple(str(item).strip() for item in value if str(item).strip())
        raise ConfigError(f"{field_name} must be a list or comma-separated string.")
    return str(value).strip() if value is not None else ""


def _validate_settings(settings: Settings) -> None:
    if settings.request_timeout <= 0:
        raise ConfigError("request_timeout must be greater than zero.")
    if settings.max_file_bytes <= 0:
        raise ConfigError("max_file_bytes must be greater than zero.")
    if settings.min_content_bytes < 0:
        raise ConfigError("min_content_bytes must not be negative.")
    if settings.introspection_depth < 1:
        raise ConfigError("introspection_depth must be at least one.")
    if not settings.output_dir:
        raise ConfigError("output_dir must not be empty.")
