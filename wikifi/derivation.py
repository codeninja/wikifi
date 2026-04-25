from typing import Dict, List
from wikifi.models import IntrospectionAssessment
from wikifi.provider.base import LLMProvider

class Deriver:
    def __init__(self, provider: LLMProvider):
        self.provider = provider
        self.derivative_sections = [
            "User personas",
            "User stories",
            "System diagrams",
        ]

    async def derive_section(self, section_name: str, assessment: IntrospectionAssessment, primary_content: Dict[str, str]) -> str:
        aggregate_text = "\n\n".join([f"### {k}\n{v}" for k, v in primary_content.items()])
        
        prompt = f"""
        Derive the "{section_name}" section based on the aggregate primary documentation.
        
        Introspection:
        - Purpose: {assessment.inferred_purpose}
        
        Primary Documentation Content:
        {aggregate_text}
        
        Rules:
        - Be technology-agnostic.
        - For "User personas", include intent, needs, painpoints, usage patterns, and use cases.
        - For "User stories", use Gherkin-style (Given/When/Then) with acceptance criteria, keyed to personas.
        - For "System diagrams", use Mermaid to show a 10000-foot view of structure and behavior.
        - Exclude top-level headings. Use sub-headings (##), lists, and tables.
        - If data is missing for this section, explicitly declare it. Do not fabricate content.
        """
        
        return await self.provider.generate(prompt)
