"""Workspace lifecycle: provision the ``.wikifi/`` directory and its layout."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from wikifi.schemas import ALL_SECTIONS

NOTES_GITIGNORE = """# Intermediate per-file notes — committed only by request.
# Synthesized .md sections live next to this file and are checked in.
*.json
"""

ROOT_GITIGNORE = """# wikifi intermediate state. Synthesized sections (.md) are checked in.
.notes/
"""


@dataclass(slots=True)
class Workspace:
    """Resolved layout of a ``.wikifi/`` directory."""

    root: Path
    wiki_dir: Path
    notes_dir: Path

    @property
    def execution_summary(self) -> Path:
        return self.wiki_dir / "execution_summary.md"

    def section_path(self, section_id: str) -> Path:
        return self.wiki_dir / f"{section_id}.md"


def provision_workspace(root: Path, *, wiki_dir_name: str = ".wikifi") -> Workspace:
    """Create ``.wikifi/`` and ``.wikifi/.notes/`` if missing.

    Idempotent — re-runs against an existing workspace must not corrupt
    state. Existing markdown files are left untouched until the
    aggregation stage rewrites them.
    """
    root = root.resolve()
    wiki_dir = root / wiki_dir_name
    notes_dir = wiki_dir / ".notes"

    wiki_dir.mkdir(parents=True, exist_ok=True)
    notes_dir.mkdir(parents=True, exist_ok=True)

    notes_ignore = notes_dir / ".gitignore"
    if not notes_ignore.exists():
        notes_ignore.write_text(NOTES_GITIGNORE, encoding="utf-8")

    root_ignore = wiki_dir / ".gitignore"
    if not root_ignore.exists():
        root_ignore.write_text(ROOT_GITIGNORE, encoding="utf-8")

    return Workspace(root=root, wiki_dir=wiki_dir, notes_dir=notes_dir)


def reset_notes(workspace: Workspace) -> int:
    """Remove all extraction-note JSON files. Returns count removed."""
    count = 0
    if not workspace.notes_dir.exists():
        return 0
    for entry in workspace.notes_dir.iterdir():
        if entry.is_file() and entry.suffix == ".json":
            try:
                entry.unlink()
            except OSError:
                continue
            count += 1
    return count


def all_section_paths(workspace: Workspace) -> dict[str, Path]:
    return {section: workspace.section_path(section) for section in ALL_SECTIONS}
