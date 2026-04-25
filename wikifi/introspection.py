"""Stage 1: introspection — scan the repo and classify it."""

from __future__ import annotations

import logging
from pathlib import Path

from wikifi.config import Settings
from wikifi.filters import ScanReport, render_tree, scan
from wikifi.llm_io import request_structured
from wikifi.prompts import INTROSPECTION_USER, SYSTEM_BASE
from wikifi.providers.base import Provider, ProviderError
from wikifi.schemas import DirectorySummary, IntrospectionAssessment

log = logging.getLogger(__name__)


def summarize(scan_report: ScanReport, *, root: Path, depth: int) -> DirectorySummary:
    """Produce the structural summary that feeds the LLM assessment."""
    samples = sorted(scan_report.in_scope, key=lambda p: p.as_posix())[:25]
    return DirectorySummary(
        file_count=len(scan_report.in_scope),
        total_bytes=scan_report.total_bytes,
        extension_distribution=dict(scan_report.extension_counts.most_common()),
        manifest_presence=sorted(p.name for p in scan_report.manifests_found),
        sample_paths=[p.as_posix() for p in samples],
        tree_outline=render_tree(root, depth=depth),
    )


def introspect(
    *,
    root: Path,
    settings: Settings,
    provider: Provider,
) -> tuple[ScanReport, DirectorySummary, IntrospectionAssessment]:
    """Walk the filesystem, summarize, and ask the LLM for an assessment.

    Returns the raw scan report, the summary fed to the LLM, and the
    assessment produced. If the LLM call fails, a placeholder assessment
    is returned so downstream stages can continue with degraded context.
    """
    log.info("Stage 1: introspection — scanning %s", root)
    scan_report = scan(
        root,
        max_file_bytes=settings.max_file_bytes,
        min_content_bytes=settings.min_content_bytes,
    )
    log.info(
        "Scan complete: %d in-scope, %d skipped (excluded %d, min-bytes %d, unreadable %d)",
        len(scan_report.in_scope),
        len(scan_report.skipped_excluded) + len(scan_report.skipped_min_bytes) + len(scan_report.skipped_unreadable),
        len(scan_report.skipped_excluded),
        len(scan_report.skipped_min_bytes),
        len(scan_report.skipped_unreadable),
    )

    summary = summarize(scan_report, root=root, depth=settings.introspection_depth)

    extensions = ", ".join(f"{ext}={count}" for ext, count in list(summary.extension_distribution.items())[:20])
    manifests = ", ".join(summary.manifest_presence) or "<none>"
    samples = "\n      - " + "\n      - ".join(summary.sample_paths) if summary.sample_paths else " <none>"

    prompt = INTROSPECTION_USER.format(
        tree=summary.tree_outline,
        file_count=summary.file_count,
        total_bytes=summary.total_bytes,
        extension_distribution=extensions,
        manifests=manifests,
        samples=samples,
    )

    try:
        assessment = request_structured(
            provider,
            prompt=prompt,
            system=SYSTEM_BASE,
            model_cls=IntrospectionAssessment,
            think=settings.think_payload(),
        )
    except ProviderError as exc:
        log.warning("Introspection LLM call failed (%s) — falling back to empty assessment.", exc)
        assessment = IntrospectionAssessment(
            primary_languages=[],
            inferred_purpose="",
            classification_rationale=f"Assessment unavailable: {exc}",
            in_scope_globs=[],
            out_of_scope_globs=[],
            notable_manifests=summary.manifest_presence,
        )

    return scan_report, summary, assessment
