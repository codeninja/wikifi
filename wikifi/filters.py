"""File-system traversal and filtering for the introspection stage."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern

# Permanently-excluded directories. Hard-spec: VCS metadata, dependency caches,
# build artifacts, and tool-specific directories never enter traversal.
# Per VISION.md scope boundary, test infrastructure and dev tooling
# directories are also excluded — wikifi targets production intent.
HARD_EXCLUDED_DIRS: frozenset[str] = frozenset(
    {
        # VCS metadata
        ".git",
        ".hg",
        ".svn",
        ".bzr",
        # Editor/IDE
        ".idea",
        ".vscode",
        # Tool caches
        ".ruff_cache",
        ".pytest_cache",
        ".mypy_cache",
        ".tox",
        ".nox",
        # Python envs
        ".venv",
        "venv",
        "env",
        ".env",
        ".uv",
        "__pycache__",
        # JS deps + caches
        "node_modules",
        ".next",
        ".nuxt",
        ".cache",
        # Build artefacts
        "dist",
        "build",
        "target",
        ".gradle",
        ".terraform",
        "out",
        "coverage",
        ".coverage",
        "htmlcov",
        # Agent state / local config
        ".claude",
        ".wikifi",
        # Repo plumbing — not production intent
        ".github",
        ".githooks",
        ".gitlab",
        ".circleci",
        ".azure-pipelines",
        # Spec mirror — never feed our own benchmark spec back to the LLM.
        ".spec",
        # Tests — per scope boundary, unless something is truly remarkable.
        "tests",
        "test",
        "__tests__",
        "specs",
        "spec",
    }
)

# Files that should never enter the extraction pipeline regardless of
# extension — lockfiles, generated artefacts, repo plumbing.
HARD_EXCLUDED_FILES: frozenset[str] = frozenset(
    {
        # Worktree pointer (looks like a file, not a dir)
        ".git",
        ".gitignore",
        ".gitattributes",
        ".gitmodules",
        ".dockerignore",
        ".editorconfig",
        # Lockfiles — high size, zero business intent
        "uv.lock",
        "poetry.lock",
        "Pipfile.lock",
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "Cargo.lock",
        "Gemfile.lock",
        "composer.lock",
        "go.sum",
        # Build / CI tooling — explicitly out of scope per spec.
        "Makefile",
        "Dockerfile",
        "docker-compose.yml",
        "docker-compose.yaml",
        "Procfile",
    }
)

NOTABLE_MANIFESTS: frozenset[str] = frozenset(
    {
        "pyproject.toml",
        "setup.py",
        "setup.cfg",
        "requirements.txt",
        "Pipfile",
        "poetry.lock",
        "uv.lock",
        "package.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "package-lock.json",
        "tsconfig.json",
        "go.mod",
        "go.sum",
        "Cargo.toml",
        "Cargo.lock",
        "build.gradle",
        "pom.xml",
        "Gemfile",
        "composer.json",
        "Makefile",
        "Dockerfile",
        "docker-compose.yml",
        "docker-compose.yaml",
        "README.md",
        "VISION.md",
        "ARCHITECTURE.md",
        "CHANGELOG.md",
        "CLAUDE.md",
        "CODE-FORMAT.md",
    }
)

BINARY_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".bmp",
        ".webp",
        ".ico",
        ".pdf",
        ".zip",
        ".tar",
        ".gz",
        ".bz2",
        ".7z",
        ".rar",
        ".mp3",
        ".mp4",
        ".mov",
        ".avi",
        ".webm",
        ".wav",
        ".flac",
        ".ttf",
        ".otf",
        ".woff",
        ".woff2",
        ".eot",
        ".class",
        ".jar",
        ".war",
        ".pyc",
        ".pyo",
        ".so",
        ".dll",
        ".dylib",
        ".bin",
        ".dat",
        ".exe",
        ".o",
        ".a",
    }
)


@dataclass(slots=True)
class ScanReport:
    """Aggregate stats and full file list produced by ``scan``."""

    in_scope: list[Path] = field(default_factory=list)
    skipped_excluded: list[Path] = field(default_factory=list)
    skipped_min_bytes: list[Path] = field(default_factory=list)
    skipped_unreadable: list[Path] = field(default_factory=list)
    extension_counts: Counter[str] = field(default_factory=Counter)
    total_bytes: int = 0
    manifests_found: list[Path] = field(default_factory=list)
    files_seen: int = 0


def load_gitignore(root: Path) -> PathSpec:
    """Combine the repo's ``.gitignore`` with the wikifi-managed
    ``.wikifi/.gitignore`` (when present). Missing files are tolerated.
    """
    patterns: list[str] = []
    for relative in (".gitignore", ".wikifi/.gitignore"):
        path = root / relative
        if path.is_file():
            try:
                patterns.extend(path.read_text(encoding="utf-8").splitlines())
            except OSError:
                continue
    return PathSpec.from_lines(GitWildMatchPattern, patterns)


def is_probably_binary(path: Path, sample_size: int = 2048) -> bool:
    """Cheap binary check: extension allow-list + NUL byte sniff."""
    if path.suffix.lower() in BINARY_EXTENSIONS:
        return True
    try:
        with path.open("rb") as fh:
            chunk = fh.read(sample_size)
    except OSError:
        return True
    if b"\x00" in chunk:
        return True
    return False


def stripped_size(path: Path, max_read: int = 1_000_000) -> int:
    """Bytes of the file with whitespace stripped — used for the
    min-content guard against thinking-runaway on stub files.
    """
    try:
        with path.open("rb") as fh:
            data = fh.read(max_read)
    except OSError:
        return 0
    return len(b"".join(data.split()))


def is_hard_excluded_dir(name: str) -> bool:
    return name in HARD_EXCLUDED_DIRS


def scan(
    root: Path,
    *,
    max_file_bytes: int = 200_000,
    min_content_bytes: int = 64,
    extra_spec: PathSpec | None = None,
) -> ScanReport:
    """Walk ``root`` and partition files into in-scope vs. skipped buckets.

    Hard exclusions and binary files are never opened. Files exceeding
    ``max_file_bytes`` stay in scope (extraction will truncate). Files
    whose stripped size falls below ``min_content_bytes`` are skipped to
    prevent thinking-runaway on stubs.
    """
    root = root.resolve()
    spec = load_gitignore(root)

    report = ScanReport()

    def _is_ignored(rel: Path) -> bool:
        rel_posix = rel.as_posix()
        if spec.match_file(rel_posix):
            return True
        if extra_spec is not None and extra_spec.match_file(rel_posix):
            return True
        return False

    stack: list[Path] = [root]
    while stack:
        current = stack.pop()
        try:
            entries = sorted(current.iterdir(), key=lambda p: p.name)
        except (OSError, PermissionError):
            continue

        for entry in entries:
            try:
                rel = entry.relative_to(root)
            except ValueError:
                continue

            if entry.is_symlink():
                # Don't traverse symlinks — they can produce loops or escape root.
                continue

            if entry.is_dir():
                if is_hard_excluded_dir(entry.name):
                    continue
                if _is_ignored(rel):
                    continue
                stack.append(entry)
                continue

            if not entry.is_file():
                continue

            report.files_seen += 1

            if entry.name in HARD_EXCLUDED_FILES:
                report.skipped_excluded.append(rel)
                continue

            if _is_ignored(rel):
                report.skipped_excluded.append(rel)
                continue

            if is_probably_binary(entry):
                report.skipped_excluded.append(rel)
                continue

            if entry.name in NOTABLE_MANIFESTS:
                report.manifests_found.append(rel)

            try:
                size = entry.stat().st_size
            except OSError:
                report.skipped_unreadable.append(rel)
                continue

            if stripped_size(entry) < min_content_bytes:
                report.skipped_min_bytes.append(rel)
                continue

            report.extension_counts[entry.suffix.lower() or "<none>"] += 1
            report.total_bytes += min(size, max_file_bytes)
            report.in_scope.append(rel)

    return report


def render_tree(root: Path, *, depth: int = 3, max_entries: int = 200) -> str:
    """Return an indented tree outline for the introspection prompt."""
    root = root.resolve()
    lines: list[str] = [root.name + "/"]
    counter = {"n": 0}

    def _walk(directory: Path, prefix: str, current_depth: int) -> None:
        if current_depth > depth:
            return
        try:
            entries = sorted(
                directory.iterdir(),
                key=lambda p: (not p.is_dir(), p.name.lower()),
            )
        except OSError:
            return
        for entry in entries:
            if counter["n"] >= max_entries:
                lines.append(prefix + "... (truncated)")
                return
            if entry.name.startswith(".") and entry.name not in {".github", ".env.example"}:
                continue
            if entry.is_dir() and is_hard_excluded_dir(entry.name):
                continue
            counter["n"] += 1
            marker = "/" if entry.is_dir() else ""
            lines.append(f"{prefix}{entry.name}{marker}")
            if entry.is_dir():
                _walk(entry, prefix + "  ", current_depth + 1)

    _walk(root, "  ", 1)
    return "\n".join(lines)
