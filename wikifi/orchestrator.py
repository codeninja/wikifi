"""End-to-end pipeline that wires Stage 1 → Stage 2 → Stage 3 → Stage 4.

The CLI calls into ``init_wiki`` and ``run_walk``. Both accept a target root
and a configured provider so tests can substitute a mock provider trivially.

- Stage 1: LLM introspection of repo structure (`introspection.introspect`)
- Stage 2: deterministic per-file extraction → JSONL notes (`extractor.extract_repo`)
- Stage 3: per-section aggregation of primary sections (`aggregator.aggregate_all`)
- Stage 4: derivation of personas/user_stories/diagrams from primary section
  bodies (`deriver.derive_all`)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from wikifi.aggregator import AggregationStats, aggregate_all
from wikifi.config import Settings
from wikifi.deriver import DerivationStats, derive_all
from wikifi.extractor import ExtractionStats, extract_repo
from wikifi.introspection import IntrospectionResult, introspect
from wikifi.providers.base import LLMProvider
from wikifi.providers.ollama_provider import OllamaProvider
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

    provider = provider or _default_provider(settings)

    base_config = WalkConfig(
        root=root,
        max_file_bytes=settings.max_file_bytes,
    )

    log.info("stage 1: introspecting repository structure")
    introspection = introspect(base_config, provider, max_depth=settings.introspection_depth)

    walk_config = WalkConfig(
        root=root,
        extra_excludes=tuple(introspection.exclude),
        max_file_bytes=settings.max_file_bytes,
    )

    log.info("stage 2: extracting per-file findings")
    reset_notes(layout)
    files = list(iter_files(walk_config))
    extraction = extract_repo(
        layout=layout,
        provider=provider,
        files=files,
        repo_root=root,
        max_file_bytes=settings.max_file_bytes,
    )

    log.info("stage 3: aggregating primary sections")
    aggregation = aggregate_all(layout=layout, provider=provider)

    log.info("stage 4: deriving personas, user stories, and diagrams")
    derivation = derive_all(layout=layout, provider=provider)

    return WalkReport(
        introspection=introspection,
        extraction=extraction,
        aggregation=aggregation,
        derivation=derivation,
    )


def _default_provider(settings: Settings) -> LLMProvider:
    if settings.provider != "ollama":
        raise ValueError(
            f"unknown provider {settings.provider!r}; only 'ollama' is supported in v1"
        )
    return OllamaProvider(
        model=settings.model,
        host=settings.ollama_host,
        timeout=settings.request_timeout,
        think=settings.think,
    )
