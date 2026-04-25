from typing import List
from loguru import logger
from wikifi.models import ExtractionNote, IntrospectionAssessment, DocumentationSection
from wikifi.provider.base import LLMProvider

class Synthesizer:
    def __init__(self, provider: LLMProvider):
        self.provider = provider
        self.sections = [
            "DDD domains and subdomains",
            "Intent and problem space",
            "What the application does and solves",
            "External-system dependencies",
            "Internal + external integrations",
            "Cross-cutting concerns",
            "Core entities and their structures",
            "Hard specifications",
        ]

    async def synthesize_section(self, section_name: str, assessment: IntrospectionAssessment, notes: List[ExtractionNote]) -> str:
        notes_text = "\n".join([f"- File: {n.file_path}\n  Role: {n.role_summary}\n  Finding: {n.finding}" for n in notes])
        
        prompt = f"""
        Synthesize a documentation section for "{section_name}" based on the repository introspection and extraction notes.
        
        Introspection:
        - Purpose: {assessment.inferred_purpose}
        - Languages: {", ".join(assessment.primary_languages)}
        
        Extraction Notes:
        {notes_text}
        
        Rules:
        - Be technology-agnostic. Strip implementation-specific terminology.
        - Translate technical observations into domain-focused, user-facing intent.
        - For operational or behavioral descriptions, use strict Given/When/Then format.
        - Use Mermaid diagrams where it adds clarity (Schematics).
        - Exclude top-level headings. Use sub-headings (##), lists, and tables.
        - If data is missing for this section, explicitly declare it. Do not fabricate content.
        - Form a coherent, structured narrative.
        """
        
        return await self.provider.generate(prompt)
