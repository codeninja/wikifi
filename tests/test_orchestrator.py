import pytest

from wikifi.aggregator import SectionBody
from wikifi.config import Settings
from wikifi.deriver import DerivedSection
from wikifi.extractor import FileFindings, SectionFinding
from wikifi.introspection import IntrospectionResult
from wikifi.orchestrator import build_provider, init_wiki, run_walk
from wikifi.providers.ollama_provider import OllamaProvider
from wikifi.sections import SECTIONS
from wikifi.wiki import WikiLayout


def _settings(**overrides):
    base = dict(provider="ollama", model="m", ollama_host="http://h", request_timeout=1, max_file_bytes=200_000)
    base.update(overrides)
    return Settings(_env_file=None, **base)


def test_init_wiki_scaffolds_layout(tmp_path):
    paths = init_wiki(root=tmp_path, settings=_settings())
    assert (tmp_path / ".wikifi" / "config.toml").exists()
    assert paths


def test_run_walk_executes_all_four_stages(mini_target, mock_provider_factory):
    settings = _settings()
    introspection = IntrospectionResult(
        include=["src/"], exclude=[], primary_languages=["python"], likely_purpose="demo", rationale="ok"
    )

    def factory(schema, system, user):
        if schema is IntrospectionResult:
            return introspection
        if schema is FileFindings:
            return FileFindings(
                summary="domain code",
                findings=[SectionFinding(section_id="entities", finding="Order entity inferred.")],
            )
        if schema is SectionBody:
            return SectionBody(body="Synthesized section body.")
        if schema is DerivedSection:
            return DerivedSection(body="Derived section body.")
        raise AssertionError(f"unexpected schema {schema}")

    provider = mock_provider_factory(json_factory=factory)
    report = run_walk(root=mini_target, settings=settings, provider=provider)

    assert report.introspection.include == ["src/"]
    assert report.extraction.files_seen >= 2  # api.py + domain.py at least
    assert report.extraction.findings_total >= 2
    assert report.aggregation.sections_written >= 1
    assert report.derivation.sections_derived >= 1

    layout = WikiLayout(root=mini_target)
    entities = layout.section_path("entities").read_text()
    assert "Synthesized section body." in entities
    # personas is derivative; with entities populated it should derive successfully.
    personas = layout.section_path("personas").read_text()
    assert "Derived section body." in personas


def test_run_walk_auto_inits_when_missing(mini_target, mock_provider_factory):
    settings = _settings()
    layout = WikiLayout(root=mini_target)
    assert not layout.wiki_dir.exists()

    provider = mock_provider_factory(
        json_factory=lambda schema, system, user: (
            IntrospectionResult(include=[], exclude=[], primary_languages=[], likely_purpose="", rationale="")
            if schema is IntrospectionResult
            else FileFindings()
            if schema is FileFindings
            else SectionBody(body="empty")
        )
    )
    run_walk(root=mini_target, settings=settings, provider=provider)
    assert layout.wiki_dir.is_dir()
    for section in SECTIONS:
        assert layout.section_path(section).exists()


def test_build_provider_returns_ollama_for_ollama_settings():
    provider = build_provider(_settings(provider="ollama", model="m", ollama_host="http://localhost:11434"))
    assert isinstance(provider, OllamaProvider)
    assert provider.model == "m"


def test_build_provider_rejects_unknown():
    with pytest.raises(ValueError):
        build_provider(_settings(provider="other"))


def test_build_provider_returns_anthropic_when_selected(monkeypatch):
    """``provider='anthropic'`` dispatches to AnthropicProvider with a Claude model default."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    settings = _settings(provider="anthropic", model="m")  # non-claude model id
    provider = build_provider(settings)
    from wikifi.providers.anthropic_provider import AnthropicProvider

    assert isinstance(provider, AnthropicProvider)
    # Falls back to a sane Claude default rather than 404'ing on "m".
    assert provider.model.startswith("claude-")


def test_build_provider_returns_openai_when_selected(monkeypatch):
    """``provider='openai'`` dispatches to OpenAIProvider with a GPT default."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    settings = _settings(provider="openai", model="m")  # non-gpt id
    provider = build_provider(settings)
    from wikifi.providers.openai_provider import OpenAIProvider

    assert isinstance(provider, OpenAIProvider)
    # Falls back to gpt-4o rather than 404'ing on "m".
    assert provider.model.startswith("gpt-")


def test_build_provider_preserves_explicit_openai_model(monkeypatch):
    """A user-supplied gpt/o-series model id is passed through unchanged."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    for model in ("gpt-4o", "o3-mini", "gpt-5"):
        settings = _settings(provider="openai", model=model)
        provider = build_provider(settings)
        assert provider.model == model


def test_run_walk_persists_cache_for_resumability(mini_target, mock_provider_factory):
    """A second walk reuses the cache and skips the LLM call for unchanged files."""
    settings = _settings()
    introspection = IntrospectionResult(
        include=["src/"], exclude=[], primary_languages=["python"], likely_purpose="demo", rationale="ok"
    )

    extraction_calls = {"n": 0}

    def factory(schema, system, user):
        if schema is IntrospectionResult:
            return introspection
        if schema is FileFindings:
            extraction_calls["n"] += 1
            return FileFindings(
                summary="role",
                findings=[SectionFinding(section_id="entities", finding="Order entity inferred.")],
            )
        if schema is SectionBody:
            return SectionBody(body="Synthesized.")
        if schema is DerivedSection:
            return DerivedSection(body="Derived.")
        raise AssertionError(f"unexpected {schema}")

    provider = mock_provider_factory(json_factory=factory)
    run_walk(root=mini_target, settings=settings, provider=provider)
    first = extraction_calls["n"]
    assert first >= 2

    # Second walk against the same target with the same content: cache reuses
    # the per-file findings, so extraction calls do not increase.
    run_walk(root=mini_target, settings=settings, provider=provider)
    assert extraction_calls["n"] == first


def test_run_walk_review_flag_invokes_critic(mini_target, mock_provider_factory):
    """With ``review_derivatives=True`` the deriver runs the critic loop."""
    from wikifi.critic import Critique

    settings = _settings(review_derivatives=True)
    introspection = IntrospectionResult(
        include=["src/"], exclude=[], primary_languages=["python"], likely_purpose="demo", rationale="ok"
    )
    critic_called = {"n": 0}

    def factory(schema, system, user):
        if schema is IntrospectionResult:
            return introspection
        if schema is FileFindings:
            return FileFindings(findings=[SectionFinding(section_id="entities", finding="Order.")])
        if schema is SectionBody:
            return SectionBody(body="Synthesized.")
        if schema is DerivedSection:
            return DerivedSection(body="Derived.")
        if schema is Critique:
            critic_called["n"] += 1
            return Critique(score=9, summary="ok")
        raise AssertionError(f"unexpected {schema}")

    provider = mock_provider_factory(json_factory=factory)
    run_walk(root=mini_target, settings=settings, provider=provider)
    assert critic_called["n"] >= 1
