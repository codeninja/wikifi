from __future__ import annotations

import fnmatch
import hashlib
from collections import Counter
from pathlib import Path

from wikifi.constants import (
    IMMUTABLE_EXCLUDED_DIRS,
    IMMUTABLE_EXCLUDED_FILE_PATTERNS,
    PRODUCTION_EXTENSIONS,
    STRUCTURAL_FILENAMES,
    TEST_FILE_PATTERNS,
    TEST_PATH_PARTS,
)
from wikifi.models import DirectorySummary, Settings, SkippedFile, SourceFile


def discover_source_files(
    root: Path, settings: Settings
) -> tuple[DirectorySummary, tuple[SourceFile, ...], tuple[SkippedFile, ...]]:
    root = root.resolve()
    skipped: list[SkippedFile] = []
    selected: list[SourceFile] = []
    extension_counts: Counter[str] = Counter()
    manifest_files: list[str] = []
    documentation_files: list[str] = []
    total_size = 0
    file_count = 0

    for path in sorted(root.rglob("*")):
        if path.is_dir():
            continue
        relative = path.relative_to(root).as_posix()
        if _is_excluded_path(path, root, settings):
            skipped.append(_skipped(path, root, "excluded_path"))
            continue

        try:
            size = path.stat().st_size
        except OSError:
            skipped.append(SkippedFile(relative_path=relative, reason="unreadable_metadata"))
            continue

        file_count += 1
        total_size += size
        extension_counts[path.suffix.lower() or "[none]"] += 1

        if path.name in STRUCTURAL_FILENAMES:
            manifest_files.append(relative)
            if path.suffix.lower() in {".md", ".rst", ".txt"}:
                documentation_files.append(relative)

        if not _is_candidate_source(path, root):
            skipped.append(SkippedFile(relative_path=relative, reason="non_production_artifact", size_bytes=size))
            continue

        source = _read_source(path, root, size, settings)
        if isinstance(source, SkippedFile):
            skipped.append(source)
            continue
        selected.append(source)

    skipped_counts = Counter(item.reason for item in skipped)
    top_level_entries = tuple(sorted(item.name for item in root.iterdir() if item.name not in IMMUTABLE_EXCLUDED_DIRS))
    summary = DirectorySummary(
        root=root.as_posix(),
        file_count=file_count,
        total_size_bytes=total_size,
        extension_distribution=dict(sorted(extension_counts.items())),
        manifest_files=tuple(sorted(manifest_files)),
        documentation_files=tuple(sorted(documentation_files)),
        top_level_entries=top_level_entries,
        selected_file_count=len(selected),
        skipped_counts=dict(sorted(skipped_counts.items())),
    )
    return summary, tuple(selected), tuple(skipped)


def _read_source(path: Path, root: Path, size: int, settings: Settings) -> SourceFile | SkippedFile:
    relative = path.relative_to(root).as_posix()
    try:
        raw = path.read_bytes()
    except OSError:
        return SkippedFile(relative_path=relative, reason="unreadable_content", size_bytes=size)

    truncated = len(raw) > settings.max_file_bytes
    raw = raw[: settings.max_file_bytes]
    if _looks_binary(raw):
        return SkippedFile(relative_path=relative, reason="binary_content", size_bytes=size)
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError:
        content = raw.decode("utf-8", errors="replace")

    if len(content.strip().encode("utf-8")) < settings.min_content_bytes:
        return SkippedFile(relative_path=relative, reason="near_empty_content", size_bytes=size)

    digest = hashlib.sha256(raw).hexdigest()
    return SourceFile(
        path=path,
        relative_path=relative,
        size_bytes=size,
        content=content,
        truncated=truncated,
        digest=digest,
    )


def _is_excluded_path(path: Path, root: Path, settings: Settings) -> bool:
    parts = path.relative_to(root).parts
    for part in parts[:-1]:
        if part in IMMUTABLE_EXCLUDED_DIRS or (part.startswith(".") and part not in {".well-known"}):
            return True
    relative = path.relative_to(root).as_posix()
    name = path.name
    patterns = (*IMMUTABLE_EXCLUDED_FILE_PATTERNS, *settings.exclude_patterns)
    return any(fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(relative, pattern) for pattern in patterns)


def _is_candidate_source(path: Path, root: Path) -> bool:
    relative_parts = set(path.relative_to(root).parts[:-1])
    if relative_parts & TEST_PATH_PARTS:
        return False
    if any(fnmatch.fnmatch(path.name, pattern) for pattern in TEST_FILE_PATTERNS):
        return False
    if path.name in STRUCTURAL_FILENAMES:
        return False
    return path.suffix.lower() in PRODUCTION_EXTENSIONS


def _looks_binary(raw: bytes) -> bool:
    return b"\x00" in raw[:2048]


def _skipped(path: Path, root: Path, reason: str) -> SkippedFile:
    try:
        size = path.stat().st_size
    except OSError:
        size = 0
    return SkippedFile(relative_path=path.relative_to(root).as_posix(), reason=reason, size_bytes=size)
