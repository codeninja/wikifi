from wikifi.introspection import IntrospectionResult, introspect
from wikifi.walker import WalkConfig


def test_introspect_passes_tree_summary_to_provider(mini_target, mock_provider_factory):
    canned = IntrospectionResult(
        include=["src/"],
        exclude=["dist/"],
        primary_languages=["python"],
        likely_purpose="A small order-management demo.",
        rationale="src/ holds the only domain logic.",
    )
    provider = mock_provider_factory(json_responses={IntrospectionResult: [canned]})
    result = introspect(WalkConfig(root=mini_target), provider)

    assert result == canned
    schema, system, user = provider.json_calls[0]
    assert schema is IntrospectionResult
    assert "tech-agnostic" in system or "intent" in system.lower()
    assert "src" in user
    assert "pyproject.toml" in user


def test_introspect_includes_manifest_contents_in_prompt(mini_target, mock_provider_factory):
    canned = IntrospectionResult(include=[], exclude=[], primary_languages=[], likely_purpose="", rationale="")
    provider = mock_provider_factory(json_responses={IntrospectionResult: [canned]})
    introspect(WalkConfig(root=mini_target), provider)
    _, _, user = provider.json_calls[0]
    assert "fakeapp" in user  # the project name from pyproject.toml
