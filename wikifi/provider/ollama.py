import json
from typing import Dict, List, Optional
import httpx
from wikifi.provider.base import LLMProvider

class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str, model: str, thinking_level: str = "highest"):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.thinking_level = thinking_level

    async def generate(self, prompt: str, system_prompt: Optional[str] = None, json_mode: bool = False) -> str:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if system_prompt:
            payload["system"] = system_prompt
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            text = response.json()["response"]
            
            if json_mode:
                # Basic attempt to extract JSON if embedded in markdown or other text
                import re
                match = re.search(r'\{.*\}', text, re.DOTALL)
                if match:
                    return match.group(0)
            return text

    async def chat(self, messages: List[Dict[str, str]], json_mode: bool = False) -> str:
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "format": "json" if json_mode else None,
        }
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()["message"]["content"]
