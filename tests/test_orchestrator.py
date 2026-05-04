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
    """``provider='openai'`` dispatches to OpenAIProvider with a GPT default.

    The default-swap fires when the configured model id is obviously
    an Ollama identifier (``family:tag``) — the common "user opted
    into openai but forgot to update WIKIFI_MODEL" case.
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    settings = _settings(provider="openai", model="qwen3.6:27b")
    provider = build_provider(settings)
    from wikifi.providers.openai_provider import OpenAIProvider

    assert isinstance(provider, OpenAIProvider)
    # Falls back to gpt-4o rather than 404'ing on the Ollama default.
    assert provider.model.startswith("gpt-")


def test_build_provider_preserves_explicit_openai_model(monkeypatch):
    """A user-supplied gpt/o-series model id is passed through unchanged."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    for model in ("gpt-4o", "o3-mini", "gpt-5"):
        settings = _settings(provider="openai", model=model)
        provider = build_provider(settings)
        assert provider.model == model


def test_build_provider_preserves_azure_openai_deployment_id(monkeypatch):
    """Arbitrary Azure / proxy deployment IDs survive the swap.

    Azure-OpenAI (and OpenAI-compatible proxies) commonly use
    deployment names that don't match the upstream OpenAI prefixes —
    e.g. ``prod-gpt4o``, ``eastus-chat``, ``my-team-deployment``.
    Replacing them with ``gpt-4o`` would silently route the user to
    the wrong model on a perfectly valid configuration.
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    for deployment in ("prod-gpt4o", "eastus-chat", "my-team-deployment", "fine-tuned-v3"):
        settings = _settings(
            provider="openai",
            model=deployment,
            openai_base_url="https://my-azure-endpoint.openai.azure.com/",
        )
        provider = build_provider(settings)
        assert provider.model == deployment, f"{deployment} should pass through unchanged"


def test_build_provider_preserves_fine_tuned_openai_model(monkeypatch):
    """``ft:gpt-4o:org::id`` contains a colon but stays on the OpenAI path."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    settings = _settings(provider="openai", model="ft:gpt-4o:my-org::abc123")
    provider = build_provider(settings)
    assert provider.model == "ft:gpt-4o:my-org::abc123"


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


def test_run_walk_short_circuits_when_fully_cached(mini_target, mock_provider_factory):
    """A second walk with no source changes skips stages 3 & 4 entirely.

    Concretely: the first walk extracts and aggregates from scratch.
    The second walk hits the per-file cache for every file and finds
    the prior introspection scope on disk — so stages 3 and 4 don't
    run, and no aggregation/derivation LLM calls fire even though the
    in-memory aggregation/derivation caches are empty in the mock
    provider's bookkeeping.
    """
    settings = _settings()
    introspection = IntrospectionResult(
        include=["src/"], exclude=[], primary_languages=["python"], likely_purpose="demo", rationale="ok"
    )
    call_log = {"intro": 0, "extract": 0, "aggregate": 0, "derive": 0}

    def factory(schema, system, user):
        if schema is IntrospectionResult:
            call_log["intro"] += 1
            return introspection
        if schema is FileFindings:
            call_log["extract"] += 1
            return FileFindings(
                summary="role",
                findings=[SectionFinding(section_id="entities", finding="Order entity.")],
            )
        if schema is SectionBody:
            call_log["aggregate"] += 1
            return SectionBody(body="Synthesized.")
        if schema is DerivedSection:
            call_log["derive"] += 1
            return DerivedSection(body="Derived.")
        raise AssertionError(f"unexpected {schema}")

    provider = mock_provider_factory(json_factory=factory)
    first = run_walk(root=mini_target, settings=settings, provider=provider)
    assert first.fully_cached is False
    assert call_log["aggregate"] >= 1
    assert call_log["derive"] >= 1

    aggregate_baseline = call_log["aggregate"]
    derive_baseline = call_log["derive"]

    second = run_walk(root=mini_target, settings=settings, provider=provider)
    assert second.fully_cached is True
    # Stages 3 and 4 are skipped entirely on the no-change re-walk.
    assert call_log["aggregate"] == aggregate_baseline
    assert call_log["derive"] == derive_baseline


