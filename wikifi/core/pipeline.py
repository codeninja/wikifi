from typing import Any, Dict

from rich.console import Console

from wikifi.config import get_settings
from wikifi.core.aggregation import run_aggregation
from wikifi.core.derivation import run_derivation
from wikifi.core.extraction import run_extraction
from wikifi.core.traversal import run_introspection
from wikifi.models import ExecutionSummary

console = Console()


class Orchestrator:
    def __init__(self):
        self.settings = get_settings()

    def run(self) -> ExecutionSummary:
        stage_metrics: Dict[str, Any] = {}

        # 1. Introspection
        console.print("[bold green]Starting Introspection...[/bold green]")
        valid_files, summary, assessment = run_introspection()
        stage_metrics["introspection"] = {
            "file_count": summary.file_count,
            "total_size": summary.total_size,
            "manifest_presence": summary.manifest_presence,
            "primary_languages": assessment.primary_languages,
            "inferred_purpose": assessment.inferred_purpose,
        }

        if not valid_files:
            console.print("[yellow]No valid files found for extraction. Halting.[/yellow]")
            return ExecutionSummary(
                stage_metrics=stage_metrics,
                completion_status="halted",
                consolidated_findings="No valid files to process.",
            )

        # 2. Extraction
        console.print("[bold green]Starting Extraction...[/bold green]")
        notes = run_extraction(valid_files)
        stage_metrics["extraction"] = {"notes_extracted": len(notes)}

        if not notes:
            console.print("[yellow]No notes extracted. Halting.[/yellow]")
            return ExecutionSummary(
                stage_metrics=stage_metrics, completion_status="halted", consolidated_findings="No notes extracted."
            )

        # 3. Aggregation
        console.print("[bold green]Starting Aggregation...[/bold green]")
        sections, agg_stats = run_aggregation(notes)
        stage_metrics["aggregation"] = {
            "successful_writes": agg_stats.successful_writes,
            "empty_section_count": agg_stats.empty_section_count,
        }

        # 4. Derivation
        console.print("[bold green]Starting Derivation...[/bold green]")
        run_derivation(sections)
        stage_metrics["derivation"] = {"completed": True}

        console.print("[bold green]Pipeline Complete.[/bold green]")

        findings = (
            f"Pipeline completed successfully. {len(notes)} notes extracted. "
            f"{agg_stats.successful_writes} sections written."
        )
        summary_obj = ExecutionSummary(
            stage_metrics=stage_metrics, completion_status="success", consolidated_findings=findings
        )
        return summary_obj


def run_pipeline() -> ExecutionSummary:
    orchestrator = Orchestrator()
    return orchestrator.run()
