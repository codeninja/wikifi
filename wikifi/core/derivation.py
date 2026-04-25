from pathlib import Path
from typing import List

from rich.console import Console

from wikifi.config import get_settings
from wikifi.llm import llm_provider
from wikifi.models import DocumentationSection

console = Console()


class DerivationEngine:
    def __init__(self):
        self.settings = get_settings()
        self.sections_dir = Path(self.settings.workspace_path)

        self.derivative_sections = {
            "user_personas": (
                "User personas — derived from capabilities, intent, entities, and integrations. "
                "AI-generated, with intent, needs, painpoints, usage patterns, and use cases."
            ),
            "user_stories": (
                "User stories — core features expressed as Gherkin-style user stories "
                "with acceptance criteria, keyed to the personas above."
            ),
            "diagrams": (
                "Diagrams — representations of domains, entities, integrations, "
                "rendered from the aggregate; technology-agnostic. 10000-foot view."
            ),
        }

    def generate_derivative(self, name: str, desc: str, aggregated_docs: str) -> str:
        prompt = (
            f"You are a technical architect generating derivative documentation.\n"
            f"Based ONLY on the provided primary documentation, generate the '{name}' section.\n"
            f"Description: {desc}\n\n"
            "Constraints:\n"
            "- Do NOT fabricate information not supported by the aggregate documents.\n"
            "- Keep the output technology-agnostic.\n"
            "- Do NOT include top-level headings, rely exclusively on sub-headings, lists, and tables.\n\n"
            f"Primary Documentation:\n{aggregated_docs}"
        )

        system_prompt = (
            "You are a technical architect creating derivative documentation "
            "artifacts based on provided source materials."
        )

        try:
            return llm_provider.generate_text(prompt, system_prompt)
        except Exception as e:
            return f"Derivation failed: {e}"


def run_derivation(sections: List[DocumentationSection]) -> None:
    engine = DerivationEngine()

    # Combine all primary documentation for context
    aggregated_docs = ""
    for sec in sections:
        aggregated_docs += f"--- {sec.category} ---\n{sec.final_markdown_body}\n\n"

    # Cap length if needed
    if len(aggregated_docs) > 80000:
        aggregated_docs = aggregated_docs[:80000] + "\n... truncated for brevity ..."

    console.print("[bold cyan]Generating derivative documentation...[/bold cyan]")
    for name, desc in engine.derivative_sections.items():
        console.print(f"Deriving {name}...")
        content = engine.generate_derivative(name, desc, aggregated_docs)

        file_path = engine.sections_dir / f"{name}.md"
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            console.print(f"[red]Failed to write {name}.md: {e}[/red]")
