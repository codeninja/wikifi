# Core Entities

The documentation generation pipeline relies on a set of core domain entities that manage configuration, source analysis, content extraction, and final output assembly. These entities are organized to enforce consistent processing boundaries, track intermediate findings, and produce structured documentation artifacts.

### Configuration & Processing Boundaries
The system uses a hierarchical configuration model to define how source repositories are scanned and processed. A base settings container manages default values, which can be overridden by local configuration files to ensure environment-specific customization. Scanning and traversal configurations establish the root directory, path inclusion/exclusion filters, and file size constraints. These boundaries ensure that only relevant source files are processed while preventing resource exhaustion from oversized or irrelevant directories.

### Analysis & Introspection
Before content generation, the system performs structural and semantic analysis of the target repository. Directory summaries capture aggregate statistics, including file counts, total size, extension distribution, and the presence of key manifest or documentation files. An introspection assessment synthesizes this structural data to identify primary languages, infer the system's overarching purpose, and document a classification rationale. This assessment respects the previously defined path filters and serves as the foundation for targeted content extraction.

### Extraction & Intermediate Records
During source analysis, intermediate findings are captured as timestamped extraction notes. Each note functions as a structured record that links a specific file reference to a role summary and the extracted finding. These records preserve the context of individual source files and serve as the raw material for downstream aggregation. The system maintains a chronological log of these notes to ensure traceability throughout the pipeline.

### Aggregation & Output Structure
Extracted notes are consolidated into categorized documentation sections. Each section acts as a logical container for generated content, ultimately producing a final markdown body. Aggregation statistics track the success rate of section writes and explicitly flag empty sections to highlight coverage gaps. The final output adheres to a predefined workspace layout that organizes configuration files, intermediate notes, and final section artifacts into a consistent, navigable directory hierarchy.

### Pipeline Execution & Reporting
A unified execution summary consolidates metrics, findings, and completion status across all processing stages. This entity provides a single source of truth for pipeline health, output readiness, and overall processing efficiency, enabling operators to verify that all stages completed successfully before final delivery.

### Entity Fields, Relationships & Invariants
| Entity | Primary Fields | Key Invariants |
|---|---|---|
| Configuration | Default settings, local overrides | Local overrides always take precedence over environment defaults |
| Scan/Traversal Config | Root path, inclusion/exclusion patterns, size thresholds | Processing never exceeds defined size constraints or traverses excluded paths |
| Directory Summary | File count, total size, extension distribution, manifest presence | Statistics reflect only files within allowed traversal boundaries |
| Introspection Assessment | Primary languages, inferred purpose, classification rationale | Assessment is derived strictly from directory summaries and path filters |
| Extraction Note | Timestamp, file reference, role summary, extracted finding | Each note is immutable once created and tied to a single source file |
| Documentation Section | Category, aggregated content, final markdown body | Sections are generated only after successful note aggregation |
| Aggregation Stats | Successful writes, empty section count | Stats are updated atomically after each section generation attempt |
| Workspace Layout | Paths for config, notes, sections | Directory structure remains consistent across pipeline runs |
| Execution Summary | Stage metrics, completion status, consolidated findings | Summary is generated only after all pipeline stages report completion |

**Relationships:** Configuration entities dictate the boundaries for analysis entities. Analysis outputs feed directly into extraction notes, which are then grouped and transformed into documentation sections. Aggregation statistics and the execution summary operate as cross-cutting observers, tracking the health and output of the entire flow.

**Known Gaps:** The exact mapping rules between intermediate extraction notes and final documentation sections are implied by the aggregation process but not explicitly detailed in the available notes. Further specification may be needed to define how notes are grouped, prioritized, or filtered during section assembly, as well as how empty sections are resolved or reported upstream.
