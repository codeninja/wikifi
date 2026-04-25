# Hard Specifications

### Data Serialization & Encoding Standards
All intermediate extraction artifacts and state records must conform to immutable serialization contracts. Data is persisted using a newline-delimited structured record format, with each entry prefixed by a standardized UTC timestamp to guarantee chronological traceability. Character encoding follows a strict standard with a defined replacement-character fallback to prevent processing failures on malformed input.

### Processing Thresholds & Exclusion Policies
System stability and context-window efficiency are maintained through hard-enforced size limits and filtering rules. The following thresholds are non-negotiable:

| Artifact Category | Size Limit | Handling Behavior |
|---|---|---|
| General source files | 200,000 bytes | Automatically bypassed if exceeded |
| Configuration & documentation | 20,000 bytes | Truncated to preserve context capacity |
| Source control metadata, dependency caches, compiled outputs, internal working directories | N/A | Permanently excluded from analysis unless explicitly overridden |

### Structural & Output Contracts
The documentation system operates under a stable directory layout contract that ensures backward compatibility and consistent readability across all generated outputs. All automated synthesis must conform to a predefined structural schema and utilize only approved section identifiers. Deviation from these layout and schema contracts is strictly prohibited to maintain interoperability with downstream consumers.

### Content Synthesis Mandates
Generated documentation must strictly adhere to technology-agnostic principles, translating all technical observations into universal domain terminology. The synthesis process requires merging redundant information, resolving conflicting data points, and constructing a unified narrative rather than presenting raw extraction logs. Each documentation segment must also strictly align with its designated inclusion and exclusion criteria as defined in its operational brief. When source material is insufficient or contradictory, the system must explicitly declare these gaps rather than inferring or fabricating content.

### Specification Gaps
The provided source material does not contain formal service-level agreements (SLAs) or external contractual obligations. These requirements must be defined and integrated separately if they are to be enforced as hard specifications.
