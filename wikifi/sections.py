"""Capture-scope section taxonomy.

Source: VISION.md "What every generated wiki captures". Each section becomes one
markdown file under `.wikifi/`. The id is the filename stem; title is the
human-facing heading; description guides the LLM during extraction and aggregation.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Section:
    id: str
    title: str
    description: str


SECTIONS: tuple[Section, ...] = (
    Section(
        id="personas",
        title="User Personas",
        description=(
            "Who uses the system. Intent, needs, pain points, usage patterns, "
            "and use cases. Inferred from code, not from real users."
        ),
    ),
    Section(
        id="user_stories",
        title="User Stories",
        description=(
            "Features expressed as Gherkin-style user stories with acceptance "
            "criteria. One feature per story; group related stories together."
        ),
    ),
    Section(
        id="domains",
        title="Domains and Subdomains",
        description=(
            "DDD-style core business domains, subdomains, and their relationships. "
            "Independent of current module boundaries or technology choices."
        ),
    ),
    Section(
        id="intent",
        title="Intent and Problem Space",
        description=(
            "Why the system exists, in the system's own words. What problem it "
            "solves, for whom, and the constraints that shape its design — "
            "decoupled from how it currently solves them."
        ),
    ),
    Section(
        id="capabilities",
        title="Capabilities",
        description=(
            "What the application does and the value it delivers, at a domain "
            "level. No reference to current tech stack or architecture."
        ),
    ),
    Section(
        id="external_dependencies",
        title="External-System Dependencies",
        description=(
            "Third-party APIs, services, infrastructure the system depends on. "
            "Capture the role each plays, not the SDK in use."
        ),
    ),
    Section(
        id="integrations",
        title="Integrations",
        description=(
            "Internal and external integration touchpoints in both directions: "
            "what the system calls into, and what calls into it."
        ),
    ),
    Section(
        id="cross_cutting",
        title="Cross-Cutting Concerns",
        description=(
            "Observability, monitoring, data integrity, authentication and "
            "authorization, data storage. The non-functional invariants that "
            "must be preserved through migration."
        ),
    ),
    Section(
        id="entities",
        title="Core Entities",
        description=(
            "Domain entities, their fields, relationships, and the invariants "
            "that hold across them. Tech-agnostic — describe what the entity is "
            "and what it needs, not which ORM models it."
        ),
    ),
    Section(
        id="hard_specifications",
        title="Hard Specifications",
        description=(
            "Critical requirements that must be carried forward verbatim: "
            "compliance rules, SLAs, contractual obligations, immutable formats."
        ),
    ),
    Section(
        id="diagrams",
        title="Diagrams",
        description=(
            "Mermaid diagrams visualizing domains, entity relationships, and "
            "integration flows. Tech-agnostic — no reference to current stack."
        ),
    ),
)


SECTIONS_BY_ID: dict[str, Section] = {s.id: s for s in SECTIONS}
SECTION_IDS: tuple[str, ...] = tuple(s.id for s in SECTIONS)
