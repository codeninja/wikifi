"""Prompt templates for the four pipeline stages.

All synthesized output is technology-agnostic: the LLM is instructed to
strip language/framework names and surface intent, behaviour, and
domain concepts. Markdown bodies omit top-level (H1) headings — every
``.wikifi/*.md`` file starts at H2 (``##``).
"""

from __future__ import annotations

from textwrap import dedent

# --- system prompts ---------------------------------------------------------

SYSTEM_BASE = dedent(
    """
    You are wikifi, a technology-agnostic documentation engine. You read
    source artifacts and translate them into business intent and behaviour,
    deliberately stripping language-, framework-, and library-specific
    vocabulary. Never name a programming language, framework, ORM, web
    server, or library in your output. Never mention file paths, function
    names, or class names in synthesized prose — refer to the *capability*
    they implement instead. Refuse to fabricate: if upstream evidence is
    missing or contradictory, declare the gap explicitly.
    """
).strip()


# --- stage 1: introspection -------------------------------------------------

INTROSPECTION_USER = dedent(
    """
    Examine the high-level layout of a target repository and produce a
    JSON assessment.

    Repository tree (depth-limited):
    ```
    {tree}
    ```

    Directory statistics:
    - file_count_in_scope: {file_count}
    - total_bytes_in_scope: {total_bytes}
    - extension_distribution: {extension_distribution}
    - manifests_present: {manifests}
    - sample_paths: {samples}

    Return a JSON object with these fields and nothing else:
    - primary_languages: list of likely primary languages, by evidence weight.
      It is acceptable to use language names HERE only — this is meta
      classification, not synthesized prose.
    - inferred_purpose: a concise (<= 60 word) technology-agnostic statement
      of what the system appears to do and for whom.
    - classification_rationale: <= 80 words explaining the evidence used.
    - in_scope_globs: glob patterns of files that look like production
      source carrying business intent.
    - out_of_scope_globs: glob patterns of files that should be ignored
      during extraction (build artefacts, fixtures, vendored code, examples).
    - notable_manifests: subset of manifests_present that are most useful
      for understanding system purpose.
    """
).strip()


# --- stage 2: extraction ----------------------------------------------------

EXTRACTION_USER = dedent(
    """
    A single source artefact from the target repository is provided below.
    Extract its DOMAIN intent — what business behaviour or capability it
    implements — and produce a structured JSON record.

    File reference (for traceability only — do NOT mention this path in
    role_summary or finding text):
        {path}

    Inferred system purpose (from introspection): {purpose}

    Source content (truncated to the first {max_bytes} bytes if larger):
    ```
    {content}
    ```

    JSON schema requirements:
    - role_summary: one or two sentences, technology-agnostic, describing
      the responsibility this artefact carries inside the system. No file
      names, no language names, no framework names.
    - findings: a list of zero or more entries, each tagging a section
      id and a single tech-agnostic finding paragraph. Allowed section
      ids:
        * intent — purpose, problem space, design constraints
        * capabilities — value proposition, what the system does for users
        * domains — bounded contexts, subdomains, domain relationships
        * entities — core data structures, fields, invariants, relationships
        * integrations — internal pipeline handoffs, internal/external touchpoints
        * external_dependencies — third-party services, infrastructure, standards
        * cross_cutting — observability, data integrity, state management, auth
        * hard_specifications — non-negotiable rules, thresholds, immutable contracts
      Pick only sections the artefact actually informs. Skip irrelevant ones.
    - skip_reason: set to a short string only when the artefact carries no
      extractable production intent (configuration boilerplate, empty stub,
      generated lockfile). Set to null otherwise. When skip_reason is set,
      findings must be empty.

    Forbidden in finding text: file paths, function/class names, language
    names, framework names, library names. Speak in terms of business
    capability and behaviour.
    """
).strip()


# --- stage 3: aggregation ---------------------------------------------------

AGGREGATION_SYSTEM = dedent(
    """
    {base}

    You are now synthesizing one section of a wiki from many per-file
    notes. Output is markdown only — no preamble, no closing remarks, no
    code fences around the whole reply. Begin directly with an H2 heading
    (``## Heading``) — do NOT emit a top-level H1 (``# Heading``). Use
    sub-headings, bulleted lists, and tables for structure. Use Mermaid
    code fences (```mermaid ... ```) only when a diagram clarifies the
    prose, never as decoration. When evidence is missing, contradictory,
    or thin, write an explicit ``### Documented Gaps`` paragraph rather
    than padding with speculation.
    """
).strip()


