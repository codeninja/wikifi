"""Content-addressed cache for the walk pipeline.

The cache turns a clean re-walk of a 50k-file legacy monorepo from "hours"
to "minutes-of-changed-files-only". Four scopes are persisted, each in its
own file under ``.wikifi/.cache/``:

- **Per-file extraction cache.** Keyed by ``(rel_path, file_fingerprint)``,
  values are the list of structured findings the extractor produced. If a
  file's bytes haven't changed since the last walk the cache entry is
  reused verbatim and no LLM call is made.
- **Per-section aggregation cache.** Keyed by the SHA-256 of the section's
  full notes payload (after extraction completes). If the notes payload
  is bit-identical to last walk's, the cached markdown body is reused
  rather than calling the aggregator again.
- **Per-section derivation cache.** Keyed by the SHA-256 of the derivative
  section's upstream-body payload. Same role as aggregation, but for
  Stage 4 (personas, user_stories, diagrams).
- **Introspection cache.** Single entry — the prior walk's Stage 1
  result, with a stable hash of the include/exclude scope. The
  orchestrator uses this to decide whether the walk can short-circuit
  stages 3 & 4 entirely when nothing changed.

Resumability falls out of the per-file cache for free: a walk that crashes
at file 8127/10000 picks up exactly where it left off because the previous
8126 files' fingerprints are still in the cache from the last successful
extraction call. Aggregation and derivation gain the same property as long
as they persist incrementally — see :func:`save_aggregation` /
:func:`save_derivation`, the per-stage helpers wired through the
orchestrator's persist callback.

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

from wikifi.wiki import CACHE_DIRNAME, WikiLayout

log = logging.getLogger("wikifi.cache")

EXTRACTION_CACHE_FILENAME = "extraction.json"
AGGREGATION_CACHE_FILENAME = "aggregation.json"
DERIVATION_CACHE_FILENAME = "derivation.json"
INTROSPECTION_CACHE_FILENAME = "introspection.json"
# Cache schema version, bumped to invalidate every entry across upgrades:
# v1 → v2: stages 3 & 4 gained incremental persistence; derivation +
#          introspection caches added.
# v2 → v3: ``CachedSection.finding_ids`` added so the aggregator can
#          classify per-section deltas (added / removed findings) and
#          choose between cache-hit, surgical-edit, and full-rewrite
#          paths instead of always rewriting on any note change.
# Older entries load to empty so an upgraded wiki re-extracts on the
# first walk; subsequent walks pick up the new behavior.
CACHE_VERSION = 3

# Re-exposed for callers that already import ``CACHE_DIRNAME`` from this
# module; the constant itself lives in :mod:`wikifi.wiki` next to the
# other layout names.
__all__ = [
    "AGGREGATION_CACHE_FILENAME",
    "CACHE_DIRNAME",
    "CACHE_VERSION",
    "CachedDerivation",
    "CachedFindings",
    "CachedIntrospection",
    "CachedSection",
    "DERIVATION_CACHE_FILENAME",
    "EXTRACTION_CACHE_FILENAME",
    "INTROSPECTION_CACHE_FILENAME",
    "WalkCache",
    "aggregation_cache_path",
    "cache_dir",
    "compute_finding_id",
    "derivation_cache_path",
    "extraction_cache_path",
    "hash_introspection_scope",
    "hash_section_notes",
    "hash_upstream_bodies",
    "introspection_cache_path",
    "load",
    "note_finding_ids",
    "reset",
    "save",
    "save_aggregation",
    "save_derivation",
    "save_extraction",
    "save_introspection",
]


@dataclass
class CachedFindings:
    """Per-file findings recovered from cache."""

    fingerprint: str
    findings: list[dict[str, Any]]
    summary: str = ""
    chunks_processed: int = 0


@dataclass
class CachedSection:
    """Per-section aggregator output recovered from cache.

    ``finding_ids`` is the ordered list of stable per-note ids (see
    :func:`compute_finding_id`) that fed into the cached body, aligned
    with the notes' position so a 1-based ``claim.source_indices``
    entry maps to ``finding_ids[idx - 1]``. Surgical aggregation uses
    this to detect which findings were added or removed between walks
    and route an edit instead of a full rewrite.
    """

    notes_hash: str
    body: str
    claims: list[dict[str, Any]] = field(default_factory=list)
    contradictions: list[dict[str, Any]] = field(default_factory=list)
    finding_ids: list[str] = field(default_factory=list)


@dataclass
class CachedDerivation:
    """Per-section deriver output recovered from cache.

    ``upstream_hash`` covers the concatenated bodies of the upstream
    primary sections this derivative was synthesized from. ``revised``
    records whether the critic + reviser loop ran on this body — true
    even when the critic accepted the draft unchanged.

    The asymmetry the lookup enforces (see :meth:`WalkCache.lookup_derivation`):
    a cached body that has *not* been through review is rejected when
    the current walk asks for ``--review`` (the user explicitly opted
    in to the critic loop, so we owe them the loop). The inverse —
    reusing a reviewed cached body on a walk that runs without review —
    is fine, since a reviewed body is strictly higher quality.
    """

    upstream_hash: str
    body: str
    revised: bool = False


@dataclass
class CachedIntrospection:
    """The prior walk's Stage 1 result, used for the short-circuit check.

    ``scope_hash`` is computed from ``(include, exclude)`` only — those
    are what shape extraction. ``primary_languages`` and ``rationale``
    are descriptive and would otherwise cause spurious scope-change
    detections from one-token model variations.
    """

    scope_hash: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class WalkCache:
    """Mutable in-memory view of every cache scope; persisted via :func:`save`."""

    extraction: dict[str, CachedFindings] = field(default_factory=dict)
    aggregation: dict[str, CachedSection] = field(default_factory=dict)
    derivation: dict[str, CachedDerivation] = field(default_factory=dict)
    introspection: CachedIntrospection | None = None
    extraction_hits: int = 0
    extraction_misses: int = 0
    aggregation_hits: int = 0
    aggregation_misses: int = 0
    derivation_hits: int = 0
    derivation_misses: int = 0

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
        finding_ids: list[str] | None = None,
    ) -> None:
        self.aggregation[section_id] = CachedSection(
            notes_hash=notes_hash,
            body=body,
            claims=list(claims or []),
            contradictions=list(contradictions or []),
            finding_ids=list(finding_ids or []),
        )

    # ----- derivation scope -----

    def lookup_derivation(
        self, section_id: str, upstream_hash: str, *, expect_revised: bool
    ) -> CachedDerivation | None:
        """Return the cached derivative body when upstreams + review mode match.

        ``expect_revised`` is ``True`` when the current walk was invoked
        with ``--review``. A non-revised cached body is rejected in that
        case so the user actually gets the critic loop they asked for;
        the inverse case (cached revised body, walk invoked without
        review) is fine — the revised body is strictly higher quality.
        """
        entry = self.derivation.get(section_id)
        if entry is None or entry.upstream_hash != upstream_hash:
            self.derivation_misses += 1
            return None
        if expect_revised and not entry.revised:
            self.derivation_misses += 1
            return None
        self.derivation_hits += 1
        return entry

    def record_derivation(
        self,
        section_id: str,
        *,
        upstream_hash: str,
        body: str,
        revised: bool,
    ) -> None:
        self.derivation[section_id] = CachedDerivation(upstream_hash=upstream_hash, body=body, revised=revised)

    # ----- introspection scope -----

    def lookup_introspection(self, scope_hash: str) -> CachedIntrospection | None:
        if self.introspection is None or self.introspection.scope_hash != scope_hash:
            return None
        return self.introspection

    def record_introspection(self, *, scope_hash: str, payload: dict[str, Any]) -> None:
        self.introspection = CachedIntrospection(scope_hash=scope_hash, payload=dict(payload))


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def cache_dir(layout: WikiLayout) -> Path:
    return layout.cache_dir


def extraction_cache_path(layout: WikiLayout) -> Path:
    return cache_dir(layout) / EXTRACTION_CACHE_FILENAME


def aggregation_cache_path(layout: WikiLayout) -> Path:
    return cache_dir(layout) / AGGREGATION_CACHE_FILENAME


def derivation_cache_path(layout: WikiLayout) -> Path:
    return cache_dir(layout) / DERIVATION_CACHE_FILENAME


def introspection_cache_path(layout: WikiLayout) -> Path:
    return cache_dir(layout) / INTROSPECTION_CACHE_FILENAME


def load(layout: WikiLayout) -> WalkCache:
    """Load every cache scope from disk. Missing or invalid files yield empty entries."""
    cache = WalkCache()
    cache.extraction = _load_extraction(extraction_cache_path(layout))
    cache.aggregation = _load_aggregation(aggregation_cache_path(layout))
    cache.derivation = _load_derivation(derivation_cache_path(layout))
    cache.introspection = _load_introspection(introspection_cache_path(layout))
    return cache


def save(layout: WikiLayout, cache: WalkCache) -> None:
    """Persist every cache scope atomically."""
    cache_dir(layout).mkdir(parents=True, exist_ok=True)
    save_extraction(layout, cache)
    save_aggregation(layout, cache)
    save_derivation(layout, cache)
    save_introspection(layout, cache)


def save_extraction(layout: WikiLayout, cache: WalkCache) -> None:
    """Persist only the extraction scope. Used by stage 2's per-file callback."""
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


