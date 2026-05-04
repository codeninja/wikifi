# Capabilities

The system transforms any source code repository into a structured, human-readable wiki that captures the intent and domain knowledge encoded in that codebase — not its mechanical implementation details.

## Core Wiki Generation

A four-stage pipeline drives the primary transformation:

1. **Repository introspection** — The system scans the repository's directory structure and manifest files to decide which files contain production source worth analysing and which to exclude, producing include/exclude patterns, a language inventory, and a one-paragraph purpose summary.
2. **Per-file extraction** — Every included file is read and its intent-bearing findings are classified into predefined wiki sections. Large files are automatically split so no content is silently lost. Files that use recognised schema or interface-definition formats (data schemas, API contracts, interface definitions, migration scripts) are routed through purpose-built deterministic extractors rather than general-purpose analysis, reducing cost and latency.
3. **Section aggregation** — Per-file findings are synthesised into polished, coherent markdown for each of up to eight primary wiki sections covering business domains, system intent, capabilities, external dependencies, integrations, cross-cutting concerns, core entities, and hard specifications.
4. **Derivative content synthesis** — From the aggregated primary sections the system generates additional content: user personas inferred from capabilities and entities, user stories expressed in structured behavioural notation, and relationship diagrams spanning domains and integrations.

The wiki can be initialised as a browsable stub before any analysis runs, so the structure is always present regardless of pipeline state.

## Traceability and Conflict Surfacing

Every assertion in the generated wiki is annotated with compact citation markers linked to a sources footer that identifies the exact file and line range from which the claim was drawn. This lets readers verify any statement against the original codebase.

When the system detects conflicting information across source files it does not silently resolve or suppress the disagreement. Instead it emits an explicit
