"""End-to-end pipeline that wires Stage 1 → Stage 2 → Stage 3 → Stage 4.

The CLI calls into ``init_wiki``, ``run_walk``, and ``run_report``. Each
accepts a target root and a configured provider so tests can substitute
a mock provider trivially.

- Stage 1: LLM introspection of repo structure (`introspection.introspect`)
- Stage 1.5: lightweight static analysis (`repograph.build_graph`) when
  ``settings.use_graph`` is set
- Stage 2: deterministic per-file extraction → JSONL notes
  (`extractor.extract_repo`), with caching, specialized routing, and
  cross-file context if available
- Stage 3: per-section aggregation of primary sections
  (`aggregator.aggregate_all`), with section-level cache
- Stage 4: derivation of personas/user_stories/diagrams from primary
  section bodies (`deriver.derive_all`), with optional critic loop
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from wikifi.aggregator import AggregationStats, aggregate_all
from wikifi.cache import WalkCache
from wikifi.cache import load as load_cache
from wikifi.cache import reset as reset_cache
from wikifi.cache import save as save_cache
from wikifi.config import Settings
from wikifi.deriver import DerivationStats, derive_all
from wikifi.extractor import ExtractionStats, extract_repo
from wikifi.introspection import IntrospectionResult, introspect
from wikifi.providers.base import LLMProvider
from wikifi.providers.ollama_provider import OllamaProvider
from wikifi.repograph import RepoGraph, build_graph
from wikifi.walker import WalkConfig, iter_files
from wikifi.wiki import WikiLayout, initialize, reset_notes

log = logging.getLogger("wikifi.orchestrator")


def init_wiki(*, root: Path, settings: Settings) -> list[Path]:
    """Create the `.wikifi/` skeleton in ``root``. Idempotent."""
    layout = WikiLayout(root=root)
    return initialize(
        layout,
        model=settings.model,
        provider=settings.provider,
        ollama_host=settings.ollama_host,
    )


@dataclass
class WalkReport:
    introspection: IntrospectionResult
    extraction: ExtractionStats
    aggregation: AggregationStats
    derivation: DerivationStats
    cache: WalkCache | None = None
    graph: RepoGraph | None = None


def run_walk(
    *,
    root: Path,
    settings: Settings,
    provider: LLMProvider | None = None,
) -> WalkReport:
    """Execute the full Stage 1 → 2 → 3 → 4 pipeline against ``root``."""
    layout = WikiLayout(root=root)
    if not layout.wiki_dir.exists():
        # Auto-init so `wikifi walk` works on a fresh project.
        initialize(
            layout,
            model=settings.model,
            provider=settings.provider,
            ollama_host=settings.ollama_host,
        )

    provider = provider or build_provider(settings)

    base_config = WalkConfig(
        root=root,
        max_file_bytes=settings.max_file_bytes,
        min_content_bytes=settings.min_content_bytes,
    )

    log.info("stage 1: introspecting repository structure")
    introspection = introspect(base_config, provider, max_depth=settings.introspection_depth)

    walk_config = WalkConfig(
        root=root,
        extra_excludes=tuple(introspection.exclude),
        max_file_bytes=settings.max_file_bytes,
        min_content_bytes=settings.min_content_bytes,
    )

    files = list(iter_files(walk_config))

    cache: WalkCache | None = None
    if settings.use_cache:
        cache = load_cache(layout)
        # Drop cache entries for files that fell out of scope so the
        # cache size tracks the live in-scope set.
        in_scope = {p.as_posix() for p in files}
        cache.prune_extraction(keep=in_scope)
    else:
        reset_cache(layout)

    graph: RepoGraph | None = None
    if settings.use_graph:
        log.info("stage 1.5: building repo import graph")
        graph = build_graph(repo_root=root, files=files)

    log.info("stage 2: extracting per-file findings")
    reset_notes(layout)

    def _persist() -> None:
        if cache is not None:
            save_cache(layout, cache)

    extraction = extract_repo(
        layout=layout,
        provider=provider,
        files=files,
        repo_root=root,
        chunk_size_bytes=settings.chunk_size_bytes,
        chunk_overlap_bytes=settings.chunk_overlap_bytes,
        cache=cache,
        graph=graph,
        persist_cache=_persist if cache is not None else None,
    )

    log.info("stage 3: aggregating primary sections")
    aggregation = aggregate_all(layout=layout, provider=provider, cache=cache)

    log.info("stage 4: deriving personas, user stories, and diagrams")
    derivation = derive_all(
        layout=layout,
        provider=provider,
        review=settings.review_derivatives,
        review_min_score=settings.review_min_score,
    )

    if cache is not None:
        save_cache(layout, cache)

    return WalkReport(
        introspection=introspection,
        extraction=extraction,
        aggregation=aggregation,
        derivation=derivation,
        cache=cache,
        graph=graph,
    )


def build_provider(settings: Settings) -> LLMProvider:
    """Construct the configured provider.

    Local Ollama is the default. Hosted Anthropic is opt-in via
    ``WIKIFI_PROVIDER=anthropic`` and an ``ANTHROPIC_API_KEY``.
    """
    if settings.provider == "ollama":
        return OllamaProvider(
            model=settings.model,
            host=settings.ollama_host,
            timeout=settings.request_timeout,
            think=settings.think,
        )
    if settings.provider == "anthropic":
        from wikifi.providers.anthropic_provider import AnthropicProvider

        # When users opt in to Anthropic but leave the Ollama default
        # model id in place, swap to a sensible Claude default rather
        # than 404 on the model name.
        model = settings.model if settings.model.startswith("claude-") else "claude-opus-4-7"
        return AnthropicProvider(
            model=model,
            api_key=settings.anthropic_api_key,
            timeout=settings.request_timeout,
            max_tokens=settings.anthropic_max_tokens,
            think=settings.think,
        )
    raise ValueError(f"unknown provider {settings.provider!r}; expected 'ollama' or 'anthropic'")
