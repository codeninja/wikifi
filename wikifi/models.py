from typing import Any, Dict, List

from pydantic import BaseModel, Field


class DirectorySummary(BaseModel):
    file_count: int
    total_size: int
    extension_distribution: Dict[str, int]
    manifest_presence: bool


class IntrospectionAssessment(BaseModel):
    primary_languages: List[str] = Field(description="Primary programming languages detected")
    inferred_purpose: str = Field(description="Inferred purpose of the system")
    classification_rationale: str = Field(description="Rationale behind the classification")


class ExtractionNote(BaseModel):
    timestamp: str
    file_reference: str
    role_summary: str = Field(description="Summary of the file's role in the system")
    extracted_finding: str = Field(description="Detailed extracted finding or domain concept mapping")


class DocumentationSection(BaseModel):
    category: str
    aggregated_content: str
    final_markdown_body: str


class AggregationStats(BaseModel):
    successful_writes: int
    empty_section_count: int


class WorkspaceLayout(BaseModel):
    config_paths: str
    notes_paths: str
    sections_paths: str


class ExecutionSummary(BaseModel):
    stage_metrics: Dict[str, Any]
    completion_status: str
    consolidated_findings: str
