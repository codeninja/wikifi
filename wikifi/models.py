from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class ExtractionNote(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    file_path: str
    role_summary: str
    finding: str

class DirectorySummary(BaseModel):
    file_count: int = 0
    total_size: int = 0
    extension_distribution: Dict[str, int] = Field(default_factory=dict)
    manifests: List[str] = Field(default_factory=list)

class IntrospectionAssessment(BaseModel):
    primary_languages: List[str]
    inferred_purpose: str
    classification_rationale: str
    notable_files: List[str]

class DocumentationSection(BaseModel):
    category: str
    content: str
    markdown_body: Optional[str] = None

class AggregationStats(BaseModel):
    successful_writes: int = 0
    empty_sections: int = 0

class ExecutionSummary(BaseModel):
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    stages_completed: List[str] = Field(default_factory=list)
    success: bool = False
    message: Optional[str] = None

class WorkspaceLayout(BaseModel):
    root_dir: str
    notes_dir: str
    sections_dir: str
    config_path: str