def save_aggregation(layout: WikiLayout, cache: WalkCache) -> None:
    """Persist only the aggregation scope. Used by stage 3's per-section callback.

    Splitting the per-stage save out of :func:`save` means a stage 3
    interruption no longer rewinds the wiki to the state captured at the
    end of stage 2 — every successful section's body and notes_hash are
    on disk before the next section starts.
    """
    cache_dir(layout).mkdir(parents=True, exist_ok=True)
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
                    "finding_ids": entry.finding_ids,
                }
                for sid, entry in cache.aggregation.items()
            },
        },
    )


def save_derivation(layout: WikiLayout, cache: WalkCache) -> None:
    """Persist only the derivation scope. Used by stage 4's per-section callback."""
    cache_dir(layout).mkdir(parents=True, exist_ok=True)
    _atomic_write_json(
        derivation_cache_path(layout),
        {
            "version": CACHE_VERSION,
            "saved_at": datetime.now(UTC).isoformat(),
            "entries": {
                sid: {
                    "upstream_hash": entry.upstream_hash,
                    "body": entry.body,
                    "revised": entry.revised,
                }
                for sid, entry in cache.derivation.items()
            },
        },
    )


def save_introspection(layout: WikiLayout, cache: WalkCache) -> None:
    """Persist only the introspection scope. Used by stage 1."""
    if cache.introspection is None:
        return
    cache_dir(layout).mkdir(parents=True, exist_ok=True)
    _atomic_write_json(
        introspection_cache_path(layout),
        {
            "version": CACHE_VERSION,
            "saved_at": datetime.now(UTC).isoformat(),
            "scope_hash": cache.introspection.scope_hash,
            "payload": cache.introspection.payload,
        },
    )


