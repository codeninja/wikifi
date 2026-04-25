from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from wikifi.models import AggregationStats, ExtractionNote, PipelineResult, WorkspaceLayout
from wikifi.text import markdown_table


def write_notes(layout: WorkspaceLayout, notes: tuple[ExtractionNote, ...]) -> None:
    with layout.notes_file.open("w", encoding="utf-8") as handle:
        for note in notes:
            handle.write(json.dumps(asdict(note), sort_keys=True) + "\n")


def write_summary(result: PipelineResult) -> None:
    summary = result.as_summary()
    result.layout.summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    result.layout.summary_markdown.write_text(_summary_markdown(summary, result), encoding="utf-8")


def _summary_markdown(summary: dict[str, Any], result: PipelineResult) -> str:
    metric_rows = [
        ("Completion status", summary["completion_status"]),
        ("Provider status", summary["provider_status"]),
        ("Selected source files", str(summary["directory_summary"]["selected_file_count"])),
        ("Extraction notes", str(summary["extraction_note_count"])),
        ("Primary sections written", _stats_label(result.aggregation_stats)),
        ("Derivative sections written", _stats_label(result.derivative_stats)),
    ]
    stage_rows = [(stage, str(result.stage_metrics.get(stage, "completed"))) for stage in summary["stage_order"]]
    skipped_rows = [
        (reason, str(count)) for reason, count in sorted(summary["directory_summary"]["skipped_counts"].items())
    ] or [("None", "0")]
    return "\n\n".join(
        [
            "## Execution Summary",
            "",
            "Generated only after introspection, extraction, aggregation, and derivation completed.",
            "",
            "### Pipeline Health",
            markdown_table(("Metric", "Value"), metric_rows),
            "### Stage Metrics",
            markdown_table(("Stage", "Status"), stage_rows),
            "### Skipped Input Counts",
            markdown_table(("Reason", "Count"), skipped_rows),
            "### Output Readiness",
            _readiness_statement(result.aggregation_stats, result.derivative_stats),
            "",
        ]
    )


def _stats_label(stats: AggregationStats) -> str:
    return f"{stats.successful_writes}/{stats.attempted_sections} with {stats.empty_section_count} empty"


def _readiness_statement(primary: AggregationStats, derivative: AggregationStats) -> str:
    if primary.empty_section_count or derivative.empty_section_count:
        return "One or more sections were empty; review gap declarations before relying on the wiki."
    return "All configured primary and derivative sections were written with non-empty content."


def append_log(path: Path, message: str) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(message.rstrip() + "\n")
