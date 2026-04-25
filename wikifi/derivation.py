from __future__ import annotations

from wikifi.constants import DERIVATIVE_SECTIONS
from wikifi.models import AggregationStats, ExtractionNote, IntrospectionAssessment, WorkspaceLayout
from wikifi.text import bullet_list, dedupe, markdown_table


def derive_sections(
    layout: WorkspaceLayout,
    assessment: IntrospectionAssessment,
    notes: tuple[ExtractionNote, ...],
) -> AggregationStats:
    primary_context = _load_primary_context(layout)
    stats = AggregationStats()
    for section in DERIVATIVE_SECTIONS:
        if section.key == "personas":
            content = _personas(primary_context, assessment, notes)
        elif section.key == "user_stories":
            content = _user_stories(primary_context, assessment, notes)
        elif section.key == "diagrams":
            content = _diagrams(primary_context, notes)
        else:
            content = f"## {section.title}\n\nGap Declaration: no derivative renderer was configured.\n"
        path = layout.derivatives_dir / section.filename
        path.write_text(content, encoding="utf-8")
        stats.record(path, content)
    return stats


def _load_primary_context(layout: WorkspaceLayout) -> str:
    chunks: list[str] = []
    for path in sorted(layout.sections_dir.glob("*.md")):
        try:
            chunks.append(path.read_text(encoding="utf-8"))
        except OSError:
            continue
    return "\n\n".join(chunks)


def _personas(primary_context: str, assessment: IntrospectionAssessment, notes: tuple[ExtractionNote, ...]) -> str:
    capabilities = _category_items(notes, "capabilities")
    dependencies = _category_items(notes, "external_dependencies")
    return "\n\n".join(
        [
            "## User Personas",
            "",
            "Derived from the aggregate primary wiki, not from any single source artifact.",
            "",
            "### Onboarding Engineering Practitioner",
            bullet_list(
                [
                    "Needs a fast, traceable map of system purpose, source boundaries, and domain behavior.",
                    "Uses generated sections to understand production behavior without reverse-engineering every file.",
                    f"Depends on extracted capabilities such as {', '.join(capabilities[:3])}."
                    if capabilities
                    else "Depends on explicit gap declarations when capabilities are not evident.",
                ],
                fallback="No onboarding needs were derivable.",
            ),
            "### Technical Writer and System Architect",
            bullet_list(
                [
                    "Needs stable, technology-agnostic narratives and behavioral specifications.",
                    "Uses section synthesis and diagrams to establish a documentation baseline.",
                    f"Works within the inferred system purpose: {assessment.inferred_purpose}",
                ],
                fallback="No writer or architect needs were derivable.",
            ),
            "### Portfolio Manager and Acquisition Integrator",
            bullet_list(
                [
                    "Needs deterministic repository assessment, pipeline health metrics, and comparable outputs.",
                    "Uses execution reports to verify readiness across unfamiliar or mixed-paradigm repositories.",
                    f"Reviews dependency signals such as {', '.join(dependencies[:3])}."
                    if dependencies
                    else "Reviews explicit absence of dependency evidence when no dependencies are found.",
                ],
                fallback="No portfolio needs were derivable.",
            ),
            "### Gap Declaration",
            (
                "Role-based authorization, access controls, and persona-specific processing presets are not defined "
                "by source evidence."
            ),
            f"Primary context size used for derivation: {len(primary_context)} characters.",
            "",
        ]
    )


def _user_stories(primary_context: str, assessment: IntrospectionAssessment, notes: tuple[ExtractionNote, ...]) -> str:
    capability_items = _category_items(notes, "capabilities")[:4]
    if not capability_items:
        capability_items = ["surface source-backed system intent with explicit gap declarations"]
    stories = []
    for index, capability in enumerate(capability_items, start=1):
        stories.append(
            "\n".join(
                [
                    f"### Feature {index}: {capability.capitalize()}",
                    "",
                    "```gherkin",
                    "Given a target repository within the configured traversal boundary",
                    f"When the wikifi pipeline evaluates evidence to {capability}",
                    "Then the generated wiki documents the behavior in technology-agnostic language",
                    "And the output preserves source traceability and explicit gaps",
                    "```",
                    "",
                    "**Acceptance Criteria:**",
                    "- The behavior is derived from aggregate pipeline evidence.",
                    "- Missing or ambiguous information is declared instead of fabricated.",
                    "- The story remains independent of implementation language or framework choices.",
                ]
            )
        )
    return "\n\n".join(
        [
            "## User Stories",
            "",
            (
                "These stories are synthesized after primary capture for the inferred purpose: "
                f"{assessment.inferred_purpose}"
            ),
            *stories,
            "### Gap Declaration",
            (
                "Contradictory feature evidence is not auto-resolved; consumers must review source-linked notes when "
                "conflict is reported."
            ),
            f"Primary context size used for derivation: {len(primary_context)} characters.",
            "",
        ]
    )


def _diagrams(primary_context: str, notes: tuple[ExtractionNote, ...]) -> str:
    source_rows = [
        (
            note.file_reference,
            note.role_summary,
            ", ".join(sorted(key for key, values in note.categories.items() if values)) or "No category",
        )
        for note in notes[:10]
    ]
    if not source_rows:
        source_rows = [("No selected source", "No aggregate entity evidence was available.", "Gap")]
    entity_lines = "\n".join(
        f"    NOTE_{index} {{\n        string source\n    }}" for index, _ in enumerate(source_rows)
    )
    return "\n\n".join(
        [
            "## Diagrams",
            "",
            "Derived from finalized primary sections and the complete extraction-note set.",
            "",
            "### 10000-Foot Flow",
            "```mermaid\nflowchart TD\n"
            "  User[Knowledge Consumer]\n"
            "  CLI[Command Interface]\n"
            "  Introspection[Repository Introspection]\n"
            "  Extraction[Semantic Extraction]\n"
            "  Aggregation[Primary Wiki Sections]\n"
            "  Derivation[Personas, Stories, Diagrams]\n"
            "  Report[Execution Summary]\n"
            "  User --> CLI --> Introspection --> Extraction --> Aggregation --> Derivation --> Report\n"
            "```",
            "### Entity Evidence Map",
            markdown_table(("Source", "Role", "Categories"), source_rows),
            "```mermaid\nerDiagram\n"
            "    WORKSPACE ||--o{ EXTRACTION_NOTE : contains\n"
            "    EXTRACTION_NOTE }o--o{ DOCUMENTATION_SECTION : informs\n"
            f"{entity_lines}\n"
            "```",
            "### Integration Sequence",
            "```mermaid\nsequenceDiagram\n"
            "  participant Operator\n"
            "  participant CLI\n"
            "  participant Pipeline\n"
            "  participant Provider\n"
            "  participant Wiki\n"
            "  Operator->>CLI: request init or walk\n"
            "  CLI->>Pipeline: load config and enforce stage order\n"
            "  Pipeline->>Provider: request extraction or synthesis through provider boundary\n"
            "  Provider-->>Pipeline: return analysis or trigger fallback gap\n"
            "  Pipeline->>Wiki: write primary and derivative sections\n"
            "  Wiki-->>Operator: expose report and documentation artifacts\n"
            "```",
            "### Gap Declaration",
            "These diagrams are abstract behavior maps and intentionally omit current implementation topology.",
            f"Primary context size used for derivation: {len(primary_context)} characters.",
            "",
        ]
    )


def _category_items(notes: tuple[ExtractionNote, ...], key: str) -> list[str]:
    return dedupe(item for note in notes for item in note.categories.get(key, []))