def reset(layout: WikiLayout) -> None:
    """Delete every cache file. Triggered by `walk --no-cache` and tests."""
    for path in (
        extraction_cache_path(layout),
        aggregation_cache_path(layout),
        derivation_cache_path(layout),
        introspection_cache_path(layout),
    ):
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
                finding_ids=[str(fid) for fid in entry.get("finding_ids", [])],
            )
        except (KeyError, TypeError, ValueError) as exc:
            log.warning("dropping malformed aggregation cache entry %s: %s", sid, exc)
    return out


def _load_derivation(path: Path) -> dict[str, CachedDerivation]:
    raw = _load_json(path)
    if not raw or raw.get("version") != CACHE_VERSION:
        return {}
    out: dict[str, CachedDerivation] = {}
    for sid, entry in raw.get("entries", {}).items():
        try:
            out[sid] = CachedDerivation(
                upstream_hash=entry["upstream_hash"],
                body=entry.get("body", ""),
                revised=bool(entry.get("revised", False)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            log.warning("dropping malformed derivation cache entry %s: %s", sid, exc)
    return out


def _load_introspection(path: Path) -> CachedIntrospection | None:
    raw = _load_json(path)
    if not raw or raw.get("version") != CACHE_VERSION:
        return None
    try:
        return CachedIntrospection(
            scope_hash=raw["scope_hash"],
            payload=dict(raw.get("payload", {})),
        )
    except (KeyError, TypeError, ValueError) as exc:
        log.warning("dropping malformed introspection cache: %s", exc)
        return None


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("could not load cache at %s: %s; starting fresh", path, exc)
        return None


# ---------------------------------------------------------------------------
# Hash helpers used at stage boundaries
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


def hash_upstream_bodies(upstream_bodies: dict[str, str]) -> str:
    """Stable digest of the upstream-section bodies a derivation will consume.

    Keys (section ids) are sorted so iteration order doesn't shift the
    hash between Python versions or dict insertion patterns. Bodies are
    hashed verbatim — when the aggregator writes a new section.md, that
    section's downstream derivations should re-derive.
    """
    from wikifi.fingerprint import hash_text

    payload = [{"section_id": sid, "body": upstream_bodies[sid]} for sid in sorted(upstream_bodies)]
    return hash_text(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def compute_finding_id(*, file: str, section_id: str, finding: str) -> str:
    """Stable identity for one note across walks.

    Composition: ``sha256(file + "::" + section_id + "::" + finding)``,
    truncated to 16 hex chars. Two walks that emit the same finding
    text from the same file targeting the same section produce the
    same id; any change in any of the three components is a fresh id.

    A reword of ``finding`` (even one character) gets a new id, which
    semantically counts as "removed-and-added" from the surgical
    aggregator's point of view — the same as a delete-plus-insert in a
    text diff. That's intentional: a paragraph the cached body wrote
    around the old wording can no longer be assumed to still be
    grounded by the new wording.
    """
    from wikifi.fingerprint import hash_text

    return hash_text(f"{file}::{section_id}::{finding}")


def note_finding_ids(notes: list[dict[str, Any]], *, section_id: str) -> list[str]:
    """Compute the ordered ``finding_id`` list for a section's notes.

    Aligned with note position so a 1-based ``claim.source_indices``
    entry maps to ``finding_ids[idx - 1]``. Notes missing ``file`` or
    ``finding`` get an empty-string id, which still preserves
    positional alignment but won't compare equal to any real id —
    surgical aggregation will treat them as always-changed and route
    around them.
    """
    return [
        compute_finding_id(
            file=str(n.get("file", "")),
            section_id=section_id,
            finding=str(n.get("finding", "")),
        )
        for n in notes
    ]


def hash_introspection_scope(*, include: list[str], exclude: list[str]) -> str:
    """Hash only the scope-defining fields of an :class:`IntrospectionResult`.

    ``primary_languages`` and ``rationale`` are descriptive — small
    model-side variations between runs would otherwise defeat the
    short-circuit even when the actual walked file set is identical.
    """
    from wikifi.fingerprint import hash_text

    payload = {"include": sorted(include), "exclude": sorted(exclude)}
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
