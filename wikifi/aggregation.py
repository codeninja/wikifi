"""Stage 3: aggregation — synthesize markdown sections from extraction notes."""

from __future__ import annotations

import logging
from pathlib import Path

from wikifi.config import Settings
from wikifi.llm_io import request_text, strip_top_level_heading
from wikifi.notes_store import group_by_section, load_notes
from wikifi.prompts import (
    AGGREGATION_SYSTEM,
    AGGREGATION_USER,
    SECTION_GUIDANCE,
    SYSTEM_BASE,
)
from wikifi.providers.base import Provider, ProviderError
from wikifi.schemas import (
    PRIMARY_SECTIONS,
    AggregationStats,
    ExtractionNote,
    IntrospectionAssessment,
)
from wikifi.workspace import Workspace

log = logging.getLogger(__name__)

GAP_TEMPLATE = """## {title}

### Documented Gaps
The available evidence in this repository does not contain enough material to
synthesize this section. No extraction notes were assigned to this category
during the granular extraction stage.
"""


def _format_notes_block(items: list[tuple[ExtractionNote, str]], *, max_chars: int = 16_000) -> str:
    """Render the per-section notes into a stable, bounded prompt block."""
    lines: list[str] = []
    used = 0
    for note, finding in items:
        entry = f"- file: {note.file_reference}\n  role: {note.role_summary.strip()}\n  finding: {finding.strip()}\n"
        if used + len(entry) > max_chars:
            lines.append("- ... (additional notes omitted to keep the prompt bounded)")
            break
        lines.append(entry)
        used += len(entry)
    return "\n".join(lines) if lines else "(no notes assigned to this section)"


def _section_title(section_id: str) -> str:
    titles = {
        "intent": "Intent and Problem Space",
        "capabilities": "Capabilities",
        "domains": "Domains and Subdomains",
        "entities": "Core Entities",
        "integrations": "Integrations",
        "external_dependencies": "External-System Dependencies",
        "cross_cutting": "Cross-Cutting Concerns",
        "hard_specifications": "Hard Specifications",
    }
    return titles.get(section_id, section_id.replace("_", " ").title())


def aggregate(
    *,
    workspace: Workspace,
    assessment: IntrospectionAssessment,
    settings: Settings,
    provider: Provider,
) -> AggregationStats:
    """Synthesize one markdown file per primary section."""
    log.info("Stage 3: aggregation — synthesizing %d primary sections", len(PRIMARY_SECTIONS))

    notes = load_notes(workspace.notes_dir)
    grouped = group_by_section(notes)

    stats = AggregationStats()
    purpose = assessment.inferred_purpose or "(purpose not established)"

    for section_id in PRIMARY_SECTIONS:
        bucket = grouped.get(section_id, [])
        title = _section_title(section_id)
        out_path = workspace.section_path(section_id)

        if not bucket:
            log.warning("Section '%s' has no extraction notes — writing gap stanza.", section_id)
            out_path.write_text(GAP_TEMPLATE.format(title=title), encoding="utf-8")
            stats.empty_sections.append(section_id)
            continue

        notes_block = _format_notes_block(bucket)
        prompt = AGGREGATION_USER.format(
            section_id=section_id,
            guidance=SECTION_GUIDANCE.get(section_id, "Synthesize this section."),
            purpose=purpose,
            notes_block=notes_block,
        )

        system_prompt = AGGREGATION_SYSTEM.format(base=SYSTEM_BASE)

        try:
            body = request_text(
                provider,
                prompt=prompt,
                system=system_prompt,
                think=settings.think_payload(),
                temperature=0.2,
            )
        except ProviderError as exc:
            stats.failed_sections.append(section_id)
            log.error("Section '%s' synthesis failed: %s", section_id, exc)
            _write_failure_stanza(out_path, title=title, reason=str(exc))
            continue

        body = strip_top_level_heading(body)
        if not body.strip():
            stats.empty_sections.append(section_id)
            out_path.write_text(GAP_TEMPLATE.format(title=title), encoding="utf-8")
            continue

        out_path.write_text(body, encoding="utf-8")
        stats.successful_writes += 1
        log.info("Section '%s' written (%d chars)", section_id, len(body))

    return stats


def _write_failure_stanza(path: Path, *, title: str, reason: str) -> None:
    path.write_text(
        f"""## {title}

### Documented Gaps
Synthesis of this section did not complete during the most recent run.
Reason captured by the orchestrator:

```
{reason}
```

Re-run the walk to attempt synthesis again. The intermediate extraction
notes that would inform this section remain available under
``.wikifi/.notes/`` for inspection.
""",
        encoding="utf-8",
    )