def test_run_walk_introspection_scope_change_defeats_short_circuit(mini_target, mock_provider_factory):
    """A scope shift forces stages 3 & 4 to run even on full-extraction-cache hits."""
    settings = _settings()
    intro_v1 = IntrospectionResult(
        include=["src/"], exclude=[], primary_languages=["python"], likely_purpose="demo", rationale="ok"
    )
    # Stage 1 returns a different exclude list on the second walk.
    intro_v2 = IntrospectionResult(
        include=["src/"],
        exclude=["fixtures/"],
        primary_languages=["python"],
        likely_purpose="demo",
        rationale="ok",
    )
    intro_calls = {"n": 0}
    aggregate_calls = {"n": 0}

    def factory(schema, system, user):
        if schema is IntrospectionResult:
            intro_calls["n"] += 1
            return intro_v1 if intro_calls["n"] == 1 else intro_v2
        if schema is FileFindings:
            return FileFindings(
                summary="role",
                findings=[SectionFinding(section_id="entities", finding="Order entity.")],
            )
        if schema is SectionBody:
            aggregate_calls["n"] += 1
            return SectionBody(body="Synthesized.")
        if schema is DerivedSection:
            return DerivedSection(body="Derived.")
        raise AssertionError(f"unexpected {schema}")

    provider = mock_provider_factory(json_factory=factory)
    run_walk(root=mini_target, settings=settings, provider=provider)

    # Second walk: extraction is 100% cached but scope changed → the
    # short-circuit must not fire. The aggregator's per-section cache
    # still hits (notes are byte-identical), so we assert via
    # ``fully_cached`` and ``sections_cached`` rather than counting
    # aggregator LLM calls.
    report = run_walk(root=mini_target, settings=settings, provider=provider)
    assert report.fully_cached is False
    assert report.aggregation.sections_cached > 0


def test_run_walk_does_not_short_circuit_when_aggregation_cache_partial(mini_target, mock_provider_factory):
    """A walk that previously crashed mid-stage-3 must re-aggregate stale sections.

    Reproduces the "interrupted walk leaves stale prose" bug:
    extraction is 100% cached, scope matches, but one section's
    aggregation entry is missing (or stale) on disk. The early-out
    would skip stages 3 & 4 if it only checked extraction; the
    strengthened predicate must catch the gap and re-run.
    """
    from wikifi.cache import load as load_cache
    from wikifi.cache import save as save_cache

    settings = _settings()
    introspection = IntrospectionResult(
        include=["src/"], exclude=[], primary_languages=["python"], likely_purpose="demo", rationale="ok"
    )
    aggregate_calls = {"n": 0}

    def factory(schema, system, user):
        if schema is IntrospectionResult:
            return introspection
        if schema is FileFindings:
            return FileFindings(
                summary="role",
                findings=[
                    SectionFinding(section_id="entities", finding="Order entity."),
                    SectionFinding(section_id="capabilities", finding="Order capability."),
                ],
            )
        if schema is SectionBody:
            aggregate_calls["n"] += 1
            return SectionBody(body="Synthesized.")
        if schema is DerivedSection:
            return DerivedSection(body="Derived.")
        raise AssertionError(f"unexpected {schema}")

    provider = mock_provider_factory(json_factory=factory)
    run_walk(root=mini_target, settings=settings, provider=provider)
    baseline = aggregate_calls["n"]

    # Simulate a mid-stage-3 crash: drop one section's aggregation cache
    # entry from disk. Live notes are untouched, extraction cache is
    # untouched, only the aggregation entry for "entities" goes missing.
    layout = WikiLayout(root=mini_target)
    cache = load_cache(layout)
    assert "entities" in cache.aggregation
    del cache.aggregation["entities"]
    save_cache(layout, cache)

    report = run_walk(root=mini_target, settings=settings, provider=provider)
    assert report.fully_cached is False, "missing aggregation entry must defeat short-circuit"
    # Stage 3 ran; the missing section was re-aggregated (others hit the
    # remaining cache entries).
    assert aggregate_calls["n"] > baseline


def test_run_walk_does_not_short_circuit_when_aggregation_cache_stale(mini_target, mock_provider_factory):
    """If a cached ``notes_hash`` no longer matches live notes, force re-aggregation.

    This is the symmetric case to the missing-entry test: the entry is
    present on disk but its hash is from a prior set of notes. The
    early-out must not fire.
    """
    from wikifi.cache import load as load_cache
    from wikifi.cache import save as save_cache

    settings = _settings()
    introspection = IntrospectionResult(
        include=["src/"], exclude=[], primary_languages=["python"], likely_purpose="demo", rationale="ok"
    )

    def factory(schema, system, user):
        if schema is IntrospectionResult:
            return introspection
        if schema is FileFindings:
            return FileFindings(
                summary="role",
                findings=[SectionFinding(section_id="entities", finding="Order entity.")],
            )
        if schema is SectionBody:
            return SectionBody(body="Synthesized.")
        if schema is DerivedSection:
            return DerivedSection(body="Derived.")
        raise AssertionError(f"unexpected {schema}")

    provider = mock_provider_factory(json_factory=factory)
    run_walk(root=mini_target, settings=settings, provider=provider)

    layout = WikiLayout(root=mini_target)
    cache = load_cache(layout)
    # Forge a stale hash on a section that has notes.
    cache.aggregation["entities"].notes_hash = "stale-hash-from-a-prior-walk"
    save_cache(layout, cache)

    report = run_walk(root=mini_target, settings=settings, provider=provider)
    assert report.fully_cached is False


