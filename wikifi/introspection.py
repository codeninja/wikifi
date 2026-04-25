"""Stage 1 — LLM introspection of repository structure.

A single LLM call given a compressed view of the repo (directory summaries +
manifest contents) decides which paths are production source worth walking and
which to skip (vendor, build artifacts, tests, infra-as-code, etc.).

Output is structured (Pydantic schema) so the result is deterministic to parse
and easy to diff between runs. The agent sees no source files at this stage —
that's Stage 2's job.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from wikifi.providers.base import LLMProvider
from wikifi.walker import DirSummary, WalkConfig, read_manifest_files, summarize_tree

INTROSPECTION_SYSTEM_PROMPT = """\
You are wikifi's repository introspection pass. Your job is to look at the \
top-level structure of an unknown codebase and decide which directories and \
file patterns contain the production source that defines what the system \
*does* — and which ones should be skipped.

You are tech-agnostic: you don't care which languages, frameworks, or \
infrastructure are in use. You care about *intent-bearing code*.

Skip:
- vendored dependencies, build output, generated files, lockfiles
- test code (we capture intent, not test scaffolding)
- repo configuration, dev tooling, CI/CD, infra-as-code unless it encodes \
  domain rules
- documentation (it's input to the wiki, not the source we walk)

Include:
- application source that implements features, business logic, domain models, \
  integrations, data persistence, or external touchpoints

Output strictly conforms to the schema. Patterns are gitignore-style.\
"""


class IntrospectionResult(BaseModel):
    """Stage 1 output: which paths to walk, which to skip, and why."""

    include: list[str] = Field(
        default_factory=list,
        description="Gitignore-style patterns relative to repo root that should be walked.",
    )
    exclude: list[str] = Field(
        default_factory=list,
        description="Gitignore-style patterns relative to repo root that should be skipped.",
    )
    primary_languages: list[str] = Field(
        default_factory=list,
        description="Languages/runtimes this system is implemented in (informational).",
    )
    likely_purpose: str = Field(
        default="",
        description="One-paragraph guess at what the system does, derived from manifests and structure only.",
    )
    rationale: str = Field(
        default="",
        description="Brief justification for the include/exclude choices.",
    )


def introspect(config: WalkConfig, provider: LLMProvider, *, max_depth: int = 3) -> IntrospectionResult:
    """Run Stage 1: compress the tree, hand it to the LLM, return structured output."""
    summaries = summarize_tree(config, max_depth=max_depth)
    manifest_paths = _select_manifests(summaries)
    manifests = read_manifest_files(config, paths=manifest_paths)
    user_prompt = _render_prompt(root=config.root, summaries=summaries, manifests=manifests)
    return provider.complete_json(
        system=INTROSPECTION_SYSTEM_PROMPT,
        user=user_prompt,
        schema=IntrospectionResult,
    )


def _select_manifests(summaries: list[DirSummary]) -> list[str]:
    """Collect every notable file path across the tree, ordered by depth."""
    out: list[str] = []
    for summary in summaries:
        for name in summary.notable_files:
            rel = name if not summary.rel_path else f"{summary.rel_path}/{name}"
            out.append(rel)
    return out


def _render_prompt(*, root: Path, summaries: list[DirSummary], manifests: dict[str, str]) -> str:
    lines: list[str] = []
    lines.append(f"Repository root: {root.name}")
    lines.append("")
    lines.append("## Directory summary")
    lines.append("Format: <path> | files=<count> bytes=<total> exts={ext: count} notable=[...]")
    lines.append("")
    for summary in summaries:
        path = summary.rel_path or "."
        ext_str = ", ".join(f"{ext}={count}" for ext, count in summary.extensions.items())
        notable_str = ", ".join(summary.notable_files) if summary.notable_files else "-"
        lines.append(
            f"{path} | files={summary.file_count} bytes={summary.total_bytes} "
            f"exts={{{ext_str}}} notable=[{notable_str}]"
        )
    lines.append("")
    if manifests:
        lines.append("## Manifest and README contents (truncated)")
        for rel, body in manifests.items():
            lines.append(f"### {rel}")
            lines.append("```")
            lines.append(body.rstrip())
            lines.append("```")
            lines.append("")
    lines.append("## Task")
    lines.append(
        "Decide which paths in this repository contain production source worth walking "
        "for a tech-agnostic wiki. Return include and exclude pattern lists, the primary "
        "languages, a one-paragraph likely purpose, and a brief rationale."
    )
    return "\n".join(lines)
