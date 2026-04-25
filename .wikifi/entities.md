# Core Entities

The domain models revolve around three primary concerns: defining analysis boundaries, capturing structural and textual data from the target workspace, and producing structured documentation artifacts. Entities are organized by their role in the analysis lifecycle.

#### Scope & Configuration Entities
These entities establish the parameters and limits for the processing pipeline.
- **Analysis Scope:** Defines traversal boundaries and filtering rules. It tracks the target root directory, additional exclusion patterns, a flag for version-control ignore compliance, and a maximum allowable file size.
- **Introspection Decision:** Captures the outcome of the initial workspace evaluation. It records include/exclude path patterns, identified runtimes (informational only), a concise summary of the system’s likely purpose, and the rationale behind classification choices.
- **Configuration Profile:** Stores connection parameters required to interface with the external processing service, including provider identifiers, model specifications, and host endpoints.

#### Workspace & Content Representation
These entities abstract the filesystem into processable units without exposing low-level I/O details.
- **Documentation Workspace / Wiki Layout:** Defines the target directory structure and computes derived paths for configuration files, documentation sections, and state-tracking artifacts.
- **Directory Snapshot:** Provides a non-recursive view of a directory. It records the relative path, file count, total byte size, the most frequent file extensions, and a list of recognized configuration or documentation files.
- **Manifest Content:** Maps relative file paths to their textual content for downstream processing.

#### Extraction & Documentation Artifacts
These entities represent intermediate findings and final documentation outputs.
- **Extraction Finding:** Links a specific source file to a target documentation section, accompanied by a technology-agnostic description of its role.
- **Extraction Note:** A timestamped record of intermediate analysis results, logically grouped by their corresponding documentation section.
- **Documentation Section:** Represents a distinct wiki category. It encapsulates a title, a descriptive summary, and a dynamically generated markdown body.
- **Processing Summary:** Tracks operational metrics, including the volume of files processed, successful extractions, and skipped items.
- **Pipeline Execution Report:** A consolidated artifact that aggregates metrics and results across the introspection, extraction, and aggregation phases.

#### Cross-Entity Invariants
The following constraints must hold true across the domain to ensure data integrity and deterministic processing:

| Entity | Invariant |
|---|---|
| **Analysis Scope** | The target root must resolve to a valid directory; the maximum file size threshold must be strictly positive. |
| **Introspection Decision** | Include and exclude patterns must be mutually exclusive and collectively cover the analyzed scope. Output must strictly conform to a predefined schema. |
| **Directory Snapshot** | File extension counts are capped at the top ten. Notable configuration/documentation files are identified exclusively via a fixed registry of standard manifest names. |
| **Manifest Content** | Textual content is truncated to a safe processing length to prevent context overflow during analysis. |

#### Relationships & Data Flow
The entities interact in a sequential pipeline:
1. **Configuration Profile** and **Analysis Scope** initialize the run.
2. The system evaluates the workspace, producing an **Introspection Decision** that refines traversal boundaries.
3. Refined boundaries drive the creation of **Directory Snapshots** and **Manifest Content** objects.
4. Content is analyzed to generate **Extraction Findings** and **Extraction Notes**, which are routed to specific **Documentation Sections**.
5. Final outputs are organized within the **Documentation Workspace**, while **Processing Summaries** and **Pipeline Execution Reports** capture lifecycle metrics.

#### Known Gaps
- Field definitions for the **Pipeline Execution Report** and **Processing Summary** are not detailed in the available notes; only their high-level purposes are documented.
- The exact mechanism for how **Extraction Notes** are aggregated into the final **Documentation Section** markdown body is not specified.
- No explicit validation rules are provided for the **Configuration Profile** parameters beyond their existence.
