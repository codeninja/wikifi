"""Lightweight static analysis of the repository.

Two outputs feed Stage 2:

1. **File classification.** Each in-scope file is tagged with a
   :class:`FileKind` (``application_code``, ``sql``, ``openapi``,
   ``protobuf``, ``graphql``, ``migration``, ``other``). Specialized
   extractors short-circuit the LLM for the structured kinds — a SQL
   DDL file becomes a precise entity diff without a 90-second model
   call. Application code falls through to the existing LLM extraction
   path, but enriched with the import graph.

2. **Import / reference graph.** A regex-driven scan builds an undirected
   neighbor map: for each file, "this file imports from these files,
   and is imported by these files". The neighbor list is injected into
   the Stage 2 prompt so per-file findings can talk about cross-file
   flows ("this handler delegates to ``services/billing.py`` for the
   order-totalling step") rather than treating each file as an island.

The implementation is deliberately language-pluralistic and relies only
on regex + path resolution. tree-sitter would give richer structure but
adds a binary dep wikifi has explicitly avoided so far; the regex graph
is good enough to surface neighbors for the LLM to reason over, which is
the only consumer that matters here.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

log = logging.getLogger("wikifi.repograph")


class FileKind(StrEnum):
    APPLICATION_CODE = "application_code"
    SQL = "sql"
    OPENAPI = "openapi"
    PROTOBUF = "protobuf"
    GRAPHQL = "graphql"
    MIGRATION = "migration"
    OTHER = "other"


# Suffixes that pin a file kind purely by extension.
_EXTENSION_KINDS: dict[str, FileKind] = {
    ".sql": FileKind.SQL,
    ".ddl": FileKind.SQL,
    ".proto": FileKind.PROTOBUF,
    ".graphql": FileKind.GRAPHQL,
    ".graphqls": FileKind.GRAPHQL,
    ".gql": FileKind.GRAPHQL,
}


_APPLICATION_EXTS: frozenset[str] = frozenset(
    {
        ".py",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".mjs",
        ".cjs",
        ".go",
        ".rs",
        ".rb",
        ".php",
        ".java",
        ".kt",
        ".kts",
        ".scala",
        ".cs",
        ".cpp",
        ".cc",
        ".c",
        ".h",
        ".hpp",
        ".swift",
        ".m",
        ".mm",
        ".dart",
        ".ex",
        ".exs",
        ".clj",
        ".cljs",
        ".lua",
    }
)


# Common conventions for migration directories (Alembic, Django, Rails,
# Knex, Flyway, Liquibase). A ``.sql`` file in any of these is a migration
# rather than a generic DDL — both kinds run through the SQL extractor
# but the migration label keeps the wiki distinguishing forward-only
# changes from current schema.
_MIGRATION_DIR_TOKENS: tuple[str, ...] = (
    "/migrations/",
    "/alembic/",
    "/db/migrate/",
    "/database/migrations/",
    "/prisma/migrations/",
    "/flyway/",
    "/liquibase/",
)


# Heuristics for OpenAPI/Swagger detection inside YAML and JSON files.
_OPENAPI_HEAD_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^\s*openapi\s*:\s*[\"']?\d", re.MULTILINE),
    re.compile(r'"openapi"\s*:\s*"\d'),
    re.compile(r"^\s*swagger\s*:\s*[\"']?\d", re.MULTILINE),
    re.compile(r'"swagger"\s*:\s*"\d'),
)


def classify(rel_path: Path, sample: str | None = None) -> FileKind:
    """Return the :class:`FileKind` for a repo-relative path.

    ``sample`` may carry the first ~4 KB of the file's contents and is
    consulted for kinds that can't be decided from the path alone (YAML
    / JSON files that may or may not be OpenAPI specs).
    """
    suffix = rel_path.suffix.lower()
    posix = rel_path.as_posix().lower()

    if suffix in _EXTENSION_KINDS:
        kind = _EXTENSION_KINDS[suffix]
        if kind is FileKind.SQL and any(token in f"/{posix}" for token in _MIGRATION_DIR_TOKENS):
            return FileKind.MIGRATION
        return kind

    if suffix in {".yml", ".yaml", ".json"} and sample is not None:
        head = sample[:4096]
        if any(pat.search(head) for pat in _OPENAPI_HEAD_PATTERNS):
            return FileKind.OPENAPI

    if suffix in _APPLICATION_EXTS:
        if any(token in f"/{posix}" for token in _MIGRATION_DIR_TOKENS):
            return FileKind.MIGRATION
        return FileKind.APPLICATION_CODE

    return FileKind.OTHER


# ---------------------------------------------------------------------------
# Import graph
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GraphNode:
    rel_path: str
    imports: tuple[str, ...]
    imported_by: tuple[str, ...]

    def neighbors(self, *, limit: int = 8) -> list[str]:
        """Combined neighbor list, capped, for prompt enrichment."""
        out: list[str] = []
        seen: set[str] = set()
        for paths in (self.imports, self.imported_by):
            for path in paths:
                if path not in seen:
                    seen.add(path)
                    out.append(path)
                if len(out) >= limit:
                    return out
        return out


@dataclass
class RepoGraph:
    """Per-file import edges across an in-scope file list."""

    nodes: dict[str, GraphNode] = field(default_factory=dict)

    def get(self, rel_path: str) -> GraphNode | None:
        return self.nodes.get(rel_path)

    def neighbor_paths(self, rel_path: str, *, limit: int = 8) -> list[str]:
        node = self.nodes.get(rel_path)
        return node.neighbors(limit=limit) if node else []

    def __contains__(self, rel_path: str) -> bool:  # pragma: no cover - convenience
        return rel_path in self.nodes


# Per-language import patterns. Each pattern captures the imported module
# path/identifier; resolution to a real file is handled by a separate
# heuristic.
_PY_IMPORT = re.compile(
    r"^\s*(?:from\s+([A-Za-z_][\w.]*)\s+import|import\s+([A-Za-z_][\w.]*))",
    re.MULTILINE,
)
_JS_IMPORT = re.compile(
    r"""(?:import\s+[^'"\n]*?from\s*['"]([^'"\n]+)['"])"""
    r"""|(?:require\(\s*['"]([^'"\n]+)['"]\s*\))"""
    r"""|(?:import\(\s*['"]([^'"\n]+)['"]\s*\))""",
)
_GO_IMPORT = re.compile(r"""import\s+(?:\([^)]*\)|\"([^\"]+)\")""", re.DOTALL)
_GO_IMPORT_BLOCK = re.compile(r"^\s*\"([^\"]+)\"", re.MULTILINE)
_JAVA_IMPORT = re.compile(r"^\s*import\s+(?:static\s+)?([\w.]+);", re.MULTILINE)
_RUBY_REQUIRE = re.compile(r"""^\s*require(?:_relative)?\s+['"]([^'"\n]+)['"]""", re.MULTILINE)


