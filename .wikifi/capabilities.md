# Capabilities

The system is an automated documentation generation tool that produces a comprehensive, technology-agnostic wiki from an existing codebase. Its core value proposition is making implicit knowledge explicit, surfacing hidden inconsistencies, and keeping documentation current with low marginal effort on subsequent runs.

### Four-Stage Analysis Pipeline

Documentation is produced through a coordinated four-stage pipeline:

1. **Repository Introspection** — The system examines the directory layout and manifest files of a target repository, classifying paths as worth analyzing (production source, business logic, domain models, integrations) or worth skipping (vendored dependencies, build output, test code, CI configuration). The classification is returned as a structured, diffable result.

2. **Per-File Extraction** — Each included file is analyzed to produce structured findings describing what it contributes to each wiki section. Large files are split into overlapping windows so no content is missed; adjacent windows share a configurable overlap region to preserve cross-boundary context. Findings are deduplicated across window boundaries so a single declaration is never counted twice. Each finding carries a precise citation (path and line range) so it can be traced later.

3. **Section Aggregation** — Findings collected from all files are synthesized into coherent markdown narratives for each primary wiki section. Every claim in the narrative is backed by numbered citations pointing to the originating files and line ranges.

4. **Derivative Synthesis** — User personas, scenario-based user stories, and architectural diagrams are generated from the finalized primary section bodies. If upstream sections are empty, the system writes a placeholder declaring the gap rather than fabricating content.

### Structured Documentation Output

The wiki is organized into **eight primary sections** — business domains, system intent, capabilities, external dependencies, integrations, cross-cutting concerns, core entities, and hard specifications — plus three **derivative sections** (personas, scenario-based user stories, and architectural diagrams). Derivative sections are only generated after all primary sections are finalized and declare which primaries they depend on.

### Schema-Aware Extraction

Files recognized as data-definition schemas, API contract specifications, interface definition files, or schema migration scripts are processed by deterministic, format-specific extractors rather than the general AI path. This improves both accuracy and cost for schema-heavy artifacts. These extractors surface:

- **Data schema files** — persisted entities with their columns, foreign-key relationships, uniqueness and nullability invariants, index definitions, and ALTER-based schema additions distinguished from the original baseline.
- **API contract files** — the full list of endpoints (operation, path, summary), named request/response models, and aggregate endpoint and model counts.
- **Interface definition files** — message types, closed-value enum types, named services, and their remote procedure calls including streaming legs.
- **Query/mutation schema files** — every operation root field, including fields defined across multiple composed schema files, so capabilities spread across modular definitions are all surfaced.

### Conflict Detection

When source files contain incompatible assertions about the same domain topic, the system surfaces the disagreement explicitly in a dedicated
