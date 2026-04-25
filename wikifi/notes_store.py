"""Persistence for the immutable per-file extraction notes."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

from wikifi.schemas import ExtractionNote


def _slugify(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._-") or "note"


def write_note(notes_dir: Path, note: ExtractionNote) -> Path:
    """Write a note as ``{slug}.json`` and return the path written.

    Notes are immutable once written; a re-extraction of the same file
    overwrites the JSON so the freshest extraction is the one consumed
    downstream — but only after the previous reset_notes() in the
    pipeline has cleared the directory.
    """
    notes_dir.mkdir(parents=True, exist_ok=True)
    slug = _slugify(note.file_reference)
    path = notes_dir / f"{slug}.json"
    path.write_text(note.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_notes(notes_dir: Path) -> list[ExtractionNote]:
    """Read every ``*.json`` note from ``notes_dir``, sorted by timestamp."""
    if not notes_dir.is_dir():
        return []
    notes: list[ExtractionNote] = []
    for entry in notes_dir.iterdir():
        if entry.suffix != ".json" or not entry.is_file():
            continue
        try:
            data = json.loads(entry.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        try:
            notes.append(ExtractionNote.model_validate(data))
        except Exception:  # noqa: BLE001 - skip malformed notes silently
            continue
    notes.sort(key=lambda n: (n.timestamp, n.file_reference))
    return notes


def group_by_section(notes: list[ExtractionNote]) -> dict[str, list[tuple[ExtractionNote, str]]]:
    """Bucket findings by section id; preserves insertion order per bucket."""
    grouped: dict[str, list[tuple[ExtractionNote, str]]] = defaultdict(list)
    for note in notes:
        for finding in note.findings:
            grouped[finding.section].append((note, finding.finding))
    return grouped
