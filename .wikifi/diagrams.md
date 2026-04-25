# Diagrams

### Domain Map
The following graph visualizes the primary bounded context and its decomposition into specialized subdomains. It highlights the sequential dependency chain coordinated by the orchestration layer, alongside supporting contexts that persist state and provide generative capabilities.

```mermaid
graph TD
    Core[Automated Knowledge Transformation]
    Orch[Pipeline Orchestration]
    Intros[Repository Introspection & Curation]
    Ext[Semantic Extraction]
    Agg[Information Aggregation]
    Deriv[Artifact Derivation]
    ExtInt[External Intelligence Integration]
    WS[Workspace & State Management]

    Core --> Orch
    Orch -->|Coordinates Sequential Flow| Intros
    Intros -->|Curated Manifest| Ext
    Ext -->|Structured Notes| Agg
    Agg -->|Synthesized Sections| Deriv

    Ext -.->|Optional Semantic Translation| ExtInt
    Intros -.->|Intermediate Outputs| WS
    Ext -.->|Intermediate Outputs| WS
    Agg -.->|Intermediate Outputs| WS
    Deriv -.->|Intermediate Outputs| WS
```

### Entity Relationship View
This entity-relationship diagram maps the core domain objects, their primary attributes, and the structural dependencies that govern data flow through the pipeline. Relationships reflect the hierarchical configuration model, analysis boundaries, and cross-cutting observation points.

```mermaid
erDiagram
    CONFIGURATION {
        string default_settings
        string local_overrides
    }
    SCAN_TRAVERSAL_CONFIG {
        string root_path
        string inclusion_exclusion_patterns
        int size_thresholds
    }
    DIRECTORY_SUMMARY {
        int file_count
        int total_size
        string extension_distribution
        bool manifest_presence
    }
    INTROSPECTION_ASSESSMENT {
        string primary_languages
        string inferred_purpose
        string classification_rationale
    }
    EXTRACTION_NOTE {
        datetime timestamp
        string file_reference
        string role_summary
        string extracted_finding
    }
    DOCUMENTATION_SECTION {
        string category
        string aggregated_content
        string final_markdown_body
    }
    AGGREGATION_STATS {
        int successful_writes
        int empty_section_count
    }
    EXECUTION_SUMMARY {
        string stage_metrics
        string completion_status
        string consolidated_findings
    }

    CONFIGURATION ||--o{ SCAN_TRAVERSAL_CONFIG : "dictates boundaries for"
    SCAN_TRAVERSAL_CONFIG ||--o{ DIRECTORY_SUMMARY : "scopes analysis of"
    DIRECTORY_SUMMARY ||--o{ INTROSPECTION_ASSESSMENT : "feeds structural data to"
    INTROSPECTION_ASSESSMENT ||--o{ EXTRACTION_NOTE : "triggers creation of"
    EXTRACTION_NOTE }|--|| DOCUMENTATION_SECTION : "grouped and transformed into"
    DOCUMENTATION_SECTION ||--o{ AGGREGATION_STATS : "updates upon generation"
    EXECUTION_SUMMARY ||--o{ DOCUMENTATION_SECTION : "consolidates metrics for"
```

### Integration Flow
The sequence diagram illustrates the runtime orchestration lifecycle, stage handoffs, external service abstraction, and observability integration. It emphasizes the unidirectional data flow and the centralized configuration contract that governs execution.

```mermaid
sequenceDiagram
    participant Op as Operator/Interface
    participant Orch as Pipeline Orchestrator
    participant Conf as Configuration Provider
    participant WS as Workspace & State Manager
    participant Intros as Traversal & Introspection
    participant Ext as Extraction
    participant ExtInt as External Intelligence Backend
    participant Agg as Aggregation
    participant Deriv as Derivation
    participant Obs as Observability & Logging

    Op->>Orch: Trigger execution command
    Orch->>Conf: Retrieve runtime parameters & scoping rules
    Conf-->>Orch: Return configuration
    Orch->>WS: Provision documentation workspace
    WS-->>Orch: Confirm workspace ready

    Orch->>Intros: Initiate repository scan & filtering
    Intros->>Intros: Generate directory summaries & assessments
    Intros-->>Orch: Return filtered paths & structural metadata
    Obs->>Obs: Log stage metrics & progress

    Orch->>Ext: Pass filtered file lists & constraints
    Ext->>Ext: Translate artifacts to structured notes
    alt Complex semantic translation required
        Ext->>ExtInt: Submit request via unified provider contract
        ExtInt-->>Ext: Return structured/unstructured response
    end
    Ext-->>Orch: Return extraction notes
    Obs->>Obs: Update processing statistics

    Orch->>Agg: Forward structured notes
    Agg->>Agg: Consolidate & resolve contradictions
    Agg-->>Orch: Return synthesized documentation sections
    Obs->>Obs: Track aggregation success & gaps

    Orch->>Deriv: Deliver finalized sections
    Deriv->>Deriv: Generate derivative knowledge assets
    Deriv-->>Orch: Return polished documentation
    Obs->>Obs: Finalize execution summary & health report

    Orch-->>Op: Report completion & output readiness
```

### Modeling Constraints & Documented Gaps
The diagrams above reflect the architectural boundaries and data flows explicitly defined in the upstream specifications. The following areas remain unspecified and are intentionally omitted from the visual models:
- **Note-to-Section Mapping Rules:** The exact grouping, prioritization, or filtering logic used during section assembly is implied by the aggregation process but not formally defined.
- **Error Handling & Resilience:** Retry mechanisms, fallback behaviors, and conflict resolution strategies for external service failures or stage interruptions are not documented.
- **Inter-Stage Serialization:** The precise data exchange format used between pipeline stages is undefined, though the flow assumes structured, technology-agnostic payloads.
- **State Consolidation Boundary:** Pipeline orchestration and workspace management are modeled as distinct contexts; if execution coordination and state persistence are tightly coupled in practice, they may warrant consolidation into a single bounded context.
