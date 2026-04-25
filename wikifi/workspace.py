import json
from pathlib import Path
from typing import List, Optional
from wikifi.config import settings
from wikifi.models import WorkspaceLayout, ExtractionNote, IntrospectionAssessment

class WorkspaceManager:
    def __init__(self, target_dir: str):
        self.target_dir = Path(target_dir).resolve()
        self.wiki_dir = self.target_dir / settings.wiki_dir
        self.notes_dir = self.wiki_dir / "notes"
        self.sections_dir = self.wiki_dir / "sections"
        self.config_path = self.wiki_dir / "config.json"

    def initialize(self) -> WorkspaceLayout:
        self.wiki_dir.mkdir(parents=True, exist_ok=True)
        self.notes_dir.mkdir(parents=True, exist_ok=True)
        self.sections_dir.mkdir(parents=True, exist_ok=True)
        
        layout = WorkspaceLayout(
            root_dir=str(self.wiki_dir),
            notes_dir=str(self.notes_dir),
            sections_dir=str(self.sections_dir),
            config_path=str(self.config_path)
        )
        return layout

    def save_introspection(self, assessment: IntrospectionAssessment):
        path = self.wiki_dir / "introspection.json"
        with open(path, "w") as f:
            f.write(assessment.model_dump_json(indent=2))

    def save_note(self, note: ExtractionNote):
        # Sanitize file path for filename
        safe_name = note.file_path.replace("/", "_").replace("\\", "_") + ".json"
        path = self.notes_dir / safe_name
        with open(path, "w") as f:
            f.write(note.model_dump_json(indent=2))

    def save_section(self, name: str, content: str):
        path = self.sections_dir / f"{name}.md"
        with open(path, "w") as f:
            f.write(content)

    def load_notes(self) -> List[ExtractionNote]:
        notes = []
        for p in self.notes_dir.glob("*.json"):
            with open(p, "r") as f:
                notes.append(ExtractionNote.model_validate_json(f.read()))
        return notes

    def load_introspection(self) -> Optional[IntrospectionAssessment]:
        path = self.wiki_dir / "introspection.json"
        if not path.exists():
            return None
        with open(path, "r") as f:
            return IntrospectionAssessment.model_validate_json(f.read())
