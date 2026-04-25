from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, system_prompt: Optional[str] = None, json_mode: bool = False) -> str:
        pass

    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]], json_mode: bool = False) -> str:
        pass
