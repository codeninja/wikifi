from __future__ import annotations

from dataclasses import dataclass

SUPPORTED_PROVIDERS = {"ollama"}

IMMUTABLE_EXCLUDED_DIRS = frozenset(
    {
        ".claude",
        ".git",
        ".github",
        ".githooks",
        ".hg",
        ".idea",
        ".mypy_cache",
        ".nox",
        ".pytest_cache",
        ".ruff_cache",
        ".spec",
        ".svn",
        ".tox",
        ".venv",
        ".vscode",
        ".wikifi",
        "__pycache__",
        "build",
        "coverage",
        "dist",
        "htmlcov",
        "node_modules",
        "target",
        "vendor",
        "venv",
    }
)

IMMUTABLE_EXCLUDED_FILE_PATTERNS = (
    "*.bmp",
    "*.db",
    "*.gif",
    "*.ico",
    "*.jpeg",
    "*.jpg",
    "*.lock",
    "*.log",
    "*.min.css",
    "*.min.js",
    "*.pdf",
    "*.png",
    "*.pyc",
    "*.sqlite",
    "*.sqlite3",
    "*.svg",
    "*.webp",
    "package-lock.json",
    "pnpm-lock.yaml",
    "uv.lock",
    "yarn.lock",
)

STRUCTURAL_FILENAMES = frozenset(
    {
        "README",
        "README.md",
        "VISION.md",
        "CLAUDE.md",
        "CODE-FORMAT.md",
        "pyproject.toml",
        "package.json",
        "Cargo.toml",
        "go.mod",
        "pom.xml",
        "build.gradle",
        "settings.gradle",
        "Makefile",
        "Dockerfile",
        "docker-compose.yml",
        "compose.yml",
    }
)

PRODUCTION_EXTENSIONS = frozenset(
    {
        ".c",
        ".cc",
        ".clj",
        ".cpp",
        ".cs",
        ".css",
        ".ex",
        ".exs",
        ".go",
        ".h",
        ".hpp",
        ".html",
        ".java",
        ".js",
        ".jsx",
        ".kt",
        ".kts",
        ".php",
        ".py",
        ".rb",
        ".rs",
        ".scala",
        ".sql",
        ".swift",
        ".ts",
        ".tsx",
    }
)

TEST_PATH_PARTS = frozenset(
    {
        "__tests__",
        "spec",
        "specs",
        "test",
        "tests",
    }
)

TEST_FILE_PATTERNS = (
    "test_*",
    "*_test.*",
    "*.spec.*",
    "*.test.*",
)


@dataclass(frozen=True)
class SectionDefinition:
    key: str
    filename: str
    title: str
    purpose: str
    derivative: bool = False


PRIMARY_SECTIONS: tuple[SectionDefinition, ...] = (
    SectionDefinition(
        key="domains",
        filename="domains.md",
        title="Domains and Subdomains",
        purpose="Core business domains, bounded contexts, and their relationships.",
    ),
    SectionDefinition(
        key="intent",
        filename="intent.md",
        title="Intent and Problem Space",
        purpose="The system purpose, value proposition, and problem space.",
    ),
    SectionDefinition(
        key="capabilities",
        filename="capabilities.md",
        title="Capabilities",
        purpose="What the system does for its users in domain language.",
    ),
    SectionDefinition(
        key="external_dependencies",
        filename="external_dependencies.md",
        title="External-System Dependencies",
        purpose="Third-party services, infrastructure, and standards the system depends on.",
    ),
    SectionDefinition(
        key="integrations",
        filename="integrations.md",
        title="Integrations",
        purpose="Internal and external touchpoints and handoffs.",
    ),
    SectionDefinition(
        key="cross_cutting",
        filename="cross_cutting.md",
        title="Cross-Cutting Concerns",
        purpose="Observability, data integrity, security, storage, and operational guardrails.",
    ),
    SectionDefinition(
        key="entities",
        filename="entities.md",
        title="Core Entities",
        purpose="Domain entities, important structures, and relationships.",
    ),
    SectionDefinition(
        key="hard_specifications",
        filename="hard_specifications.md",
        title="Hard Specifications",
        purpose="Critical behavior and requirements that must carry forward.",
    ),
    SectionDefinition(
        key="inline_schematics",
        filename="inline_schematics.md",
        title="Inline Schematics",
        purpose="Mermaid visualizations that clarify domains, entities, and integrations.",
    ),
)

DERIVATIVE_SECTIONS: tuple[SectionDefinition, ...] = (
    SectionDefinition(
        key="personas",
        filename="personas.md",
        title="User Personas",
        purpose="Personas derived from the aggregate primary wiki.",
        derivative=True,
    ),
    SectionDefinition(
        key="user_stories",
        filename="user_stories.md",
        title="User Stories",
        purpose="Gherkin-style stories derived from aggregate behavior.",
        derivative=True,
    ),
    SectionDefinition(
        key="diagrams",
        filename="diagrams.md",
        title="Diagrams",
        purpose="Aggregate Mermaid diagrams for domains, entities, and integrations.",
        derivative=True,
    ),
)

STAGE_ORDER = ("introspection", "extraction", "aggregation", "derivation")
