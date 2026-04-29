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
