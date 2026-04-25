from unittest.mock import MagicMock

import litellm
import pytest


@pytest.fixture(autouse=True)
def mock_litellm(monkeypatch):
    def mock_completion(model, messages, **kwargs):
        mock_response = MagicMock()
        mock_message = MagicMock()

        # Determine what to return based on response_format
        response_format = kwargs.get("response_format")
        if response_format and getattr(response_format, "get", lambda k: None)("type") == "json_object":
            # Return dummy JSON matching schema
            # We look at the system prompt which contains the schema
            content = "{}"
            for msg in messages:
                if msg["role"] == "system" and "IntrospectionAssessment" in msg["content"]:
                    content = (
                        '{"primary_languages": ["Python"], '
                        '"inferred_purpose": "Test", '
                        '"classification_rationale": "Mock"}'
                    )
                elif msg["role"] == "system" and "ExtractedData" in msg["content"]:
                    content = '{"role_summary": "Mock role", "extracted_finding": "Mock finding"}'
            mock_message.content = content
        else:
            # Return dummy text
            mock_message.content = "Mock markdown content."

        mock_response.choices = [MagicMock(message=mock_message)]
        return mock_response

    monkeypatch.setattr(litellm, "completion", mock_completion)


@pytest.fixture(autouse=True)
def setup_env(monkeypatch, tmp_path):
    monkeypatch.setenv("ROOT_PATH", str(tmp_path))
    monkeypatch.setenv("WORKSPACE_PATH", str(tmp_path / ".wikifi"))
    monkeypatch.setenv("LLM_API_KEY", "mock_key")
