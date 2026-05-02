"""Content-addressed cache for the walk pipeline.

The cache turns a clean re-walk of a 50k-file legacy monorepo from "hours"
to "minutes-of-changed-files-only". Two scopes are persisted:

- **Per-file extraction cache.** Keyed by ``(rel_path, file_fingerprint)``,
  values are the list of structured findings the extractor produced. If a
  file's bytes haven't changed since the last walk the cache entry is
  reused verbatim and no LLM call is made.
- **Per-section aggregation cache.** Keyed by the SHA-256 of the section's
  full notes payload (after extraction completes). If the notes payload
  is bit-identical to last walk's, the cached markdown body is reused
  rather than calling the aggregator again.

Resumability falls out of the per-file cache for free: a walk that crashes
at file 8127/10000 picks up exactly where it left off because the previous
8126 files' fingerprints are still in the cache from the last successful
extraction call.

Cache files live under ``.wikifi/.cache/`` so they share the wiki's
git-ignore rules but stay out of the section markdown that *is* committed.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from wikifi.wiki import WikiLayout

log = logging.getLogger("wikifi.cache")

CACHE_DIRNAME = ".cache"
EXTRACTION_CACHE_FILENAME = "extraction.json"
AGGREGATION_CACHE_FILENAME = "aggregation.json"
CACHE_VERSION = 1  # bump to invalidate every cache entry across upgrades


@dataclass
class CachedFindings:
    """Per-file findings recovered from cache."""

    fingerprint: str
    findings: list[dict[str, Any]]
    summary: str = ""
    chunks_processed: int = 0


@dataclass
class CachedSection:
    """Per-section aggregator output recovered from cache."""

    notes_hash: str
    body: str
    claims: list[dict[str, Any]] = field(default_factory=list)
    contradictions: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class WalkCache:
    """Mutable in-memory view of both caches; persisted via :func:`save`."""

    extraction: dict[str, CachedFindings] = field(default_factory=dict)
    aggregation: dict[str, CachedSection] = field(default_factory=dict)
    extraction_hits: int = 0
    extraction_misses: int = 0
    aggregation_hits: int = 0
    aggregation_misses: int = 0

    # ----- extraction scope -----

    def lookup_extraction(self, rel_path: str, fingerprint: str) -> CachedFindings | None:
        entry = self.extraction.get(rel_path)
        if entry is None or entry.fingerprint != fingerprint:
            self.extraction_misses += 1
            return None
        self.extraction_hits += 1
        return entry

    def record_extraction(
        self,
        rel_path: str,
        *,
        fingerprint: str,
        findings: list[dict[str, Any]],
        summary: str,
        chunks_processed: int,
    ) -> None:
        self.extraction[rel_path] = CachedFindings(
            fingerprint=fingerprint,
            findings=list(findings),
            summary=summary,
            chunks_processed=chunks_processed,
        )

    def forget_extraction(self, rel_path: str) -> None:
        self.extraction.pop(rel_path, None)

    def prune_extraction(self, *, keep: set[str]) -> int:
        """Drop cache entries for files no longer in scope. Returns count removed."""
        removed = [path for path in list(self.extraction) if path not in keep]
        for path in removed:
            del self.extraction[path]
        return len(removed)

    # ----- aggregation scope -----

    def lookup_aggregation(self, section_id: str, notes_hash: str) -> CachedSection | None:
        entry = self.aggregation.get(section_id)
        if entry is None or entry.notes_hash != notes_hash:
            self.aggregation_misses += 1
            return None
        self.aggregation_hits += 1
        return entry

    def record_aggregation(
        self,
        section_id: str,
        *,
        notes_hash: str,
        body: str,
        claims: list[dict[str, Any]] | None = None,
        contradictions: list[dict[str, Any]] | None = None,
    ) -> None:
        self.aggregation[section_id] = CachedSection(
            notes_hash=notes_hash,
            body=body,
            claims=list(claims or []),
            contradictions=list(contradictions or []),
        )


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def cache_dir(layout: WikiLayout) -> Path:
    return layout.wiki_dir / CACHE_DIRNAME


def extraction_cache_path(layout: WikiLayout) -> Path:
    return cache_dir(layout) / EXTRACTION_CACHE_FILENAME


def aggregation_cache_path(layout: WikiLayout) -> Path:
    return cache_dir(layout) / AGGREGATION_CACHE_FILENAME


def load(layout: WikiLayout) -> WalkCache:
    """Load both caches from disk. Missing or invalid files yield an empty cache."""
    cache = WalkCache()
    cache.extraction = _load_extraction(extraction_cache_path(layout))
    cache.aggregation = _load_aggregation(aggregation_cache_path(layout))
    return cache


def save(layout: WikiLayout, cache: WalkCache) -> None:
    """Persist both caches atomically."""
    cache_dir(layout).mkdir(parents=True, exist_ok=True)
    _atomic_write_json(
        extraction_cache_path(layout),
        {
            "version": CACHE_VERSION,
            "saved_at": datetime.now(UTC).isoformat(),
            "entries": {
                path: {
                    "fingerprint": entry.fingerprint,
                    "summary": entry.summary,
                    "chunks_processed": entry.chunks_processed,
                    "findings": entry.findings,
                }
                for path, entry in cache.extraction.items()
            },
        },
    )
    _atomic_write_json(
        aggregation_cache_path(layout),
        {
            "version": CACHE_VERSION,
            "saved_at": datetime.now(UTC).isoformat(),
            "entries": {
                sid: {
                    "notes_hash": entry.notes_hash,
                    "body": entry.body,
                    "claims": entry.claims,
                    "contradictions": entry.contradictions,
                }
                for sid, entry in cache.aggregation.items()
            },
        },
    )


def reset(layout: WikiLayout) -> None:
    """Delete every cache file. Triggered by `walk --no-cache` and tests."""
    for path in (extraction_cache_path(layout), aggregation_cache_path(layout)):
        if path.exists():
            path.unlink()


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _load_extraction(path: Path) -> dict[str, CachedFindings]:
    raw = _load_json(path)
    if not raw or raw.get("version") != CACHE_VERSION:
        return {}
    out: dict[str, CachedFindings] = {}
    for rel, entry in raw.get("entries", {}).items():
        try:
            out[rel] = CachedFindings(
                fingerprint=entry["fingerprint"],
                findings=list(entry.get("findings", [])),
                summary=entry.get("summary", ""),
                chunks_processed=int(entry.get("chunks_processed", 0)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            log.warning("dropping malformed extraction cache entry %s: %s", rel, exc)
    return out


def _load_aggregation(path: Path) -> dict[str, CachedSection]:
    raw = _load_json(path)
    if not raw or raw.get("version") != CACHE_VERSION:
        return {}
    out: dict[str, CachedSection] = {}
    for sid, entry in raw.get("entries", {}).items():
        try:
            out[sid] = CachedSection(
                notes_hash=entry["notes_hash"],
                body=entry.get("body", ""),
                claims=list(entry.get("claims", [])),
                contradictions=list(entry.get("contradictions", [])),
            )
        except (KeyError, TypeError, ValueError) as exc:
            log.warning("dropping malformed aggregation cache entry %s: %s", sid, exc)
    return out


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("could not load cache at %s: %s; starting fresh", path, exc)
        return None


# ---------------------------------------------------------------------------
# Hash helpers used at the section boundary
# ---------------------------------------------------------------------------


def hash_section_notes(notes: list[dict[str, Any]]) -> str:
    """Stable digest of a section's note payload for aggregation cache keys.

    The hash spans the *content* fields the aggregator and renderer
    actually rely on — file ref, summary, finding text, and the
    structured ``sources`` list (file/lines/fingerprint per source).
    Including ``sources`` is what keeps citation freshness honest:
    when a referenced file's lines move or its fingerprint changes,
    the cache misses and we re-aggregate against the new evidence
    instead of replaying stale citations.
    """
    from wikifi.fingerprint import hash_text

    payload = [
        {
            "file": n.get("file", ""),
            "summary": n.get("summary", ""),
            "finding": n.get("finding", ""),
            "sources": _normalize_sources(n.get("sources")),
        }
        for n in notes
    ]
    return hash_text(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def _normalize_sources(sources: Any) -> list[dict[str, Any]]:
    """Render the ``sources`` list into a stable dict shape for hashing.

    Notes vary in how ``sources`` is stored — a list of dicts from the
    JSONL store, a list of Pydantic models from in-memory paths, or
    missing entirely on legacy notes. Coerce each entry to the same
    ``{file, lines, fingerprint}`` shape so the hash is stable across
    code paths.
    """
    if not sources:
        return []
    out: list[dict[str, Any]] = []
    for src in sources:
        if isinstance(src, dict):
            file = src.get("file", "")
            lines = src.get("lines")
            fingerprint = src.get("fingerprint", "")
        else:
            file = getattr(src, "file", "")
            lines = getattr(src, "lines", None)
            fingerprint = getattr(src, "fingerprint", "")
        # Tuples and lists both serialize the same in JSON, but coerce
        # to a list so two notes with identical (start, end) ranges
        # produce identical bytes regardless of representation.
        normalized_lines: list[int] | None
        if lines is None:
            normalized_lines = None
        else:
            try:
                normalized_lines = [int(lines[0]), int(lines[1])]
            except (TypeError, ValueError, IndexError):
                normalized_lines = None
        out.append({"file": file, "lines": normalized_lines, "fingerprint": fingerprint or ""})
    return out
