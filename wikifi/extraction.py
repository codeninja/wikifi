"""Stage 2: extraction — turn each in-scope file into a structured note."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from wikifi.config import Settings
from wikifi.filters import ScanReport
from wikifi.llm_io import request_structured
from wikifi.notes_store import write_note
from wikifi.prompts import EXTRACTION_USER, SYSTEM_BASE
from wikifi.providers.base import Provider, ProviderError
from wikifi.schemas import (
    ExtractionNote,
    ExtractionPayload,
    IntrospectionAssessment,
)
from wikifi.workspace import Workspace

log = logging.getLogger(__name__)


@dataclass(slots=True)
class ExtractionStats:
    notes_written: int = 0
    failures: int = 0
    truncated: int = 0
    skipped_by_model: int = 0
    failure_paths: list[str] = field(default_factory=list)


def _read_truncated(path: Path, max_bytes: int) -> tuple[str, bool]:
    """Read up to ``max_bytes`` of UTF-8 text. Returns (text, was_truncated)."""
    try:
        with path.open("rb") as fh:
            raw = fh.read(max_bytes + 1)
    except OSError:
        return "", False
    truncated = len(raw) > max_bytes
    if truncated:
        raw = raw[:max_bytes]
    try:
        text = raw.decode("utf-8", errors="replace")
    except UnicodeDecodeError:
        text = raw.decode("latin-1", errors="replace")
    return text, truncated


def extract_all(
    *,
    workspace: Workspace,
    scan_report: ScanReport,
    assessment: IntrospectionAssessment,
    settings: Settings,
    provider: Provider,
) -> ExtractionStats:
    """Process every in-scope file and persist a note per file."""
    log.info("Stage 2: extraction — %d files in scope", len(scan_report.in_scope))
    stats = ExtractionStats()

    purpose = assessment.inferred_purpose or "(purpose not yet established)"

    for index, rel in enumerate(scan_report.in_scope, start=1):
        absolute = workspace.root / rel
        text, truncated = _read_truncated(absolute, settings.max_file_bytes)
        if truncated:
            stats.truncated += 1
        if not text.strip():
            log.debug("Skipping %s — empty after read", rel)
            continue

        prompt = EXTRACTION_USER.format(
            path=rel.as_posix(),
            purpose=purpose,
            max_bytes=settings.max_file_bytes,
            content=text,
        )

        try:
            payload = request_structured(
                provider,
                prompt=prompt,
                system=SYSTEM_BASE,
                model_cls=ExtractionPayload,
                think=settings.think_payload(),
            )
        except ProviderError as exc:
            stats.failures += 1
            stats.failure_paths.append(rel.as_posix())
            log.warning(
                "[%d/%d] extraction failed for %s: %s",
                index,
                len(scan_report.in_scope),
                rel,
                exc,
            )
            continue

        note = ExtractionNote.now(
            file_reference=rel.as_posix(),
            payload=payload if isinstance(payload, ExtractionPayload) else ExtractionPayload.model_validate(payload),
        )
        if note.skip_reason and not note.findings:
            stats.skipped_by_model += 1
        write_note(workspace.notes_dir, note)
        stats.notes_written += 1
        log.info(
            "[%d/%d] note saved for %s (%d findings%s)",
            index,
            len(scan_report.in_scope),
            rel,
            len(note.findings),
            ", skipped" if note.skip_reason else "",
        )

    log.info(
        "Extraction complete: %d notes, %d failures, %d truncated, %d model-skipped",
        stats.notes_written,
        stats.failures,
        stats.truncated,
        stats.skipped_by_model,
    )
    return stats