SECTION_GUIDANCE: dict[str, str] = {
    "intent": (
        "Convey the system's *why*: purpose, problem statement, target audience, "
        "design constraints, and operational boundaries. Cover what is in scope "
        "and what is explicitly out of scope. Surface tensions or trade-offs the "
        "evidence reveals."
    ),
    "capabilities": (
        "Convey *what the system does for its users*: value proposition, key "
        "capabilities, the order in which capability stages execute, and the "
        "quality-assurance and adaptive-configuration affordances that surround "
        "them. Frame everything in domain language."
    ),
    "domains": (
        "Identify the core domain and its bounded contexts/subdomains. Classify "
        "each subdomain (Core / Supporting / Generalized) where the evidence "
        "supports it. Describe the data flow between contexts. Note state "
        "management decisions visible in the evidence."
    ),
    "entities": (
        "Enumerate the core domain entities, their primary fields, key "
        "invariants, and relationships. Group entities by responsibility "
        "(configuration, analysis, extraction, aggregation, reporting). Use a "
        "table for the field/invariant summary when it improves clarity."
    ),
    "integrations": (
        "Describe internal pipeline handoffs in directional terms (component A "
        "supplies X to component B). Describe external interfaces — AI provider, "
        "filesystem, console, telemetry — through their abstraction contracts. "
        "Provide a touchpoint summary table."
    ),
    "external_dependencies": (
        "List the external systems and standards the application relies on, with "
        "the role each plays. Treat AI inference as a swappable abstraction. "
        "Include filesystem access, validation frameworks, markup/diagram "
        "standards, and ignore-pattern logic."
    ),
    "cross_cutting": (
        "Cover concerns that span the whole system: observability and "
        "monitoring, data integrity and traceability, state management and "
        "storage, operational guardrails (timeouts, size caps, reasoning mode "
        "controls, determinism), and authentication/authorization (declare a gap "
        "if absent)."
    ),
    "hard_specifications": (
        "Enumerate non-negotiable rules: pipeline ordering, single-provider "
        "constraint, workspace auto-provisioning, deterministic execution, "
        "immutable exclusions, strict size thresholds, fault tolerance, "
        "structural recognition, technology-agnostic translation, narrative "
        "synthesis, behavioural Given/When/Then format, visual constraints, "
        "explicit gap reporting, configuration precedence, intermediate-artefact "
        "isolation, immutable directory schema."
    ),
}


AGGREGATION_USER = dedent(
    """
    Section to synthesize: **{section_id}**

    Section guidance: {guidance}

    Inferred system purpose (from introspection): {purpose}

    The notes below were produced one-per-file by an extraction pass.
    Deduplicate, align terminology, and weave them into a coherent
    technology-agnostic narrative. Speak only in domain/behavioural
    terms — strip any residual implementation jargon. Do not list raw
    notes verbatim.

    Notes:
    {notes_block}

    Reminder: begin output with an H2 heading. No top-level H1. Use
    ``### Documented Gaps`` when evidence is incomplete. Do not fabricate.
    """
).strip()


# --- stage 4: derivation ----------------------------------------------------

PERSONAS_USER = dedent(
    """
    Derive 2-4 user personas for the system from the synthesized primary
    sections below. Personas must come from the AGGREGATE — never from a
    single source artefact.

    For each persona include: focus statement, goals, needs, pain points,
    and the served use cases or pipeline capabilities. Conclude with a
    persona-to-pipeline mapping table. End with a ``### Documented Gaps``
    block listing dimensions the evidence does not pin down.

    Begin directly with an H2 heading. Do NOT emit a top-level H1.

    Synthesized primary sections:
    {primary_block}
    """
).strip()


USER_STORIES_USER = dedent(
    """
    Derive Gherkin-style user stories covering the system's core
    features, keyed to the personas summary below. Each story MUST follow
    this structure:

    ### Feature: <name>
    **User Story**
    As a <persona>, I want <capability>, so that <outcome>.

    ```gherkin
    Given <context>
    When <event>
    Then <observable outcome>
    And <additional outcome>
    ```

    **Entities Involved:** `Entity1`, `Entity2`
    **Acceptance Criteria:**
    - <criterion>
    - *(Gap Declaration)* <if applicable>

    Cover at least the major capabilities surfaced in the primary
    sections. Conclude with a story-to-component mapping table.

    Begin output with an H2 heading. Do NOT emit a top-level H1.

    Personas summary:
    {personas_block}

    Synthesized primary sections (for capability and entity grounding):
    {primary_block}
    """
).strip()


DIAGRAMS_USER = dedent(
    """
    Produce three technology-agnostic diagrams describing the system,
    each in a Mermaid code fence. Required diagrams:

    1. **Domain Map** — a ``graph TD`` showing the core domain and its
       bounded contexts/subdomains and their relationships.
    2. **Entity Relationship View** — an ``erDiagram`` of the core
       entities, their primary fields, and the relationships between them.
    3. **Integration Flow** — a ``sequenceDiagram`` of the pipeline
       handoffs, including the AI abstraction, observability, and
       storage participants.

    Each diagram is preceded by an H3 sub-heading and followed by a
    ``**Key Observations:**`` bulleted list. Conclude with a
    ``### Documented Gaps`` block when relevant.

    Begin output with an H2 heading. Do NOT emit a top-level H1.

    Synthesized primary sections (use them as the source of truth):
    {primary_block}
    """
).strip()
