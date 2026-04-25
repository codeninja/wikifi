## Cross-Cutting Concerns

Observability, data integrity, security, storage, and operational guardrails.


### Cross-Cutting Findings

- Aggregation preserves operational visibility, fault tolerance, or traceability concerns.
- Cli preserves operational visibility, fault tolerance, or traceability concerns.
- Config preserves operational visibility, fault tolerance, or traceability concerns.
- Constants preserves operational visibility, fault tolerance, or traceability concerns.
- Derivation preserves operational visibility, fault tolerance, or traceability concerns.
- Extraction preserves operational visibility, fault tolerance, or traceability concerns.
- Introspection preserves operational visibility, fault tolerance, or traceability concerns.
- Models preserves operational visibility, fault tolerance, or traceability concerns.
- Orchestrator preserves operational visibility, fault tolerance, or traceability concerns.
- Providers preserves operational visibility, fault tolerance, or traceability concerns.
- Reporting preserves operational visibility, fault tolerance, or traceability concerns.
- Text preserves operational visibility, fault tolerance, or traceability concerns.
- Traversal preserves operational visibility, fault tolerance, or traceability concerns.
- Workspace preserves operational visibility, fault tolerance, or traceability concerns.

### Guardrail Matrix

| Concern | Carried-Forward Requirement |
| --- | --- |
| Traceability | Extraction notes preserve file references, source digests, and evidence snippets. |
| Fault Tolerance | Unreadable, malformed, oversized, and near-empty inputs are skipped or truncated with metrics. |
| Determinism | Traversal, extraction fallback, aggregation, and derivation use stable ordering. |
| Data Integrity | Missing or ambiguous evidence is declared as a gap instead of fabricated. |

