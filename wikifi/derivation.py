"""Stage 4: derivation — personas, user stories, diagrams from the aggregate."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from wikifi.config import Settings
from wikifi.llm_io import request_text, strip_top_level_heading
from wikifi.prompts import (
    AGGREGATION_SYSTEM,
    DIAGRAMS_USER,
    PERSONAS_USER,
    SYSTEM_BASE,
    USER_STORIES_USER,
)
from wikifi.providers.base import Provider, ProviderError
from wikifi.schemas import PRIMARY_SECTIONS
from wikifi.workspace import Workspace

log = logging.getLogger(__name__)


@dataclass(slots=True)
class DerivationStats:
    successful_writes: int = 0
    empty_sections: list[str] = field(default_factory=list)
    failed_sections: list[str] = field(default_factory=list)


def _read_primary_block(workspace: Workspace, *, max_chars: int = 24_000) -> str:
    """Concatenate primary section markdown for the derivative prompts."""
    parts: list[str] = []
    used = 0
    for section in PRIMARY_SECTIONS:
        path = workspace.section_path(section)
        if not path.is_file():
            continue
        body = path.read_text(encoding="utf-8")
        chunk = f"\n\n--- {section} ---\n\n{body}"
        if used + len(chunk) > max_chars:
            parts.append(f"\n\n--- {section} ---\n\n(omitted — prompt budget reached)")
            break
        parts.append(chunk)
        used += len(chunk)
    return "".join(parts) if parts else "(no primary sections available)"


def _read_personas(workspace: Workspace) -> str:
    path = workspace.section_path("personas")
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return "(personas not yet derived)"


def _write_section(
    *,
    out_path: Path,
    body: str,
    title: str,
    stats: DerivationStats,
    section_id: str,
) -> None:
    cleaned = strip_top_level_heading(body)
    if not cleaned.strip():
        stats.empty_sections.append(section_id)
        out_path.write_text(
            f"## {title}\n\n### Documented Gaps\nDerivation produced no content for this section.\n",
            encoding="utf-8",
        )
        return
    out_path.write_text(cleaned, encoding="utf-8")
    stats.successful_writes += 1


def derive(
    *,
    workspace: Workspace,
    settings: Settings,
    provider: Provider,
) -> DerivationStats:
    """Run the three derivative passes in dependency order."""
    log.info("Stage 4: derivation — personas, user_stories, diagrams")
    stats = DerivationStats()
    primary_block = _read_primary_block(workspace)
    system_prompt = AGGREGATION_SYSTEM.format(base=SYSTEM_BASE)

    # Personas first — user stories cite them.
    try:
        personas_body = request_text(
            provider,
            prompt=PERSONAS_USER.format(primary_block=primary_block),
            system=system_prompt,
            think=settings.think_payload(),
            temperature=0.2,
        )
        _write_section(
            out_path=workspace.section_path("personas"),
            body=personas_body,
            title="User Personas",
            stats=stats,
            section_id="personas",
        )
    except ProviderError as exc:
        log.error("Personas derivation failed: %s", exc)
        stats.failed_sections.append("personas")
        _write_failure_stanza(workspace.section_path("personas"), title="User Personas", reason=str(exc))

    personas_block = _read_personas(workspace)

    try:
        stories_body = request_text(
            provider,
            prompt=USER_STORIES_USER.format(
                primary_block=primary_block,
                personas_block=personas_block,
            ),
            system=system_prompt,
            think=settings.think_payload(),
            temperature=0.2,
        )
        _write_section(
            out_path=workspace.section_path("user_stories"),
            body=stories_body,
            title="User Stories",
            stats=stats,
            section_id="user_stories",
        )
    except ProviderError as exc:
        log.error("User-stories derivation failed: %s", exc)
        stats.failed_sections.append("user_stories")
        _write_failure_stanza(workspace.section_path("user_stories"), title="User Stories", reason=str(exc))

    try:
        diagrams_body = request_text(
            provider,
            prompt=DIAGRAMS_USER.format(primary_block=primary_block),
            system=system_prompt,
            think=settings.think_payload(),
            temperature=0.2,
        )
        _write_section(
            out_path=workspace.section_path("diagrams"),
            body=diagrams_body,
            title="Diagrams",
            stats=stats,
            section_id="diagrams",
        )
    except ProviderError as exc:
        log.error("Diagrams derivation failed: %s", exc)
        stats.failed_sections.append("diagrams")
        _write_failure_stanza(workspace.section_path("diagrams"), title="Diagrams", reason=str(exc))

    return stats


def _write_failure_stanza(path: Path, *, title: str, reason: str) -> None:
    path.write_text(
        f"""## {title}

### Documented Gaps
Derivation of this section did not complete during the most recent run.
Reason captured by the orchestrator:

```
{reason}
```
""",
        encoding="utf-8",
    )
