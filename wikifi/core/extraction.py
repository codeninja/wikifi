from datetime import datetime
from pathlib import Path
from typing import List, Optional

from rich.progress import track

from wikifi.config import get_settings
from wikifi.llm import llm_provider
from wikifi.models import ExtractionNote


class ExtractionEngine:
    def __init__(self):
        self.settings = get_settings()
        self.notes_dir = Path(self.settings.workspace_path) / "notes"
        self.notes_dir.mkdir(parents=True, exist_ok=True)

    def extract_file(self, file_path: Path) -> Optional[ExtractionNote]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read(self.settings.max_file_size)
        except Exception:
            return None

        # Determine language/context roughly

        prompt = (
            f"You are an expert system analyst. Analyze the following source code/artifact from `{file_path}`.\n"
            "Identify the file's role in the system and extract domain concepts, business rules, or functional "
            "responsibilities. Ignore low-level implementation details and syntax optimization.\n\n"
            f"--- START `{file_path}` ---\n{content}\n--- END ---\n\n"
            "Extract the role summary and detailed findings as requested by the schema."
        )

        try:
            # We want to extract a partial note, the LLM will fill in role_summary and extracted_finding
            # We provide a wrapper schema to extract those fields.
            from pydantic import BaseModel, Field

            class ExtractedData(BaseModel):
                role_summary: str = Field(description="Summary of the file's role in the system")
                extracted_finding: str = Field(description="Detailed extracted finding or domain concept mapping")

            extracted_data = llm_provider.generate_structured(prompt, ExtractedData)

            note = ExtractionNote(
                timestamp=datetime.utcnow().isoformat(),
                file_reference=str(file_path),
                role_summary=extracted_data.role_summary,
                extracted_finding=extracted_data.extracted_finding,
            )

            # Persist note
            note_file = self.notes_dir / f"{file_path.name}_{hash(str(file_path))}.json"
            with open(note_file, "w", encoding="utf-8") as nf:
                note_json = note.model_dump_json(indent=2)
                nf.write(note_json)

            return note
        except Exception as e:
            # "Invalid or unreadable inputs must be logged and skipped. The pipeline must never halt"
            print(f"Failed to extract from {file_path}: {e}")
            return None


def run_extraction(valid_files: List[Path]) -> List[ExtractionNote]:
    engine = ExtractionEngine()
    notes = []

    # We could use rich track for progress reporting
    for file_path in track(valid_files, description="Extracting domain concepts..."):
        note = engine.extract_file(file_path)
        if note:
            notes.append(note)

    return notes
