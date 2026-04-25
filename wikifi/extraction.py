import json
from pathlib import Path
from typing import List, Optional
from loguru import logger
from wikifi.models import DirectorySummary, IntrospectionAssessment, ExtractionNote
from wikifi.provider.base import LLMProvider
from wikifi.config import settings

class Introspector:
    def __init__(self, provider: LLMProvider):
        self.provider = provider

    async def assess(self, summary: DirectorySummary) -> IntrospectionAssessment:
        prompt = f"""
        Analyze the following repository summary and infer the system's purpose and primary languages.
        
        Summary:
        {summary.model_dump_json(indent=2)}
        
        Respond in JSON format with the following fields:
        - primary_languages: List of primary programming languages
        - inferred_purpose: A brief description of what the system does and why it exists
        - classification_rationale: Why you classified it this way
        - notable_files: Key manifest or documentation files found
        """
        
        response = await self.provider.generate(prompt, json_mode=True)
        try:
            data = json.loads(response)
            return IntrospectionAssessment(**data)
        except Exception as e:
            logger.error(f"Failed to parse introspection response: {e}")
            # Fallback
            return IntrospectionAssessment(
                primary_languages=[],
                inferred_purpose="Unknown",
                classification_rationale="Failed to parse LLM response",
                notable_files=summary.manifests
            )

class Extractor:
    def __init__(self, provider: LLMProvider, root_dir: Path):
        self.provider = provider
        self.root_dir = root_dir

    async def extract_note(self, file_path: Path) -> Optional[ExtractionNote]:
        relative_path = str(file_path.relative_to(self.root_dir))
        
        try:
            with open(file_path, "r", errors="ignore") as f:
                content = f.read(settings.max_file_size)
        except Exception as e:
            logger.warning(f"Could not read file {file_path}: {e}")
            return None

        if len(content.strip()) < settings.min_content_bytes:
            return None

        prompt = f"""
        Analyze the following source file and extract its domain role and key findings.
        Focus on intent, business logic, and functionality, not implementation details.
        Be technology-agnostic.
        
        File: {relative_path}
        Content:
        ```
        {content}
        ```
        
        Respond in JSON format with the following fields:
        - role_summary: What role this file plays in the system domain
        - finding: Key functional or domain-level discovery from this file
        """
        
        try:
            response = await self.provider.generate(prompt, json_mode=True)
            data = json.loads(response)
            return ExtractionNote(
                file_path=relative_path,
                role_summary=data["role_summary"],
                finding=data["finding"]
            )
        except Exception as e:
            logger.error(f"Failed to extract note for {relative_path}: {e}")
            return None
