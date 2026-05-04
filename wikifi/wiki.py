"""``.wikifi/`` directory layout, scaffolding, and section writer.

The layout is the contract between wikifi and the target project — keep it
stable so existing wikis remain readable when wikifi is upgraded.

```
<target>/.wikifi/
  config.toml          # provider/model overrides; created by `wikifi init`
  .gitignore           # excludes per-file extraction notes + cache by default
  <section>.md         # one per entry in wikifi.sections.SECTIONS
  .notes/              # per-file/per-section extraction state (jsonl)
  .cache/              # content-addressed extraction + aggregation cache
```
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from wikifi.sections import SECTIONS, Section

WIKI_DIRNAME = ".wikifi"
NOTES_DIRNAME = ".notes"
# Cache dir constant lives here (not in ``cache.py``) so the layout has
# one source of truth and ``cache.py`` can import it without inverting
# the existing ``cache → wiki`` dependency direction.
CACHE_DIRNAME = ".cache"
CONFIG_FILENAME = "config.toml"
GITIGNORE_FILENAME = ".gitignore"

# Lines we guarantee in ``.wikifi/.gitignore``. Both ``.notes/`` and
# ``.cache/`` are local working state — section markdown is what gets
# committed. New entries appended here are also backfilled into older
# wikis on the next ``wikifi init`` (see :func:`initialize`) so users
# upgrading wikifi don't accumulate noisy untracked files.
_GITIGNORE_REQUIRED_ENTRIES: tuple[str, ...] = (
    f"{NOTES_DIRNAME}/",
    f"{CACHE_DIRNAME}/",
)
DEFAULT_GITIGNORE = (
    "# wikifi local working state — section markdown is committed, "
    "notes and cache are not.\n" + "\n".join(_GITIGNORE_REQUIRED_ENTRIES) + "\n"
)


@dataclass(frozen=True)
class WikiLayout:
    root: Path  # the target project root (CWD at init time)

    @property
    def wiki_dir(self) -> Path:
        return self.root / WIKI_DIRNAME

    @property
    def config_path(self) -> Path:
        return self.wiki_dir / CONFIG_FILENAME

    @property
    def gitignore_path(self) -> Path:
        return self.wiki_dir / GITIGNORE_FILENAME

    @property
    def notes_dir(self) -> Path:
        return self.wiki_dir / NOTES_DIRNAME

    @property
    def cache_dir(self) -> Path:
        return self.wiki_dir / CACHE_DIRNAME

    def section_path(self, section: Section | str) -> Path:
        sid = section.id if isinstance(section, Section) else section
        return self.wiki_dir / f"{sid}.md"

    def notes_path(self, section: Section | str) -> Path:
        sid = section.id if isinstance(section, Section) else section
        return self.notes_dir / f"{sid}.jsonl"


def initialize(layout: WikiLayout, *, model: str, provider: str, ollama_host: str) -> list[Path]:
    """Create the `.wikifi/` skeleton. Idempotent — existing files are left alone.

    Returns the list of paths created (or that already existed and were
    confirmed in place). Section markdown files start with a single h1 heading
    so a freshly-initialized wiki is browsable before `walk` runs.
    """
    created: list[Path] = []
    layout.wiki_dir.mkdir(parents=True, exist_ok=True)
    created.append(layout.wiki_dir)

    layout.notes_dir.mkdir(exist_ok=True)
    created.append(layout.notes_dir)

    if not layout.config_path.exists():
        layout.config_path.write_text(_render_config(model=model, provider=provider, ollama_host=ollama_host))
    created.append(layout.config_path)

    _ensure_gitignore(layout)
    created.append(layout.gitignore_path)

    for section in SECTIONS:
        path = layout.section_path(section)
        if not path.exists():
            path.write_text(_empty_section(section))
        created.append(path)

    return created


def _ensure_gitignore(layout: WikiLayout) -> None:
    """Ensure the wiki's .gitignore exists and covers every required entry.

    Older wikis predate the cache layer and have a ``.gitignore`` that
    only ignores ``.notes/``. Backfill any missing line-by-line entries
    from :data:`_GITIGNORE_REQUIRED_ENTRIES` so users upgrading wikifi
    don't end up with stray ``.cache/`` (or future-added) directories
    showing as untracked changes in the target repo.
    """
    path = layout.gitignore_path
    if not path.exists():
        path.write_text(DEFAULT_GITIGNORE)
        return
    existing = path.read_text(encoding="utf-8")
    existing_lines = {line.strip() for line in existing.splitlines() if line.strip()}
    missing = [entry for entry in _GITIGNORE_REQUIRED_ENTRIES if entry not in existing_lines]
    if not missing:
        return
    suffix_nl = "" if existing.endswith("\n") else "\n"
    path.write_text(existing + suffix_nl + "\n".join(missing) + "\n")


def write_section(layout: WikiLayout, section: Section, body: str) -> Path:
    """Replace a section's body with rendered markdown."""
    path = layout.section_path(section)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render_section(section, body))
    return path


def append_note(layout: WikiLayout, section: Section | str, note: dict[str, Any]) -> None:
    """Append a single per-file note to the section's jsonl scratch file."""
    layout.notes_dir.mkdir(parents=True, exist_ok=True)
    record = {"timestamp": datetime.now(UTC).isoformat(), **note}
    with layout.notes_path(section).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_notes(layout: WikiLayout, section: Section | str) -> list[dict[str, Any]]:
    """Load every persisted note for a section in insertion order."""
    path = layout.notes_path(section)
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def reset_notes(layout: WikiLayout) -> None:
    """Truncate every section's notes file. Called at the start of `walk`."""
    if not layout.notes_dir.exists():
        return
    for child in layout.notes_dir.iterdir():
        if child.is_file():
            child.unlink()


def _render_config(*, model: str, provider: str, ollama_host: str) -> str:
    return (
        "# wikifi local config — overrides WIKIFI_* environment variables when present.\n"
        f'provider = "{provider}"\n'
        f'model = "{model}"\n'
        f'ollama_host = "{ollama_host}"\n'
    )


def _empty_section(section: Section) -> str:
    return (
        f"# {section.title}\n\n"
        "_Not yet populated. Run `wikifi walk` to fill this section._\n\n"
        f"> {section.description}\n"
    )


def _render_section(section: Section, body: str) -> str:
    body = body.strip()
    return f"# {section.title}\n\n{body}\n"
