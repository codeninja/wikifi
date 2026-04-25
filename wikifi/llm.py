import json
from typing import Optional, Type, TypeVar

import litellm
from pydantic import BaseModel

from wikifi.config import get_settings

T = TypeVar("T", bound=BaseModel)


class LLMProvider:
    def __init__(self):
        self.settings = get_settings()
        self.model = self.settings.llm_model

        if self.settings.llm_api_key:
            litellm.api_key = self.settings.llm_api_key

        # Optionally disable litellm telemetry if desired
        litellm.telemetry = False

    def generate_structured(self, prompt: str, schema: Type[T]) -> T:
        """Generate structured output according to the given Pydantic schema."""
        # For maximum compatibility with local LLMs (Ollama),
        # we instruct the model to return JSON matching the schema.
        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        system_prompt = f"You are an analytical agent. You must respond ONLY with valid JSON matching the following schema:\n{schema_json}"

        try:
            response = litellm.completion(
                model=self.model,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            # Remove any potential markdown block backticks wrapping the JSON (common with some local models)
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            return schema.model_validate_json(content)
        except Exception as e:
            # Re-raise to be handled by pipeline observability
            raise RuntimeError(f"Failed to generate structured output: {e}") from e

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate free-form analytical generation for narrative clarity."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = litellm.completion(
                model=self.model,
                messages=messages,
            )
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"Failed to generate text output: {e}") from e


# Singleton instance
llm_provider = LLMProvider()
