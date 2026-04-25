from pathlib import Path
from typing import List, Tuple

from rich.console import Console

from wikifi.config import get_settings
from wikifi.llm import llm_provider
from wikifi.models import AggregationStats, DocumentationSection, ExtractionNote

console = Console()


class AggregationEngine:
    def __init__(self):
        self.settings = get_settings()
        self.sections_dir = Path(self.settings.workspace_path)
        self.sections_dir.mkdir(parents=True, exist_ok=True)

        self.primary_sections = {
            "domains": "DDD domains and subdomains — the core business domains, subdomains, and their relationships.",
            "intent": "Intent and problem space — the 'why' behind the system.",
            "application": "What the application does and solves — a domain-level description.",
            "external_dependencies": "External-system dependencies — third-party APIs, services.",
            "integrations": "Internal + external integrations — touchpoints in both directions.",
            "cross_cutting": "Cross-cutting concerns — observability, monitoring, data integrity, authentication.",
            "entities": "Core entities and their structures — data structures, relationships, patterns.",
            "hard_specifications": "Hard specifications — critical requirements which must be carried forward.",
            "schematics": "Inline Schematics — Mermaid diagrams representing domains, entities.",
        }

    def aggregate_section(
        self, section_name: str, section_desc: str, notes: List[ExtractionNote]
    ) -> DocumentationSection:
        # Prepare the context
        notes_context = ""
        for i, note in enumerate(notes):
            notes_context += f"--- Note {i + 1} from {note.file_reference} ---\nRole: {note.role_summary}\nFinding: {note.extracted_finding}\n\n"
            if len(notes_context) > 80000:
                notes_context += "... truncated for brevity ...\n"
                break

        prompt = (
            f"You are a technical writer synthesizing a technology-agnostic knowledge base.\n"
            f"Your task is to write the section: '{section_name}'\n"
            f"Description: {section_desc}\n\n"
            "Constraints:\n"
            "- Extract and synthesize content directly from the provided notes.\n"
            "- If the notes lack relevant information for this section, you MUST state explicitly: "
            "'No explicit information found for this section.' Do NOT fabricate or speculate.\n"
            "- Avoid implementation-specific terminology. Use domain language.\n"
            "- Do NOT include top-level headings, rely exclusively on sub-headings, lists, and tables.\n\n"
            f"Extracted Notes:\n{notes_context}"
        )

        system_prompt = (
            "You are a technical writer producing markdown documentation. "
            "Write a concise, narrative synthesis avoiding raw transcripts."
        )

        try:
            markdown_content = llm_provider.generate_text(prompt, system_prompt)
        except Exception as e:
            markdown_content = f"Synthesis failed: {e}"

        return DocumentationSection(
            category=section_name, aggregated_content=markdown_content, final_markdown_body=markdown_content
        )


def run_aggregation(notes: List[ExtractionNote]) -> Tuple[List[DocumentationSection], AggregationStats]:
    engine = AggregationEngine()
    sections = []
    successful_writes = 0
    empty_section_count = 0

    console.print("[bold cyan]Synthesizing primary documentation sections...[/bold cyan]")

    for name, desc in engine.primary_sections.items():
        console.print(f"Aggregating {name}...")
        section = engine.aggregate_section(name, desc, notes)

        content_lower = section.final_markdown_body.lower()
        is_empty = "no explicit information" in content_lower or len(content_lower) < 50

        if is_empty:
            empty_section_count += 1
            section.final_markdown_body = "*No explicit information found for this section.*"

        file_path = engine.sections_dir / f"{name}.md"
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(section.final_markdown_body)
            successful_writes += 1
        except Exception as e:
            console.print(f"[red]Failed to write {name}.md: {e}[/red]")

        sections.append(section)

    stats = AggregationStats(successful_writes=successful_writes, empty_section_count=empty_section_count)

    return sections, stats
