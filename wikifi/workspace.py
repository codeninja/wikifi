from __future__ import annotations

import shutil
from pathlib import Path

from wikifi.constants import DERIVATIVE_SECTIONS, PRIMARY_SECTIONS
from wikifi.models import Settings, WorkspaceLayout

DEFAULT_CONFIG_TEMPLATE = """[wikifi]
provider = "ollama"
model = "qwen3.6:27b"
ollama_host = "http://localhost:11434"
request_timeout = 900
max_file_bytes = 200000
min_content_bytes = 64
introspection_depth = 3
think = "high"
allow_provider_fallback = true
exclude_patterns = []
"""

WORKSPACE_GITIGNORE = """/notes/
/tmp/
/run.log
"""


def ensure_workspace(root: Path, settings: Settings, *, force_config: bool = False) -> WorkspaceLayout:
    layout = WorkspaceLayout.from_root(root.resolve(), settings.output_dir)
    layout.wiki_dir.mkdir(parents=True, exist_ok=True)
    layout.notes_dir.mkdir(parents=True, exist_ok=True)
    layout.sections_dir.mkdir(parents=True, exist_ok=True)
    layout.derivatives_dir.mkdir(parents=True, exist_ok=True)
    layout.reports_dir.mkdir(parents=True, exist_ok=True)

    if force_config or not layout.config_file.exists():
        layout.config_file.write_text(DEFAULT_CONFIG_TEMPLATE, encoding="utf-8")
    if force_config or not layout.gitignore.exists():
        layout.gitignore.write_text(WORKSPACE_GITIGNORE, encoding="utf-8")

    for section in PRIMARY_SECTIONS:
        (layout.sections_dir / section.filename).touch(exist_ok=True)
    for section in DERIVATIVE_SECTIONS:
        (layout.derivatives_dir / section.filename).touch(exist_ok=True)

    return layout


def reset_intermediate(layout: WorkspaceLayout) -> None:
    if layout.notes_dir.exists():
        shutil.rmtree(layout.notes_dir)
    layout.notes_dir.mkdir(parents=True, exist_ok=True)
    layout.run_log.write_text("", encoding="utf-8")


def write_workspace_readme(layout: WorkspaceLayout) -> None:
    readme = layout.wiki_dir / "README.md"
    if readme.exists():
        return
    readme.write_text(
        "\n".join(
            [
                "## wikifi Workspace",
                "",
                "This directory contains generated, technology-agnostic documentation.",
                "",
                "- `sections/` contains primary capture produced from direct source evidence.",
                "- `derivatives/` contains personas, user stories, and diagrams synthesized from aggregate sections.",
                "- `reports/` contains execution summaries and pipeline health details.",
                "- `notes/` contains intermediate extraction records and is ignored by default.",
                "",
            ]
        ),
        encoding="utf-8",
    )
