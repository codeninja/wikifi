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

When stage 2 finishes with 100% cache hits and the introspection scope
is unchanged from the prior walk, stages 3 and 4 are skipped entirely —
the wiki on disk is already current, and re-running the LLM passes
would only risk drift on prose that already passed review. See
``_evaluate_short_circuit`` for the exact predicate.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from wikifi.aggregator import AggregationStats, aggregate_all, aggregation_fully_cached
from wikifi.cache import (
    WalkCache,
    hash_introspection_scope,
    save_aggregation,
    save_derivation,
    save_extraction,
    save_introspection,
)
from wikifi.cache import load as load_cache
from wikifi.cache import reset as reset_cache
from wikifi.cache import save as save_cache
from wikifi.config import Settings
from wikifi.deriver import DerivationStats, derivation_fully_cached, derive_all
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
    # True when stage 2 saw 100% cache hits *and* the introspection
    # scope matched the prior walk, so stages 3 & 4 were skipped. The
    # CLI uses this to surface "no work needed" rather than rendering
    # a long stats table that's all zeros.
    fully_cached: bool = False


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
    prior_scope_hash: str | None = None
    if settings.use_cache:
        cache = load_cache(layout)
        # Snapshot the prior walk's scope before we overwrite it — the
        # short-circuit check needs to compare against what was on disk
        # at the start of *this* walk.
        prior_scope_hash = cache.introspection.scope_hash if cache.introspection else None
        # Drop cache entries for files that fell out of scope so the
        # cache size tracks the live in-scope set.
        in_scope = {p.as_posix() for p in files}
        cache.prune_extraction(keep=in_scope)
    else:
        reset_cache(layout)

    # Persist this walk's introspection result before stage 2 starts.
    # Even if the walk crashes between here and the end, the scope hash
    # is on disk so the next walk can decide whether to short-circuit.
    if cache is not None:
        scope_hash = hash_introspection_scope(include=introspection.include, exclude=introspection.exclude)
        cache.record_introspection(scope_hash=scope_hash, payload=introspection.model_dump())
        save_introspection(layout, cache)
    else:
        scope_hash = None

    graph: RepoGraph | None = None
    if settings.use_graph:
        log.info("stage 1.5: building repo import graph")
        graph = build_graph(repo_root=root, files=files)

    log.info("stage 2: extracting per-file findings")
    reset_notes(layout)

    def _persist_extraction() -> None:
        if cache is not None:
            save_extraction(layout, cache)

    extraction = extract_repo(
        layout=layout,
        provider=provider,
        files=files,
        repo_root=root,
        chunk_size_bytes=settings.chunk_size_bytes,
        chunk_overlap_bytes=settings.chunk_overlap_bytes,
        cache=cache,
        graph=graph,
        persist_cache=_persist_extraction if cache is not None else None,
        use_specialized_extractors=settings.use_specialized_extractors,
    )

    fully_cached = _evaluate_short_circuit(
        extraction=extraction,
        scope_hash=scope_hash,
        prior_scope_hash=prior_scope_hash,
        cache=cache,
        layout=layout,
        review=settings.review_derivatives,
    )

    if fully_cached:
        log.info(
            "stages 3 & 4 skipped: %d files all cache-hit and introspection scope unchanged",
            extraction.files_seen,
        )
        # Bring the cache file mtime forward so a watcher tailing the
        # cache dir sees that this walk did happen, even though it was
        # a no-op LLM-wise.
        if cache is not None:
            save_cache(layout, cache)
        return WalkReport(
            introspection=introspection,
            extraction=extraction,
            aggregation=AggregationStats(),
            derivation=DerivationStats(),
            cache=cache,
            graph=graph,
            fully_cached=True,
        )

    def _persist_aggregation() -> None:
        if cache is not None:
            save_aggregation(layout, cache)

    log.info("stage 3: aggregating primary sections")
    aggregation = aggregate_all(
        layout=layout,
        provider=provider,
        cache=cache,
        persist_cache=_persist_aggregation if cache is not None else None,
    )

    def _persist_derivation() -> None:
        if cache is not None:
            save_derivation(layout, cache)

    log.info("stage 4: deriving personas, user stories, and diagrams")
    derivation = derive_all(
        layout=layout,
        provider=provider,
        review=settings.review_derivatives,
        review_min_score=settings.review_min_score,
        cache=cache,
        persist_cache=_persist_derivation if cache is not None else None,
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
        fully_cached=False,
    )


