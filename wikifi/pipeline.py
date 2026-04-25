"""Top-level orchestration — runs the four stages in their immutable order."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

from wikifi.aggregation import aggregate
from wikifi.config import Settings, load_settings
from wikifi.derivation import derive
from wikifi.extraction import extract_all
from wikifi.factory import build_provider
from wikifi.introspection import introspect
from wikifi.providers.base import Provider
from wikifi.schemas import ExecutionSummary
from wikifi.workspace import provision_workspace, reset_notes

log = logging.getLogger(__name__)


def run_walk(
    target: Path,
    *,
    settings: Settings | None = None,
    provider: Provider | None = None,
    keep_notes: bool = False,
) -> ExecutionSummary:
    """Execute the full pipeline against ``target`` and return the summary.

    The four stages run sequentially: introspection → extraction →
    aggregation → derivation. Each stage owns its own degradation
    behaviour; the pipeline never halts on a single-file failure.
    """
    settings = settings or load_settings(target)
    provider = provider or build_provider(settings)

    started_at = datetime.now(UTC)
    log.info(
        "wikifi walk → target=%s provider=%s model=%s think=%s",
        target,
        provider.name,
        settings.model,
        settings.think,
    )

    # Probe the provider once before doing real work so misconfiguration
    # surfaces immediately.
    provider.healthcheck()

    workspace = provision_workspace(target, wiki_dir_name=settings.wiki_dir_name)
    if not keep_notes:
        cleared = reset_notes(workspace)
        if cleared:
            log.info("Cleared %d stale extraction notes", cleared)

    scan_report, _summary, assessment = introspect(
        root=workspace.root,
        settings=settings,
        provider=provider,
    )

    extraction_stats = extract_all(
        workspace=workspace,
        scan_report=scan_report,
        assessment=assessment,
        settings=settings,
        provider=provider,
    )

    aggregation_stats = aggregate(
        workspace=workspace,
        assessment=assessment,
        settings=settings,
        provider=provider,
    )

    derivation_stats = derive(
        workspace=workspace,
        settings=settings,
        provider=provider,
    )

    finished_at = datetime.now(UTC)

    notes: list[str] = []
    if assessment.classification_rationale:
        notes.append(f"introspection: {assessment.classification_rationale}")
    if extraction_stats.failure_paths:
        notes.append("extraction failures: " + ", ".join(extraction_stats.failure_paths[:10]))
    if aggregation_stats.failed_sections:
        notes.append("aggregation failures: " + ", ".join(aggregation_stats.failed_sections))
    if derivation_stats.failed_sections:
        notes.append("derivation failures: " + ", ".join(derivation_stats.failed_sections))

    summary = ExecutionSummary(
        started_at=started_at,
        finished_at=finished_at,
        target_path=str(workspace.root),
        files_seen=scan_report.files_seen,
        files_in_scope=len(scan_report.in_scope),
        files_skipped_min_bytes=len(scan_report.skipped_min_bytes),
        files_skipped_excluded=len(scan_report.skipped_excluded),
        files_truncated=extraction_stats.truncated,
        extraction_notes_written=extraction_stats.notes_written,
        extraction_failures=extraction_stats.failures,
        primary_sections_written=aggregation_stats.successful_writes,
        primary_sections_empty=list(aggregation_stats.empty_sections),
        derivative_sections_written=derivation_stats.successful_writes,
        derivative_sections_empty=list(derivation_stats.empty_sections),
        provider=provider.name,
        model=settings.model,
        think=str(settings.think),
        notes=notes,
    )

    write_execution_summary(workspace.execution_summary, summary)
    return summary


def write_execution_summary(path: Path, summary: ExecutionSummary) -> None:
    """Render the summary as markdown — checked-in alongside the sections."""
    duration = (summary.finished_at - summary.started_at).total_seconds()
    notes_block = "\n".join(f"- {n}" for n in summary.notes) if summary.notes else "- (none)"
    primary_empty = ", ".join(summary.primary_sections_empty) or "(none)"
    derivative_empty = ", ".join(summary.derivative_sections_empty) or "(none)"
    body = f"""## Execution Summary

### Run
- target: `{summary.target_path}`
- started: `{summary.started_at.isoformat()}`
- finished: `{summary.finished_at.isoformat()}`
- duration_seconds: `{duration:.1f}`
- provider: `{summary.provider}`
- model: `{summary.model}`
- think: `{summary.think}`

### File Inclusion
| Metric | Count |
|---|---|
| files_seen | {summary.files_seen} |
| files_in_scope | {summary.files_in_scope} |
| files_skipped_excluded | {summary.files_skipped_excluded} |
| files_skipped_min_bytes | {summary.files_skipped_min_bytes} |
| files_truncated | {summary.files_truncated} |

### Stage Outcomes
| Stage | Result |
|---|---|
| extraction_notes_written | {summary.extraction_notes_written} |
| extraction_failures | {summary.extraction_failures} |
| primary_sections_written | {summary.primary_sections_written} |
| primary_sections_empty | {primary_empty} |
| derivative_sections_written | {summary.derivative_sections_written} |
| derivative_sections_empty | {derivative_empty} |

### Notes
{notes_block}
"""
    path.write_text(body, encoding="utf-8")
