"""Stage 2 — per-file structured extraction.

Given the include/exclude decision from Stage 1, walk each file deterministically
and ask the LLM what intent-bearing content it contributes to each capture
section. Results are appended to per-section JSONL note files for the aggregator.

The contract: one LLM call per file, output validated against a strict Pydantic
schema. Files that can't be read or validated are recorded as skipped findings
rather than crashing the walk.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, Field

from wikifi.providers.base import LLMProvider
from wikifi.sections import PRIMARY_SECTION_IDS, PRIMARY_SECTIONS
from wikifi.wiki import WikiLayout, append_note

log = logging.getLogger("wikifi.extractor")


# Per-file extraction targets *primary* sections only. Derivative sections
# (personas, user stories, diagrams) emerge from the aggregate of primaries
# and are produced in Stage 4 — asking the model to identify them at the
# per-file level produces sparse, speculative findings.
_SECTION_LIST = ", ".join(PRIMARY_SECTION_IDS)
_SECTION_BRIEFS = "\n".join(f"- {s.id}: {s.description}" for s in PRIMARY_SECTIONS)


EXTRACTION_SYSTEM_PROMPT = f"""\
You are wikifi's per-file extraction pass. You read a single source file and \
identify what it contributes to each section of a technology-agnostic wiki.

You describe *intent* — what the code is trying to accomplish for the system's \
users — not the mechanics of the code. Never name the language, framework, or \
library. Translate everything into domain language.

If a file contributes nothing to a section, omit that section. If a file is \
purely scaffolding (config, formatting, build, test fixtures) return an empty \
findings list.

Only emit findings for these section ids: {_SECTION_LIST}

Section briefs:
{_SECTION_BRIEFS}
"""


class SectionFinding(BaseModel):
    """A single contribution from one file to one section."""

    section_id: str = Field(description=f"Must be one of: {_SECTION_LIST}")
    finding: str = Field(description="Tech-agnostic markdown describing the contribution. 1-5 sentences.")


class FileFindings(BaseModel):
    """The full set of findings the LLM produced for a given file."""

    summary: str = Field(default="", description="One-sentence summary of the file's role.")
    findings: list[SectionFinding] = Field(default_factory=list)


@dataclass
class ExtractionStats:
    files_seen: int = 0
    files_with_findings: int = 0
    findings_total: int = 0
    files_skipped: int = 0


def extract_repo(
    *,
    layout: WikiLayout,
    provider: LLMProvider,
    files: Iterable[Path],
    repo_root: Path,
    max_file_bytes: int = 200_000,
) -> ExtractionStats:
    """Walk the supplied files and append per-section findings to the notes store."""
    stats = ExtractionStats()
    valid_ids = set(PRIMARY_SECTION_IDS)

    for rel in files:
        stats.files_seen += 1
        full = repo_root / rel
        try:
            data = full.read_text(encoding="utf-8", errors="replace")
        except OSError:
            log.warning("could not read %s; skipping", rel)
            stats.files_skipped += 1
            continue
        if len(data) > max_file_bytes:
            data = data[:max_file_bytes] + "\n... [truncated]\n"

        try:
            findings = provider.complete_json(
                system=EXTRACTION_SYSTEM_PROMPT,
                user=_render_user_prompt(rel=rel, body=data),
                schema=FileFindings,
            )
        except Exception as exc:  # provider/parse errors are per-file, not per-walk
            log.warning("extraction failed for %s: %s", rel, exc)
            stats.files_skipped += 1
            continue

        if not findings.findings:
            continue

        stats.files_with_findings += 1
        for finding in findings.findings:
            if finding.section_id not in valid_ids:
                continue
            append_note(
                layout,
                finding.section_id,
                {
                    "file": rel.as_posix(),
                    "summary": findings.summary,
                    "finding": finding.finding,
                },
            )
            stats.findings_total += 1

    return stats


def _render_user_prompt(*, rel: Path, body: str) -> str:
    return (
        f"File path: {rel.as_posix()}\n\n"
        "File contents:\n"
        "```\n"
        f"{body}\n"
        "```\n\n"
        "Return findings strictly in the FileFindings schema. Use section ids "
        f"only from: {_SECTION_LIST}."
    )
