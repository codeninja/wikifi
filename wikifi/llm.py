from typing import Type, TypeVar, Optional
from pydantic import BaseModel
import litellm
import json
from wikifi.config import get_settings

T = TypeVar("T", bound=BaseModel)

class LLMProvider:
    def __init__(self):
        self.settings = get_settings()
        self.model = self.settings.llm_model
        
        # Explicitly disable telemetry and any remote tracking
        litellm.telemetry = False
        litellm.add_function_to_prompt = False
        
    def generate_structured(self, prompt: str, schema: Type[T]) -> T:
        """Generate structured output according to the given Pydantic schema."""
        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        system_prompt = (
            "You are an analytical agent. You must respond ONLY with valid JSON matching the following schema:\n"
            f"{schema_json}\n"
            "Do not include any other text, explanations, or markdown blocks. Just the raw JSON object."
        )
        
        try:
            response = litellm.completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ]
            )
            content = response.choices[0].message.content or ""
            
            # Robust cleaning for local LLM quirks
            content = content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            content = content.strip()
            
            if not content:
                raise ValueError("LLM returned empty content")
                
            return schema.model_validate_json(content)
        except Exception as e:
            # Re-raise with more context
            error_msg = f"Failed to generate structured output: {e}"
            # Check if content was defined in the try block
            try:
                if content:
                    error_msg += f"\nRaw content: {content}"
            except NameError:
                pass
            raise RuntimeError(error_msg) from e

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
