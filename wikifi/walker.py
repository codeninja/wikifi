"""Filesystem walking with gitignore + always-exclude defaults.

The walker is intentionally provider-free: it knows how to enumerate files and
build a directory summary, nothing about LLMs or sections. Higher layers
(`introspection`, `extractor`) call into it.

`pathspec.GitIgnoreSpec` mirrors git's ignore semantics — including the corner
cases — and is what we use to filter both `.gitignore` rules and the
extra excludes wikifi always applies (its own output dir, VCS metadata, common
dependency caches).
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

from pathspec import GitIgnoreSpec

# Always excluded regardless of .gitignore. Tuned for "things wikifi should
# never describe to a migration team" — VCS plumbing, dep caches, build output,
# and wikifi's own working dir. Add patterns conservatively; users can
# override via `--include` later.
DEFAULT_EXCLUDES: tuple[str, ...] = (
    ".git",  # matches both the directory in normal checkouts and the gitdir pointer file in worktrees
    ".git/",
    ".hg/",
    ".svn/",
    ".wikifi/",
    ".venv/",
    "venv/",
    "node_modules/",
    "__pycache__/",
    ".mypy_cache/",
    ".ruff_cache/",
    ".pytest_cache/",
    ".tox/",
    "dist/",
    "build/",
    "target/",
    ".next/",
    ".nuxt/",
    "*.pyc",
    "*.pyo",
    "*.so",
    "*.dll",
    "*.dylib",
    "*.class",
    "*.o",
    "*.a",
    "*.lock",
    "*.lockb",
    "*.min.js",
    "*.min.css",
)


@dataclass(frozen=True)
class WalkConfig:
    """How to filter the target tree.

    `extra_excludes` extends the always-on defaults with patterns supplied by
    Stage 1 (introspection's exclude list) or by the user.

    `min_content_bytes` filters near-empty files (think `__init__.py` with
    nothing but a version string). Empty inputs cause thinking-capable
    models to wander for minutes producing speculative findings, so we
    skip them before they ever hit the extractor.
    """

    root: Path
    extra_excludes: tuple[str, ...] = field(default_factory=tuple)
    respect_gitignore: bool = True
    # Absolute upper bound — files above this are treated as vendored or
    # generated noise and skipped entirely. Real source files (even
    # monolithic ones) fit comfortably under the default; the extractor
    # chunks anything that exceeds its per-call window rather than dropping
    # it here.
    max_file_bytes: int = 2_000_000
    min_content_bytes: int = 64


def build_spec(config: WalkConfig) -> GitIgnoreSpec:
    """Compose the ignore spec from defaults, root .gitignore, and extra excludes."""
    lines: list[str] = list(DEFAULT_EXCLUDES)
    if config.respect_gitignore:
        gi = config.root / ".gitignore"
        if gi.exists():
            lines.extend(gi.read_text(encoding="utf-8").splitlines())
    lines.extend(config.extra_excludes)
    return GitIgnoreSpec.from_lines(lines)


def iter_files(config: WalkConfig) -> Iterator[Path]:
    """Yield repo-relative paths of files that should be analyzed.

    Filters applied (in order, so cheapest checks fail fast):

    1. Path matches a default-exclude / gitignore / introspection-exclude →
       skip.
    2. Size > ``max_file_bytes`` → skip (likely generated, vendored, or asset).
       Real source files — even monolithic ones — are expected to fit; the
       extractor chunks anything bigger than its per-call window.
    3. Stripped content < ``min_content_bytes`` → skip (likely a stub
       ``__init__.py``, a one-liner config, or an empty file). Tiny inputs
       cause thinking-capable models to invent findings or run away on the
       reasoning trace; not worth analyzing either way.
    """
    spec = build_spec(config)
    for path in _walk(config.root, spec):
        try:
            stat = path.stat()
        except OSError:
            continue
        if stat.st_size > config.max_file_bytes:
            continue
        if config.min_content_bytes > 0:
            try:
                stripped = path.read_text(encoding="utf-8", errors="replace").strip()
            except OSError:
                continue
            if len(stripped) < config.min_content_bytes:
                continue
        yield path.relative_to(config.root)


def _walk(root: Path, spec: GitIgnoreSpec) -> Iterator[Path]:
    """Depth-first walk that prunes ignored directories before descending."""
    stack: list[Path] = [root]
    while stack:
        current = stack.pop()
        try:
            entries = sorted(current.iterdir())
        except (OSError, PermissionError):
            continue
        for entry in entries:
            rel = entry.relative_to(root).as_posix()
            if entry.is_dir():
                # Match against directory form so patterns like `.venv/` work.
                if spec.match_file(rel + "/"):
                    continue
                stack.append(entry)
            elif entry.is_file():
                if spec.match_file(rel):
                    continue
                yield entry


@dataclass(frozen=True)
class DirSummary:
    """Aggregate stats for a single directory (non-recursive)."""

    rel_path: str  # "" for root
    file_count: int
    total_bytes: int
    extensions: dict[str, int]  # extension → count, top 10 by count
    notable_files: tuple[str, ...]  # manifest / readme filenames present


def summarize_tree(config: WalkConfig, *, max_depth: int) -> list[DirSummary]:
    """Return a directory summary, depth-limited, in pre-order.

    Used as the structural input to the Stage 1 introspection LLM pass: the
    model sees a compressed view of the repo and decides which areas warrant
    a deterministic walk.
    """
    spec = build_spec(config)
    summaries: list[DirSummary] = []
    _summarize_recursive(config.root, config.root, spec, depth=0, max_depth=max_depth, out=summaries)
    return summaries


def _summarize_recursive(
    root: Path,
    current: Path,
    spec: GitIgnoreSpec,
    *,
    depth: int,
    max_depth: int,
    out: list[DirSummary],
) -> None:
    if depth > max_depth:
        return
    try:
        entries = sorted(current.iterdir())
    except (OSError, PermissionError):
        return

    file_count = 0
    total_bytes = 0
    ext_counts: dict[str, int] = {}
    notable: list[str] = []
    subdirs: list[Path] = []

    for entry in entries:
        rel = entry.relative_to(root).as_posix()
        if entry.is_dir():
            if spec.match_file(rel + "/"):
                continue
            subdirs.append(entry)
        elif entry.is_file():
            if spec.match_file(rel):
                continue
            file_count += 1
            try:
                total_bytes += entry.stat().st_size
            except OSError:
                pass
            ext = entry.suffix.lower() or "<noext>"
            ext_counts[ext] = ext_counts.get(ext, 0) + 1
            if _is_notable(entry.name):
                notable.append(entry.name)

    rel_path = current.relative_to(root).as_posix() if current != root else ""
    top_exts = dict(sorted(ext_counts.items(), key=lambda kv: kv[1], reverse=True)[:10])
    out.append(
        DirSummary(
            rel_path=rel_path,
            file_count=file_count,
            total_bytes=total_bytes,
            extensions=top_exts,
            notable_files=tuple(notable),
        )
    )

    for sub in subdirs:
        _summarize_recursive(root, sub, spec, depth=depth + 1, max_depth=max_depth, out=out)


_NOTABLE_NAMES = frozenset(
    {
        "pyproject.toml",
        "setup.py",
        "setup.cfg",
        "requirements.txt",
        "Pipfile",
        "poetry.lock",
        "package.json",
        "pnpm-workspace.yaml",
        "Cargo.toml",
        "go.mod",
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
        "Gemfile",
        "composer.json",
        "Dockerfile",
        "docker-compose.yml",
        "Makefile",
        "README.md",
        "README.rst",
        "VISION.md",
        "ARCHITECTURE.md",
        "CHANGELOG.md",
    }
)


def _is_notable(name: str) -> bool:
    return name in _NOTABLE_NAMES


def read_manifest_files(config: WalkConfig, *, paths: Iterable[str], max_bytes: int = 20_000) -> dict[str, str]:
    """Read a small set of manifest/readme files for inclusion in the introspection prompt."""
    out: dict[str, str] = {}
    for rel in paths:
        candidate = config.root / rel
        if not candidate.is_file():
            continue
        try:
            data = candidate.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if len(data) > max_bytes:
            data = data[:max_bytes] + "\n... [truncated]\n"
        out[rel] = data
    return out
