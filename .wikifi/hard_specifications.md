# Hard Specifications

### Pipeline Execution & Architecture
- **Sequential Processing Order:** The system must execute stages in a strict, non-negotiable sequence: Introspection → Extraction → Aggregation → Derivation. Deviations from this order are prohibited.
- **Single-Provider Constraint:** The current release supports only one designated processing backend. Configuration attempts targeting alternative providers must fail gracefully without interrupting the pipeline.
- **Workspace Auto-Provisioning:** The target documentation workspace must be automatically initialized if it does not exist prior to pipeline execution.

### Input Processing & Data Boundaries
- **Deterministic & Non-Destructive Execution:** All processing stages must operate deterministically and preserve original source integrity. No upstream data may be altered or deleted during transformation.
- **Immutable Exclusion Patterns:** Version control metadata, dependency caches, build artifacts, and tool-specific directories are permanently excluded from traversal.
- **Strict Size Thresholds:**
  | Metric | Limit | Handling Behavior |
  |---|---|---|
  | Maximum file size | 200,000 bytes | Truncated to limit |
  | Minimum stripped content | 64 bytes | Files below threshold are ignored |
- **Fault Tolerance:** Invalid or unreadable inputs must be logged and skipped. The pipeline must never halt due to malformed source material.
- **Structural Recognition:** A predefined set of notable manifest and documentation filenames is used exclusively for structural analysis and routing.

### Content Synthesis & Documentation Standards
- **Technology-Agnostic Translation:** All outputs must strip implementation-specific terminology. Technical observations must be translated into domain-focused, user-facing intent.
- **Narrative Synthesis:** Generated content must form a coherent, structured narrative. Raw transcripts, verbatim note dumps, or unprocessed fragments are prohibited.
- **Behavioral Documentation Structure:** All operational or behavioral descriptions must adhere to a strict `Given/When/Then` format.
- **Visual & Formatting Constraints:** Diagrams must utilize standardized syntax with approved chart types. Output must exclude top-level headings and rely exclusively on appropriate markdown sub-headings, lists, and tables.
- **Explicit Gap & Contradiction Reporting:** Missing data, failed derivations, or conflicting upstream evidence must be explicitly declared. The system must preserve original evidence rather than fabricating content or leaving silent blanks.

### Configuration & Artifact Management
- **Configuration Precedence:** Local configuration files strictly override environment-level variables. This hierarchy is immutable.
- **Intermediate Artifact Isolation:** Temporary processing directories (intermediate notes) must be excluded from version control by default to prevent repository bloat and maintain clean lineage.

### Output Structure & Compatibility Contract
- **Immutable Directory Schema:** The documentation directory layout functions as a strict backward-compatibility contract. Structural modifications are prohibited, as they will break existing documentation readability and violate compliance expectations.