def build_graph(*, repo_root: Path, files: Iterable[Path]) -> RepoGraph:
    """Build a :class:`RepoGraph` from the supplied in-scope files.

    Files outside :data:`_APPLICATION_EXTS` contribute nothing — their
    import semantics aren't text-recoverable in any meaningful sense
    (binary, image, lockfile, etc.).
    """
    file_list = [Path(f) for f in files]
    file_set = {p.as_posix() for p in file_list}
    candidates_by_module: dict[str, list[str]] = _index_modules(file_set)

    raw_edges: dict[str, set[str]] = defaultdict(set)
    reverse: dict[str, set[str]] = defaultdict(set)

    for rel in file_list:
        full = repo_root / rel
        if rel.suffix.lower() not in _APPLICATION_EXTS:
            continue
        try:
            text = full.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        targets = _resolve_imports(rel, text, file_set=file_set, modules=candidates_by_module)
        rel_str = rel.as_posix()
        for target in targets:
            if target == rel_str:
                continue
            raw_edges[rel_str].add(target)
            reverse[target].add(rel_str)

    nodes: dict[str, GraphNode] = {}
    for rel in file_list:
        rel_str = rel.as_posix()
        nodes[rel_str] = GraphNode(
            rel_path=rel_str,
            imports=tuple(sorted(raw_edges.get(rel_str, set()))),
            imported_by=tuple(sorted(reverse.get(rel_str, set()))),
        )
    return RepoGraph(nodes=nodes)