def test_run_walk_does_not_short_circuit_when_derivation_cache_missing(mini_target, mock_provider_factory):
    """A missing derivation cache entry must defeat the short-circuit too."""
    from wikifi.cache import load as load_cache
    from wikifi.cache import save as save_cache

    settings = _settings()
    introspection = IntrospectionResult(
        include=["src/"], exclude=[], primary_languages=["python"], likely_purpose="demo", rationale="ok"
    )

    def factory(schema, system, user):
        if schema is IntrospectionResult:
            return introspection
        if schema is FileFindings:
            return FileFindings(
                summary="role",
                findings=[SectionFinding(section_id="entities", finding="Order entity.")],
            )
        if schema is SectionBody:
            return SectionBody(body="Synthesized.")
        if schema is DerivedSection:
            return DerivedSection(body="Derived.")
        raise AssertionError(f"unexpected {schema}")

    provider = mock_provider_factory(json_factory=factory)
    run_walk(root=mini_target, settings=settings, provider=provider)

    layout = WikiLayout(root=mini_target)
    cache = load_cache(layout)
    # Drop derivation entries to simulate a stage-4 crash.
    cache.derivation.clear()
    save_cache(layout, cache)

    report = run_walk(root=mini_target, settings=settings, provider=provider)
    assert report.fully_cached is False


def test_run_walk_first_walk_is_never_fully_cached(mini_target, mock_provider_factory):
    """Without a prior introspection on disk, the early-out cannot fire."""
    settings = _settings()
    introspection = IntrospectionResult(
        include=["src/"], exclude=[], primary_languages=["python"], likely_purpose="demo", rationale="ok"
    )

    def factory(schema, system, user):
        if schema is IntrospectionResult:
            return introspection
        if schema is FileFindings:
            return FileFindings(findings=[SectionFinding(section_id="entities", finding="Order.")])
        if schema is SectionBody:
            return SectionBody(body="Synthesized.")
        if schema is DerivedSection:
            return DerivedSection(body="Derived.")
        raise AssertionError(f"unexpected {schema}")

    provider = mock_provider_factory(json_factory=factory)
    report = run_walk(root=mini_target, settings=settings, provider=provider)
    assert report.fully_cached is False


def test_run_walk_does_not_short_circuit_when_contributing_file_deleted(mini_target, mock_provider_factory):
    """Deleting a contributing file between walks must force stage 3 to rewrite the section.

    Reproduces the empty-notes blind spot that the aggregator's
    full-cache predicate previously had: walk 1 produces findings for
    section X from one file. The file is deleted before walk 2. Stage 2
    of walk 2 produces zero notes for X, but the on-disk markdown still
    holds last walk's prose. Without the empty-state cache assertion,
    the orchestrator's short-circuit would fire and freeze the stale
    body in place.
    """
    settings = _settings()
    introspection = IntrospectionResult(
        include=["src/"], exclude=[], primary_languages=["python"], likely_purpose="demo", rationale="ok"
    )

    # Only src/ files produce "entities" findings — manifests stay silent.
    # Without this, replaying README/pyproject cache entries would keep
    # the section's notes non-empty after the src/ deletion and obscure
    # the bug we're guarding against.
    def factory(schema, system, user):
        if schema is IntrospectionResult:
            return introspection
        if schema is FileFindings:
            if "src/fakeapp" in user:
                return FileFindings(
                    summary="domain code",
                    findings=[SectionFinding(section_id="entities", finding="Order entity inferred.")],
                )
            return FileFindings()  # manifests / readme contribute nothing
        if schema is SectionBody:
            return SectionBody(body="Order is a real thing.")
        if schema is DerivedSection:
            return DerivedSection(body="Derived from Order.")
        raise AssertionError(f"unexpected {schema}")

    provider = mock_provider_factory(json_factory=factory)
    run_walk(root=mini_target, settings=settings, provider=provider)

    layout = WikiLayout(root=mini_target)
    entities_after_first = layout.section_path("entities").read_text()
    assert "Order is a real thing." in entities_after_first

    # Delete every src/ file that contributed findings. The next walk's
    # stage 2 produces zero notes for "entities" (the surviving manifests
    # contribute nothing), so stage 3's empty-notes branch is what should
    # run. The short-circuit must not fire.
    for src_file in (mini_target / "src" / "fakeapp").rglob("*.py"):
        src_file.unlink()

    second = run_walk(root=mini_target, settings=settings, provider=provider)
    assert second.fully_cached is False, (
        "deleting the contributing files must force stage 3 to re-run; "
        "otherwise the prior walk's prose stays on disk forever"
    )

    entities_after_second = layout.section_path("entities").read_text()
    assert "Order is a real thing." not in entities_after_second
    # The aggregator's empty-body placeholder is what should be on disk now.
    assert "No findings were extracted" in entities_after_second


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
