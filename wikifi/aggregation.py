from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from wikifi.constants import PRIMARY_SECTIONS, SectionDefinition
from wikifi.models import AggregationStats, DirectorySummary, ExtractionNote, IntrospectionAssessment, WorkspaceLayout
from wikifi.text import bullet_list, dedupe, markdown_table


def aggregate_sections(
    layout: WorkspaceLayout,
    summary: DirectorySummary,
    assessment: IntrospectionAssessment,
    notes: tuple[ExtractionNote, ...],
) -> AggregationStats:
    stats = AggregationStats()
    grouped = _group_notes(notes)
    for section in PRIMARY_SECTIONS:
        content = _render_section(section, summary, assessment, notes, grouped.get(section.key, []))
        path = layout.sections_dir / section.filename
        path.write_text(content, encoding="utf-8")
        stats.record(path, content)
        if "Gap Declaration" in content:
            stats.gaps.append(f"{section.title} includes explicit gap declarations.")
    return stats


def _group_notes(notes: tuple[ExtractionNote, ...]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for note in notes:
        for key, items in note.categories.items():
            grouped[key].extend(items)
        if note.gaps:
            grouped["hard_specifications"].extend(f"Gap from {note.file_reference}: {gap}" for gap in note.gaps)
    return {key: dedupe(value) for key, value in grouped.items()}


def _render_section(
    section: SectionDefinition,
    summary: DirectorySummary,
    assessment: IntrospectionAssessment,
    notes: tuple[ExtractionNote, ...],
    findings: list[str],
) -> str:
    if section.key == "domains":
        return _domains_section(section, assessment, findings)
    if section.key == "intent":
        return _intent_section(section, assessment, findings)
    if section.key == "capabilities":
        return _capabilities_section(section, summary, findings)
    if section.key == "external_dependencies":
        return _dependencies_section(section, findings)
    if section.key == "integrations":
        return _integrations_section(section, findings)
    if section.key == "cross_cutting":
        return _cross_cutting_section(section, findings)
    if section.key == "entities":
        return _entities_section(section, notes, findings)
    if section.key == "hard_specifications":
        return _hard_specs_section(section, findings)
    if section.key == "inline_schematics":
        return _schematics_section(section, notes)
    return _generic_section(section, findings)


def _section_intro(section: SectionDefinition) -> str:
    return f"## {section.title}\n\n{section.purpose}\n"


def _domains_section(section: SectionDefinition, assessment: IntrospectionAssessment, findings: list[str]) -> str:
    rows = [
        ("Automated Knowledge Translation", "Core", "Transforms source evidence into migration-ready system intent."),
        (
            "Repository Introspection and Curation",
            "Supporting",
            "Discovers and filters production-relevant source evidence.",
        ),
        (
            "Semantic Extraction and Analysis",
            "Core",
            "Turns source artifacts into domain knowledge notes.",
        ),
        (
            "Information Aggregation and Synthesis",
            "Core",
            "Composes coherent wiki sections from extracted notes.",
        ),
        (
            "Pipeline Orchestration and Lifecycle",
            "Supporting",
            "Controls stage order, workspace state, and execution reporting.",
        ),
        (
            "External Intelligence Integration",
            "Generalized",
            "Isolates reasoning backend interaction behind a provider boundary.",
        ),
    ]
    return "\n\n".join(
        [
            _section_intro(section),
            "### Primary Classification",
            bullet_list(assessment.primary_languages, fallback="No primary source classification was available."),
            "### Bounded Contexts",
            markdown_table(("Subdomain", "Classification", "Responsibility"), rows),
            "### Evidence-Based Findings",
            bullet_list(findings, fallback="No source-level domain findings were extracted."),
            _gap_block(assessment.notable_gaps),
            "",
        ]
    )


def _intent_section(section: SectionDefinition, assessment: IntrospectionAssessment, findings: list[str]) -> str:
    return "\n\n".join(
        [
            _section_intro(section),
            "### Purpose",
            assessment.inferred_purpose,
            "### Problem Space",
            bullet_list(
                findings,
                fallback="The allowed source did not explicitly state a deeper problem-space narrative.",
            ),
            "### Scope Rationale",
            assessment.classification_rationale,
            "### Operational Boundary",
            assessment.scope_description,
            _gap_block(assessment.notable_gaps),
            "",
        ]
    )


def _capabilities_section(section: SectionDefinition, summary: DirectorySummary, findings: list[str]) -> str:
    rows = [
        ("Given", "A repository with mixed source and non-source artifacts."),
        ("When", "wikifi walks the repository through the configured source boundary."),
        ("Then", "It produces domain-focused documentation from included production artifacts."),
    ]
    return "\n\n".join(
        [
            _section_intro(section),
            "### Extracted Capabilities",
            bullet_list(findings, fallback="No capability findings were extracted from the selected source."),
            "### Behavioral Contract",
            markdown_table(("Clause", "Statement"), rows),
            "### Traversal Result",
            f"{summary.selected_file_count} source files were selected from {summary.file_count} traversable files.",
            "",
        ]
    )


def _dependencies_section(section: SectionDefinition, findings: list[str]) -> str:
    return "\n\n".join(
        [
            _section_intro(section),
            "### Dependency Roles",
            bullet_list(
                findings,
                fallback=(
                    "No concrete third-party or infrastructure dependencies were detected inside the production source "
                    "boundary."
                ),
            ),
            "### Gap Declaration",
            (
                "Authentication, rate limiting, and provider-side quota behavior are not inferable unless source "
                "evidence states them."
            ),
            "",
        ]
    )


def _integrations_section(section: SectionDefinition, findings: list[str]) -> str:
    rows = [
        ("Given", "A user invokes the command interface."),
        ("When", "The orchestrator receives the request."),
        ("Then", "It delegates work through introspection, extraction, aggregation, and derivation in sequence."),
    ]
    return "\n\n".join(
        [
            _section_intro(section),
            "### Touchpoints",
            bullet_list(findings, fallback="No integration touchpoints were explicit in the selected source."),
            "### Behavioral Handoff",
            markdown_table(("Clause", "Statement"), rows),
            "",
        ]
    )


def _cross_cutting_section(section: SectionDefinition, findings: list[str]) -> str:
    rows = [
        ("Traceability", "Extraction notes preserve file references, source digests, and evidence snippets."),
        (
            "Fault Tolerance",
            "Unreadable, malformed, oversized, and near-empty inputs are skipped or truncated with metrics.",
        ),
        ("Determinism", "Traversal, extraction fallback, aggregation, and derivation use stable ordering."),
        ("Data Integrity", "Missing or ambiguous evidence is declared as a gap instead of fabricated."),
    ]
    return "\n\n".join(
        [
            _section_intro(section),
            "### Cross-Cutting Findings",
            bullet_list(findings, fallback="No additional cross-cutting findings were extracted."),
            "### Guardrail Matrix",
            markdown_table(("Concern", "Carried-Forward Requirement"), rows),
            "",
        ]
    )


def _entities_section(section: SectionDefinition, notes: tuple[ExtractionNote, ...], findings: list[str]) -> str:
    rows = [
        (
            note.file_reference,
            note.role_summary,
            ", ".join(sorted(key for key, items in note.categories.items() if items)),
        )
        for note in notes
    ]
    if not rows:
        rows = [("No source artifact", "No entity evidence was available.", "Gap")]
    return "\n\n".join(
        [
            _section_intro(section),
            "### Entity and Structure Findings",
            bullet_list(findings, fallback="No entity structures were extracted from selected source files."),
            "### Source-to-Concept Trace",
            markdown_table(("Source", "Role", "Evidence Categories"), rows),
            "",
        ]
    )


def _hard_specs_section(section: SectionDefinition, findings: list[str]) -> str:
    rows = [
        ("Given", "A file is larger than the configured byte threshold."),
        ("When", "The traversal stage reads it."),
        ("Then", "The content is truncated to the configured limit before extraction."),
        ("Given", "A file is unreadable, malformed, binary, or below the minimum content threshold."),
        ("When", "The traversal stage encounters it."),
        ("Then", "The file is skipped, counted, and the pipeline continues."),
        ("Given", "A provider other than the supported local provider is configured."),
        ("When", "The command validates runtime settings."),
        ("Then", "The run fails gracefully with a clear unsupported-provider message."),
    ]
    return "\n\n".join(
        [
            _section_intro(section),
            "### Carry-Forward Requirements",
            bullet_list(findings, fallback="No hard specifications were extracted from selected source files."),
            "### Behavioral Specifications",
            markdown_table(("Clause", "Statement"), rows),
            "### Gap Declaration",
            (
                "Contradiction resolution between source files is reported but not automatically adjudicated beyond "
                "preserving evidence."
            ),
            "",
        ]
    )


def _schematics_section(section: SectionDefinition, notes: tuple[ExtractionNote, ...]) -> str:
    sources = [note.file_reference for note in notes[:8]]
    source_nodes = "\n".join(
        f"  Extraction --> {node_id(index)}[{_short_label(path)}]" for index, path in enumerate(sources)
    )
    if not source_nodes:
        source_nodes = "  Extraction --> Empty[No selected source artifacts]"
    return "\n\n".join(
        [
            _section_intro(section),
            "### Stage-Gated Knowledge Flow",
            "```mermaid\ngraph TD\n"
            "  Introspection[Repository Introspection]\n"
            "  Extraction[Semantic Extraction]\n"
            "  Aggregation[Section Aggregation]\n"
            "  Derivation[Derivative Capture]\n"
            "  Introspection --> Extraction\n"
            f"{source_nodes}\n"
            "  Extraction --> Aggregation\n"
            "  Aggregation --> Derivation\n"
            "```",
            "### Gap Declaration",
            "Diagrams represent aggregate source relationships and must not be treated as implementation architecture.",
            "",
        ]
    )


def _generic_section(section: SectionDefinition, findings: list[str]) -> str:
    return "\n\n".join([_section_intro(section), bullet_list(findings, fallback="No findings available."), ""])


def _gap_block(gaps: tuple[str, ...]) -> str:
    if not gaps:
        return "### Gap Declaration\nNo gaps were detected for this section."
    return "### Gap Declaration\n" + bullet_list(gaps, fallback="No gaps were detected for this section.")


def _short_label(path: str) -> str:
    return Path(path).stem.replace("_", " ").replace("-", " ").title() or "Source"


def node_id(index: int) -> str:
    return f"S{index}"
