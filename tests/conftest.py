import pytest
from wikifi.provider.base import LLMProvider
from typing import Dict, List, Optional

class MockProvider(LLMProvider):
    async def generate(self, prompt: str, system_prompt: Optional[str] = None, json_mode: bool = False) -> str:
        if json_mode:
            p = prompt.lower()
            if "repository summary" in p or "introspection" in p:
                return '{"primary_languages": ["Python"], "inferred_purpose": "Test Purpose", "classification_rationale": "Test Rationale", "notable_files": []}'
            if "source file" in p:
                return '{"role_summary": "Test Role", "finding": "Test Finding"}'
            return "{}"
        return "Synthesized content for testing."

    async def chat(self, messages: List[Dict[str, str]], json_mode: bool = False) -> str:
        return "Mock chat response"

@pytest.fixture
def mock_provider():
    return MockProvider()
