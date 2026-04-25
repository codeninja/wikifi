from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def normalize_path(path: Path) -> str:
    return path.as_posix()


@dataclass(frozen=True)
class WorkspaceLayout:
    root: Path
    wiki_dir: Path
    config_file: Path
    notes_dir: Path
    notes_file: Path
    sections_dir: Path
    derivatives_dir: Path
    reports_dir: Path
    summary_json: Path
    summary_markdown: Path
    gitignore: Path
    run_log: Path

    @classmethod
    def from_root(cls, root: Path, output_dir: str = ".wikifi") -> WorkspaceLayout:
        wiki_dir = root / output_dir
        return cls(
            root=root,
            wiki_dir=wiki_dir,
            config_file=wiki_dir / "config.toml",
            notes_dir=wiki_dir / "notes",
            notes_file=wiki_dir / "notes" / "extraction.jsonl",
            sections_dir=wiki_dir / "sections",
            derivatives_dir=wiki_dir / "derivatives",
            reports_dir=wiki_dir / "reports",
            summary_json=wiki_dir / "reports" / "execution-summary.json",
            summary_markdown=wiki_dir / "reports" / "execution-summary.md",
            gitignore=wiki_dir / ".gitignore",
            run_log=wiki_dir / "run.log",
        )

    def as_json(self) -> dict[str, str]:
        return {key: normalize_path(value) for key, value in asdict(self).items()}


@dataclass(frozen=True)
class Settings:
    provider: str = "ollama"
    model: str = "qwen3.6:27b"
    ollama_host: str = "http://localhost:11434"
    request_timeout: int = 900
    max_file_bytes: int = 200_000
    min_content_bytes: int = 64
    introspection_depth: int = 3
    think: str = "high"
    output_dir: str = ".wikifi"
    allow_provider_fallback: bool = True
    exclude_patterns: tuple[str, ...] = ()

    def as_config(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "ollama_host": self.ollama_host,
            "request_timeout": self.request_timeout,
            "max_file_bytes": self.max_file_bytes,
            "min_content_bytes": self.min_content_bytes,
            "introspection_depth": self.introspection_depth,
            "think": self.think,
            "output_dir": self.output_dir,
            "allow_provider_fallback": self.allow_provider_fallback,
            "exclude_patterns": list(self.exclude_patterns),
        }


@dataclass(frozen=True)
class SourceFile:
    path: Path
    relative_path: str
    size_bytes: int
    content: str
    truncated: bool
    digest: str

    @property
    def extension(self) -> str:
        return self.path.suffix.lower()


@dataclass(frozen=True)
class SkippedFile:
    relative_path: str
    reason: str
    size_bytes: int = 0


@dataclass(frozen=True)
class DirectorySummary:
    root: str
    file_count: int
    total_size_bytes: int
    extension_distribution: dict[str, int]
    manifest_files: tuple[str, ...]
    documentation_files: tuple[str, ...]
    top_level_entries: tuple[str, ...]
    selected_file_count: int
    skipped_counts: dict[str, int]


@dataclass(frozen=True)
class IntrospectionAssessment:
    primary_languages: tuple[str, ...]
    inferred_purpose: str
    classification_rationale: str
    scope_description: str
    notable_gaps: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExtractionNote:
    timestamp: str
    file_reference: str
    role_summary: str
    finding: str
    categories: dict[str, list[str]]
    evidence: str
    source_digest: str
    provider_used: str
    gaps: tuple[str, ...] = ()

    @classmethod
    def build(
        cls,
        *,
        file_reference: str,
        role_summary: str,
        finding: str,
        categories: dict[str, list[str]],
        evidence: str,
        source_digest: str,
        provider_used: str,
        gaps: tuple[str, ...] = (),
    ) -> ExtractionNote:
        return cls(
            timestamp=utc_now(),
            file_reference=file_reference,
            role_summary=role_summary.strip(),
            finding=finding.strip(),
            categories={key: [item.strip() for item in value if item.strip()] for key, value in categories.items()},
            evidence=evidence.strip(),
            source_digest=source_digest,
            provider_used=provider_used,
            gaps=tuple(gap.strip() for gap in gaps if gap.strip()),
        )


@dataclass
class AggregationStats:
    attempted_sections: int = 0
    successful_writes: int = 0
    empty_section_count: int = 0
    section_paths: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)

    def record(self, path: Path, content: str) -> None:
        self.attempted_sections += 1
        if content.strip():
            self.successful_writes += 1
        else:
            self.empty_section_count += 1
        self.section_paths.append(normalize_path(path))


@dataclass(frozen=True)
class PipelineResult:
    layout: WorkspaceLayout
    directory_summary: DirectorySummary
    assessment: IntrospectionAssessment
    notes: tuple[ExtractionNote, ...]
    aggregation_stats: AggregationStats
    derivative_stats: AggregationStats
    completion_status: str
    provider_status: str
    stage_metrics: dict[str, Any]
    started_at: str
    finished_at: str

    def as_summary(self) -> dict[str, Any]:
        return {
            "completion_status": self.completion_status,
            "stage_order": ["introspection", "extraction", "aggregation", "derivation"],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "provider_status": self.provider_status,
            "workspace": self.layout.as_json(),
            "directory_summary": asdict(self.directory_summary),
            "introspection_assessment": asdict(self.assessment),
            "extraction_note_count": len(self.notes),
            "aggregation_stats": asdict(self.aggregation_stats),
            "derivative_stats": asdict(self.derivative_stats),
            "stage_metrics": self.stage_metrics,
        }
