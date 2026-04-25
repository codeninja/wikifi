"""Pydantic schemas for structured LLM exchanges and pipeline records."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

# Canonical primary-section ids — extraction notes target one or more of these.
PRIMARY_SECTIONS: tuple[str, ...] = (
    "intent",
    "capabilities",
    "domains",
    "entities",
    "integrations",
    "external_dependencies",
    "cross_cutting",
    "hard_specifications",
)

DERIVATIVE_SECTIONS: tuple[str, ...] = (
    "personas",
    "user_stories",
    "diagrams",
)

ALL_SECTIONS: tuple[str, ...] = PRIMARY_SECTIONS + DERIVATIVE_SECTIONS


SectionId = Literal[
    "intent",
    "capabilities",
    "domains",
    "entities",
    "integrations",
    "external_dependencies",
    "cross_cutting",
    "hard_specifications",
]


class IntrospectionAssessment(BaseModel):
    """Stage-1 assessment of the repository as a whole."""

    primary_languages: list[str] = Field(default_factory=list)
    inferred_purpose: str = ""
    classification_rationale: str = ""
    in_scope_globs: list[str] = Field(default_factory=list)
    out_of_scope_globs: list[str] = Field(default_factory=list)
    notable_manifests: list[str] = Field(default_factory=list)


class DirectorySummary(BaseModel):
    """Aggregate stats over the in-scope file set."""

    file_count: int
    total_bytes: int
    extension_distribution: dict[str, int]
    manifest_presence: list[str]
    sample_paths: list[str] = Field(default_factory=list)
    tree_outline: str = ""


class ExtractionFinding(BaseModel):
    """One finding produced by the LLM for a single source file."""

    section: SectionId
    finding: str


class ExtractionPayload(BaseModel):
    """Schema the extractor asks the LLM to emit per source file."""

    role_summary: str = Field(
        ...,
        description="One- or two-sentence, technology-agnostic description of the file's role.",
    )
    findings: list[ExtractionFinding] = Field(default_factory=list)
    skip_reason: str | None = Field(
        default=None,
        description="Set when the file carries no extractable intent; findings should then be empty.",
    )


class ExtractionNote(BaseModel):
    """Persisted, immutable record for a single source file."""

    timestamp: datetime
    file_reference: str
    role_summary: str
    findings: list[ExtractionFinding]
    skip_reason: str | None = None

    @classmethod
    def now(
        cls,
        *,
        file_reference: str,
        payload: ExtractionPayload,
    ) -> ExtractionNote:
        return cls(
            timestamp=datetime.now(UTC),
            file_reference=file_reference,
            role_summary=payload.role_summary,
            findings=list(payload.findings),
            skip_reason=payload.skip_reason,
        )


class AggregationStats(BaseModel):
    """Outcome of the synthesis stage."""

    successful_writes: int = 0
    empty_sections: list[str] = Field(default_factory=list)
    failed_sections: list[str] = Field(default_factory=list)


class ExecutionSummary(BaseModel):
    """End-of-run report covering all four stages."""

    started_at: datetime
    finished_at: datetime
    target_path: str
    files_seen: int
    files_in_scope: int
    files_skipped_min_bytes: int
    files_skipped_excluded: int
    files_truncated: int
    extraction_notes_written: int
    extraction_failures: int
    primary_sections_written: int
    primary_sections_empty: list[str]
    derivative_sections_written: int
    derivative_sections_empty: list[str]
    provider: str
    model: str
    think: str
    notes: list[str] = Field(default_factory=list)
