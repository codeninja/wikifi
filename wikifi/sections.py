"""Capture-scope section taxonomy.

Source: VISION.md "What every generated wiki captures". Each section becomes one
markdown file under `.wikifi/`. Sections are split into two tiers:

- **Primary** sections are extracted per-file from direct evidence in the code
  (Stage 2) and synthesized into final markdown by the aggregator (Stage 3).
- **Derivative** sections emerge from the *aggregate* of primary sections —
  they have no per-file evidence to extract from. They are produced in
  Stage 4 by feeding upstream primary section markdown to the model.

Personas and user stories are the canonical derivatives: a single source file
rarely declares "I serve persona X" or "the Gherkin story is Y", so asking for
them at the per-file level produces sparse, speculative findings. Diagrams are
also derivative — they render relationships across domains, entities, and
integrations rather than reading from any one file.

Order in `SECTIONS` is dependency-respecting: every derivative declares its
upstream `derived_from` sections, and they all appear earlier in the tuple.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Tier = Literal["primary", "derivative"]


@dataclass(frozen=True)
class Section:
    id: str
    title: str
    description: str
    tier: Tier = "primary"
    derived_from: tuple[str, ...] = field(default_factory=tuple)


SECTIONS: tuple[Section, ...] = (
    # ----- Primary (extracted per-file in Stage 2 → Stage 3) -----
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
    # ----- Derivative (synthesized after primaries in Stage 4) -----
    Section(
        id="personas",
        title="User Personas",
        description=(
            "Who uses the system, derived from the aggregate of capabilities, "
            "integrations, and intent. Each persona has goals, needs, pain "
            "points, and the use cases the system serves them. Personas are "
            "inferred from what the system does — never invented from a single "
            "module."
        ),
        tier="derivative",
        derived_from=("capabilities", "intent", "entities", "integrations"),
    ),
    Section(
        id="user_stories",
        title="User Stories",
        description=(
            "Features expressed as Gherkin-style user stories ('As a <persona>, "
            "I want <capability>, so that <intent>') with acceptance criteria. "
            "Each story ties an inferred persona to a capability and the "
            "entities involved. Group related stories under feature headings."
        ),
        tier="derivative",
        derived_from=("personas", "capabilities", "entities"),
    ),
    Section(
        id="diagrams",
        title="Diagrams",
        description=(
            "Mermaid diagrams that visualize structural and behavioral "
            "relationships across the system: a domain map (graph or "
            "classDiagram across domains), an entity relationship view "
            "(erDiagram across entities), and an integration flow (sequence "
            "or flowchart across integrations). Tech-agnostic — no reference "
            "to current stack."
        ),
        tier="derivative",
        derived_from=("domains", "entities", "integrations"),
    ),
)


SECTIONS_BY_ID: dict[str, Section] = {s.id: s for s in SECTIONS}
SECTION_IDS: tuple[str, ...] = tuple(s.id for s in SECTIONS)
PRIMARY_SECTIONS: tuple[Section, ...] = tuple(s for s in SECTIONS if s.tier == "primary")
DERIVATIVE_SECTIONS: tuple[Section, ...] = tuple(s for s in SECTIONS if s.tier == "derivative")
PRIMARY_SECTION_IDS: tuple[str, ...] = tuple(s.id for s in PRIMARY_SECTIONS)
DERIVATIVE_SECTION_IDS: tuple[str, ...] = tuple(s.id for s in DERIVATIVE_SECTIONS)


def _validate() -> None:
    """Static checks: derivatives reference real, earlier sections."""
    seen: set[str] = set()
    for section in SECTIONS:
        for upstream in section.derived_from:
            if upstream not in SECTIONS_BY_ID:
                raise ValueError(f"section {section.id!r} references unknown upstream {upstream!r}")
            if upstream not in seen:
                raise ValueError(f"section {section.id!r} depends on {upstream!r}, which appears later in SECTIONS")
        seen.add(section.id)


_validate()
