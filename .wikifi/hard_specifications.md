# Hard Specifications

### Pipeline Execution & Stage Ordering
The processing workflow enforces a strict sequential execution model. Stages must complete in the following immutable order: **Introspection → Extraction → Aggregation → Derivation**. Deviations from this sequence are not permitted. The system is constrained to a single designated processing engine; configuration attempts targeting alternative backends must fail gracefully without interrupting the pipeline. If the documentation workspace is absent at runtime, the system must automatically provision it before initiating any stage.

### Data Ingestion & File Management
File discovery and handling adhere to fixed boundaries to ensure predictable resource consumption:
- **Immutable Exclusion List**: Version control metadata, dependency caches, build artifacts, and tool-specific directories are permanently excluded from analysis.
- **Size Thresholds**: Files exceeding the maximum limit are truncated to preserve pipeline continuity. Files falling below the minimum stripped content threshold are discarded. Invalid or unreadable files are logged and skipped without halting execution.
- **Structural Analysis**: Directory traversal relies on a predefined set of notable manifest and documentation filenames to identify structural anchors.
- **Intermediate Artifacts**: Temporary notes and derivation caches are excluded from version control by default to prevent repository bloat.

| Constraint | Value | Enforcement Behavior |
|---|---|---|
| Maximum file size | 200,000 bytes | Truncate to limit |
| Minimum stripped content | 64 bytes | Discard if below threshold |
| Invalid/unreadable files | N/A | Log and skip; pipeline continues |

### Output Generation & Content Standards
All synthesized content must conform to a strict validation schema and adhere to the following presentation rules:
- **Domain Translation**: Technical observations must be converted into user-facing, technology-agnostic terminology. Framework-specific or language-specific references are prohibited.
- **Narrative Structure**: Outputs must form coherent, structured narratives rather than raw transcripts or fragmented notes. Behavioral descriptions must follow a strict `Given/When/Then` format.
- **Formatting Conventions**: Markdown sub-headings, lists, and tables must be applied appropriately. Top-level headings are excluded from generated content. Diagrams must use valid, standardized syntax with preferred chart types.
- **Gap Declaration Policy**: Missing, incomplete, or failed derivations must explicitly declare the gap and preserve upstream evidence. Silent blanks or fabricated content are strictly prohibited.

### Configuration & Compatibility Contracts
- **Precedence Rules**: Local configuration files override environment variables when both are present.
- **Directory Layout Contract**: The documentation directory structure is a strict backward-compatibility contract. Modifications to the layout will break existing wiki readability and are not permitted without a formal migration protocol.

### Performance Thresholds & Determinism
Processing operations are bound by fixed latency and reliability constraints to guarantee consistent delivery:
- **Deterministic Generation**: Structured output must operate with zero stochastic sampling. All results must be reproducible across identical inputs.
- **Timeout & Latency Bounds**: Request processing must respect a hard maximum timeout of 300 seconds. Standard operations are expected to complete within a target latency window of 15–60 seconds.
- **Input Calibration**: Processing configurations must be explicitly calibrated to prevent timeout failures on minimal or lightweight inputs while maintaining strict schema compliance.

> **Note**: The provided specifications are comprehensive for pipeline execution, data handling, and output standards. No contradictions were identified across the source notes. If future releases introduce multi-engine support or dynamic directory layouts, these hard constraints will require formal revision.
