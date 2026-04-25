## Cross-Cutting Concerns

Observability, data integrity, security, storage, and operational guardrails.


### Cross-Cutting Findings

- Process lifecycle management via SystemExit
- Traceability: Extraction notes preserve file references, source digests, and evidence snippets.
- Fault Tolerance: Unreadable, malformed, oversized, and near-empty inputs are skipped or truncated with metrics.
- Determinism: Traversal, extraction fallback, aggregation, and derivation use stable ordering.
- Data Integrity: Missing or ambiguous evidence is declared as a gap instead of fabricated.
- Cli preserves operational visibility, fault tolerance, or traceability concerns.
- Configuration validation
- Error handling
- File system filtering logic (exclusions, inclusions, pattern matching).
- Documentation structure definition (SectionDefinition structured record and tuples).
- Gap Declaration: Explicitly documents missing evidence or unconfigured renderers
- Traceability: Links generated content back to source notes and primary context size
- Technology Agnosticism: Outputs avoid specific implementation details
- Preserves operational visibility, fault tolerance, or traceability concerns through provider failure tracking, fallback status reporting, and evidence summarization.
- Error handling for file read operations
- Text cleaning and normalization for README parsing
- Deduplication of language and stem lists
- Path normalization
- Timestamp generation
- Data serialization to dictionaries
- File size and content validation
- Error handling with specific exit codes
- Performance measurement using perf_counter
- Logging and audit trail maintenance
- Workspace state management
- Error Handling (ProviderError, UnsupportedProviderError)
- Configuration (Settings object usage)
- Logging/Debugging (Implicit via error messages)
- Logging
- Reporting
- Serialization
- Text normalization
- Deduplication
- Formatting
- Error handling for unreadable files and metadata
- Logging/Reporting of skipped files with reasons
- Configuration-driven filtering
- Configuration management
- File system operations
- Logging (run.log)

### Guardrail Matrix

| Concern | Carried-Forward Requirement |
| --- | --- |
| Traceability | Extraction notes preserve file references, source digests, and evidence snippets. |
| Fault Tolerance | Unreadable, malformed, oversized, and near-empty inputs are skipped or truncated with metrics. |
| Determinism | Traversal, extraction fallback, aggregation, and derivation use stable ordering. |
| Data Integrity | Missing or ambiguous evidence is declared as a gap instead of fabricated. |