def _evaluate_short_circuit(
    *,
    extraction: ExtractionStats,
    scope_hash: str | None,
    prior_scope_hash: str | None,
    cache: WalkCache | None,
    layout: WikiLayout,
    review: bool,
) -> bool:
    """Decide whether stages 3 & 4 can be skipped.

    Five conditions must hold:

    1. Caching is on (``cache`` is not None).
    2. We saw at least one file (an empty repo never short-circuits —
       there's nothing to assert is "current").
    3. Every file processed in stage 2 either hit the per-file cache or
       was handled by a deterministic specialized extractor — i.e. no
       LLM call produced new findings that downstream stages haven't
       seen yet.
    4. The introspection scope matches the prior walk's. A scope shift
       can change which findings flow into which sections even when
       individual files are byte-identical, so it has to defeat the
       early-out.
    5. Every primary section's aggregation cache and every derivative
       section's derivation cache is *fresh* against the current notes /
       upstream bodies. This guards the mid-stage-3-or-4 crash case: a
       prior walk that aggregated section A but died before B–H would
       leave the extraction cache 100% covered yet sections B–H stale on
       disk. Without this guard the early-out would freeze the staleness
       in place forever.

    The "first walk on a fresh wiki" case naturally falls through:
    ``prior_scope_hash`` is None, so condition 4 fails.
    """
    if cache is None:
        return False
    if extraction.files_seen <= 0:
        return False
    no_llm_files = extraction.cache_hits + extraction.specialized_files
    if no_llm_files != extraction.files_seen:
        return False
    if scope_hash is None or prior_scope_hash is None:
        return False
    if scope_hash != prior_scope_hash:
        return False
    if not aggregation_fully_cached(layout, cache):
        return False
    if not derivation_fully_cached(layout, cache, review=review):
        return False
    return True


def build_provider(settings: Settings) -> LLMProvider:
    """Construct the configured provider.

    Local Ollama is the default. Hosted backends are opt-in via
    ``WIKIFI_PROVIDER=anthropic`` (plus ``ANTHROPIC_API_KEY``) or
    ``WIKIFI_PROVIDER=openai`` (plus ``OPENAI_API_KEY``).
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
    if settings.provider == "openai":
        from wikifi.providers.openai_provider import OpenAIProvider

        # Same default-swap guard as the Anthropic path, but inverted:
        # only swap when the model id is *obviously* an Ollama
        # identifier (the user opted into openai but forgot to update
        # WIKIFI_MODEL). Anything else passes through unchanged so
        # Azure-OpenAI / proxy deployments — which use arbitrary
        # deployment IDs like ``prod-gpt4o`` or ``eastus-chat`` that
        # don't match the upstream OpenAI naming convention — keep
        # working.
        model = "gpt-4o" if _looks_like_ollama_model(settings.model) else settings.model
        return OpenAIProvider(
            model=model,
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            timeout=settings.request_timeout,
            max_tokens=settings.openai_max_tokens,
            think=settings.think,
        )
    raise ValueError(f"unknown provider {settings.provider!r}; expected 'ollama', 'anthropic', or 'openai'")


def _looks_like_ollama_model(model: str) -> bool:
    """Heuristic — Ollama uses ``family:tag`` (e.g. ``qwen3.6:27b``).

    Fine-tuned OpenAI models also contain ``:`` (``ft:gpt-4o:...``)
    so we exclude that prefix. Anything else without a ``:`` —
    upstream OpenAI ids, Azure deployment names, plain proxy aliases —
    is left alone.
    """
    return ":" in model and not model.lower().startswith("ft:")