def _index_modules(file_set: set[str]) -> dict[str, list[str]]:
    """Build module-name → candidate-paths index for resolution.

    For Python ``foo.bar.baz`` we register every dotted prefix that maps
    to a concrete file (``foo/bar/baz.py`` or ``foo/bar/baz/__init__.py``).
    For Java ``com.foo.Bar`` we register the matching ``com/foo/Bar.java``.
    Other languages fall back to filename-stem matching when imports are
    bare names.
    """
    index: dict[str, list[str]] = defaultdict(list)
    for path in file_set:
        p = Path(path)
        suffix = p.suffix.lower()
        stem = p.stem
        # Bare filename → all paths sharing that stem
        index[stem].append(path)

        if suffix == ".py":
            parts = list(p.with_suffix("").parts)
            if parts and parts[-1] == "__init__":
                parts = parts[:-1]
            for size in range(1, len(parts) + 1):
                dotted = ".".join(parts[-size:])
                index[dotted].append(path)
        elif suffix in {".java", ".kt", ".scala", ".cs"}:
            parts = list(p.with_suffix("").parts)
            for size in range(1, len(parts) + 1):
                dotted = ".".join(parts[-size:])
                index[dotted].append(path)
        elif suffix in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}:
            parts = list(p.parts)
            # JS imports are usually written without extension.
            for size in range(1, len(parts) + 1):
                tail = "/".join(parts[-size:])
                stripped = re.sub(r"\.(?:js|jsx|ts|tsx|mjs|cjs)$", "", tail)
                index[stripped].append(path)
                index[tail].append(path)
        elif suffix == ".go":
            parts = list(p.parts)
            for size in range(1, len(parts) + 1):
                index["/".join(parts[-size:])].append(path)
    return index


def _resolve_imports(
    source: Path,
    text: str,
    *,
    file_set: set[str],
    modules: dict[str, list[str]],
) -> list[str]:
    suffix = source.suffix.lower()
    raw_targets: list[str] = []

    if suffix == ".py":
        for match in _PY_IMPORT.finditer(text):
            raw_targets.append(match.group(1) or match.group(2))
    elif suffix in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}:
        for match in _JS_IMPORT.finditer(text):
            raw_targets.append(next((g for g in match.groups() if g), ""))
    elif suffix == ".go":
        for match in _GO_IMPORT.finditer(text):
            block = match.group(0)
            for inner in _GO_IMPORT_BLOCK.finditer(block):
                raw_targets.append(inner.group(1))
            if match.group(1):
                raw_targets.append(match.group(1))
    elif suffix in {".java", ".kt", ".scala", ".cs"}:
        for match in _JAVA_IMPORT.finditer(text):
            raw_targets.append(match.group(1))
    elif suffix == ".rb":
        for match in _RUBY_REQUIRE.finditer(text):
            raw_targets.append(match.group(1))

    resolved: list[str] = []
    seen: set[str] = set()
    for raw in raw_targets:
        if not raw:
            continue
        normalized = raw.strip().strip('"').strip("'")
        if not normalized:
            continue
        for candidate in _candidates_for(normalized, source=source, file_set=file_set, modules=modules):
            if candidate not in seen:
                seen.add(candidate)
                resolved.append(candidate)
    return resolved


def _candidates_for(
    raw: str,
    *,
    source: Path,
    file_set: set[str],
    modules: dict[str, list[str]],
) -> list[str]:
    # Relative imports (``./foo``, ``../bar``) — resolve within the repo.
    # Path.resolve() would expand against the CWD; we want the result
    # relative to the repo root so it can match file_set entries.
    if raw.startswith((".", "/")):
        target = source.parent / raw
        normalized = _normalize_relative(target)
        return [p for p in _try_path_variants(normalized) if p in file_set]

    # Strip leading dots from Python relative-from imports
    stripped = raw.lstrip(".")
    matches = modules.get(stripped, [])
    matches += modules.get(stripped.split(".")[-1], [])
    matches += modules.get(stripped.split("/")[-1], [])

    out: list[str] = []
    seen: set[str] = set()
    for path in matches:
        if path in file_set and path not in seen and path != source.as_posix():
            seen.add(path)
            out.append(path)
    return out


def _normalize_relative(path: Path) -> Path:
    """Collapse ``..`` / ``.`` segments without touching the filesystem.

    ``Path.resolve()`` would anchor against the current working directory
    and break the repo-relative semantics we rely on for graph keys.
    """
    parts: list[str] = []
    for part in path.parts:
        if part in ("", "."):
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    return Path(*parts) if parts else Path()


def _try_path_variants(path: Path) -> list[str]:
    candidates: list[str] = []
    for ext in (".py", ".js", ".ts", ".tsx", ".jsx", ".mjs", ".cjs", ".rb", ".go", ""):
        with_ext = path if ext == "" else path.with_suffix(ext)
        candidates.append(with_ext.as_posix())
    candidates.append((path / "__init__.py").as_posix())
    candidates.append((path / "index.ts").as_posix())
    candidates.append((path / "index.js").as_posix())
    return candidates
