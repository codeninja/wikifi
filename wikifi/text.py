from __future__ import annotations

import re
from collections.abc import Iterable

IMPLEMENTATION_WORDS = {
    "argparse": "command interface",
    "dataclass": "structured record",
    "fastapi": "web interface",
    "flask": "web interface",
    "graphql": "query interface",
    "http": "network interface",
    "json": "structured data",
    "ollama": "local reasoning service",
    "pydantic": "validation layer",
    "pytest": "verification suite",
    "python": "source implementation",
    "react": "interactive interface",
    "requests": "network client",
    "sqlalchemy": "data persistence layer",
    "toml": "local configuration",
}


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def summarize_text(value: str, *, limit: int = 500) -> str:
    normalized = normalize_space(value)
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3].rstrip() + "..."


def bullet_list(items: Iterable[str], *, fallback: str) -> str:
    unique = dedupe(items)
    if not unique:
        return f"- {fallback}"
    return "\n".join(f"- {item}" for item in unique)


def markdown_table(headers: tuple[str, ...], rows: Iterable[tuple[str, ...]]) -> str:
    header = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(_clean_table_cell(cell) for cell in row) + " |" for row in rows]
    return "\n".join([header, separator, *body])


def dedupe(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = normalize_space(str(item))
        key = normalized.lower()
        if normalized and key not in seen:
            seen.add(key)
            result.append(normalized)
    return result


def domain_language(value: str) -> str:
    output = value
    for technical, replacement in IMPLEMENTATION_WORDS.items():
        output = re.sub(rf"\b{re.escape(technical)}\b", replacement, output, flags=re.IGNORECASE)
    return normalize_space(output)


def first_sentence(value: str) -> str:
    normalized = normalize_space(value)
    match = re.search(r"(?<=[.!?])\s+", normalized)
    if match:
        return normalized[: match.start()].strip()
    return normalized


def _clean_table_cell(value: str) -> str:
    return normalize_space(value).replace("|", "\\|")
