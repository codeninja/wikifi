from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Any

from wikifi.aggregation import aggregate_sections
from wikifi.config import ConfigError, load_settings
from wikifi.constants import STAGE_ORDER
from wikifi.derivation import derive_sections
from wikifi.extraction import extract_notes
from wikifi.introspection import assess_repository
from wikifi.models import PipelineResult, utc_now
from wikifi.providers import UnsupportedProviderError, build_provider
from wikifi.reporting import append_log, write_notes, write_summary
from wikifi.traversal import discover_source_files
from wikifi.workspace import ensure_workspace, reset_intermediate, write_workspace_readme


class PipelineError(RuntimeError):
    pass


def init_workspace(root: Path, *, force_config: bool = False) -> Path:
    root = root.resolve()
    settings = load_settings(root)
    layout = ensure_workspace(root, settings, force_config=force_config)
    write_workspace_readme(layout)
    return layout.wiki_dir


def walk(root: Path) -> PipelineResult:
    root = root.resolve()
    if not root.exists() or not root.is_dir():
        raise PipelineError(f"Target root does not exist or is not a directory: {root}")

    started_at = utc_now()
    settings = load_settings(root)
    layout = ensure_workspace(root, settings)
    write_workspace_readme(layout)
    reset_intermediate(layout)

    stage_metrics: dict[str, Any] = {"stage_order": list(STAGE_ORDER)}
    append_log(layout.run_log, f"started_at={started_at}")

    provider = build_provider(settings)

    start = perf_counter()
    directory_summary, sources, skipped = discover_source_files(root, settings)
    assessment = assess_repository(root, directory_summary, sources)
    stage_metrics["introspection"] = {
        "duration_seconds": round(perf_counter() - start, 4),
        "selected_file_count": len(sources),
        "skipped_file_count": len(skipped),
    }
    append_log(layout.run_log, "stage=introspection status=completed")

    start = perf_counter()
    notes, provider_status = extract_notes(
        sources,
        assessment,
        provider,
        allow_fallback=settings.allow_provider_fallback,
    )
    write_notes(layout, notes)
    stage_metrics["extraction"] = {
        "duration_seconds": round(perf_counter() - start, 4),
        "note_count": len(notes),
        "provider_status": provider_status,
    }
    append_log(layout.run_log, "stage=extraction status=completed")

    start = perf_counter()
    aggregation_stats = aggregate_sections(layout, directory_summary, assessment, notes)
    stage_metrics["aggregation"] = {
        "duration_seconds": round(perf_counter() - start, 4),
        "successful_writes": aggregation_stats.successful_writes,
        "empty_section_count": aggregation_stats.empty_section_count,
    }
    append_log(layout.run_log, "stage=aggregation status=completed")

    start = perf_counter()
    derivative_stats = derive_sections(layout, assessment, notes)
    stage_metrics["derivation"] = {
        "duration_seconds": round(perf_counter() - start, 4),
        "successful_writes": derivative_stats.successful_writes,
        "empty_section_count": derivative_stats.empty_section_count,
    }
    append_log(layout.run_log, "stage=derivation status=completed")

    finished_at = utc_now()
    result = PipelineResult(
        layout=layout,
        directory_summary=directory_summary,
        assessment=assessment,
        notes=notes,
        aggregation_stats=aggregation_stats,
        derivative_stats=derivative_stats,
        completion_status="completed",
        provider_status=provider_status,
        stage_metrics=stage_metrics,
        started_at=started_at,
        finished_at=finished_at,
    )
    write_summary(result)
    append_log(layout.run_log, f"finished_at={finished_at}")
    return result


def explain_error(exc: Exception) -> tuple[int, str]:
    if isinstance(exc, UnsupportedProviderError):
        return 2, str(exc)
    if isinstance(exc, ConfigError):
        return 2, str(exc)
    if isinstance(exc, PipelineError):
        return 1, str(exc)
    return 1, f"wikifi failed: {exc}"
