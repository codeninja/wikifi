# Diagrams

### Domain Map
The following graph visualizes the bounded contexts within the core domain of Automated Knowledge Translation. It reflects the strict, stage-gated dependency chain and the cross-cutting nature of external intelligence integration.

```mermaid
graph TD
  Core[Core Domain: Automated Knowledge Translation]
  Introspection[Repository Introspection & Curation\nSupporting]
  Extraction[Semantic Extraction & Analysis\nCore]
  Aggregation[Information Aggregation & Synthesis\nCore]
  Orchestration[Pipeline Orchestration & Lifecycle Management\nSupporting]
  External[External Intelligence Integration\nGeneralized]

  Core --> Introspection
  Introspection -->|Curated artifacts & structural metadata| Extraction
  Extraction -->|Structured knowledge units & analysis results| Aggregation
  Aggregation -->|Synthesized content & workspace population| Orchestration

  External -.->|On-demand pattern resolution & narrative generation| Extraction
```

**Key Observations:**
- Data flows unidirectionally through the pipeline, with intermediate states explicitly persisted between stages to support incremental processing, auditability, and fault tolerance.
- External Intelligence Integration operates as a generalized, cross-cutting capability invoked on-demand within the extraction context rather than dictating pipeline progression.
- Orchestration and workspace lifecycle management responsibilities currently overlap; future modeling may require separating execution coordination from directory/configuration governance.

### Entity Relationship View
This entity-relationship diagram maps the core domain entities, their primary fields, and the structural boundaries that govern data transformation from raw repository scanning to final documentation assembly.

```mermaid
erDiagram
    CONFIGURATION ||--o{ SCAN_TRAVERSAL_CONFIG : "defines"
    SCAN_TRAVERSAL_CONFIG ||--o{ DIRECTORY_SUMMARY : "scopes"
    DIRECTORY_SUMMARY ||--|| INTROSPECTION_ASSESSMENT : "generates"
    INTROSPECTION_ASSESSMENT ||--o{ EXTRACTION_NOTE : "guides"
    EXTRACTION_NOTE }o--|| DOCUMENTATION_SECTION : "aggregates_to"
    DOCUMENTATION_SECTION ||--o{ AGGREGATION_STATS : "updates"
    DOCUMENTATION_SECTION ||--o{ WORKSPACE_LAYOUT : "populates"
    EXECUTION_SUMMARY }o--|| PIPELINE_EXECUTION : "observes"

    CONFIGURATION {
        string default_settings
        string local_overrides
    }
    SCAN_TRAVERSAL_CONFIG {
        string root_path
        string inclusion_exclusion_patterns
        number size_thresholds
    }
    DIRECTORY_SUMMARY {
        number file_count
        number total_size
        string extension_distribution
        boolean manifest_presence
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
        number successful_writes
        number empty_section_count
    }
    WORKSPACE_LAYOUT {
        string config_paths
        string notes_paths
        string sections_paths
    }
    EXECUTION_SUMMARY {
        string stage_metrics
        string completion_status
        string consolidated_findings
    }
```

**Key Observations:**
- Configuration entities establish hard boundaries for traversal and analysis, ensuring processing never exceeds defined size constraints or excluded paths.
- Extraction notes are immutable, timestamped records tied to single source files, serving as the raw material for downstream aggregation.
- Aggregation statistics and the execution summary function as cross-cutting observers, tracking pipeline health and output readiness without interfering with the primary data flow.
- **Known Gap:** The exact mapping rules between intermediate extraction notes and final documentation sections are implied but not explicitly detailed. Further specification is required to define how notes are grouped, prioritized, or filtered during section assembly, and how empty sections are resolved or reported upstream.

### Integration Flow
The sequence diagram below illustrates the internal pipeline handoffs and external interface interactions. It captures the staged execution model, centralized orchestration, and abstracted external dependencies.

```mermaid
sequenceDiagram
  participant CLI as CLI Interface
  participant Orch as Orchestrator
  participant Traversal as Traversal & Introspection
  participant Extractor as Source Analysis & Extraction
  participant Aggregator as Content Aggregation
  participant Deriver as Derivative Generation
  participant AI as Generative AI Services
  participant Telemetry as Observability & Telemetry
  participant Storage as Wiki Storage

  CLI->>Orch: Trigger execution / provision workspace
  Orch->>Traversal: Delegate scanning & structural analysis
  Traversal->>Traversal: Apply path filters & size constraints
  Traversal-->>Orch: Return filtered paths & metadata
  Orch->>Extractor: Delegate artifact analysis
  Extractor->>AI: Request pattern resolution / narrative generation (on-demand)
  AI-->>Extractor: Return processed findings
  Extractor->>Telemetry: Log processing metrics & outcomes
  Extractor-->>Orch: Return structured analysis notes
  Orch->>Aggregator: Delegate content synthesis
  Aggregator->>AI: Request section-level synthesis
  AI-->>Aggregator: Return synthesized markdown
  Aggregator->>Storage: Write documentation sections
  Aggregator-->>Orch: Return aggregation statistics
  Orch->>Deriver: Delegate supplementary content generation
  Deriver->>AI: Request derivative synthesis
  AI-->>Deriver: Return derivative documentation
  Deriver->>Storage: Write derivative artifacts
  Deriver-->>Orch: Confirm completion
  Orch->>Orch: Consolidate metrics & generate execution summary
  Orch-->>CLI: Report pipeline health & output readiness
```

**Key Observations:**
- The orchestrator acts as the central coordinator, delegating execution to specialized components in a strict sequence while maintaining a single source of truth for pipeline health.
- All external dependencies are routed through standardized contracts, isolating core business logic from provider-specific implementations and enabling swappable analytical backends.
- Observability and telemetry are integrated directly into the extraction stage to monitor processing metrics and record analysis outcomes in real time.
- **Known Gaps:** The integration contracts do not specify exact data schemas or serialization formats for inter-module handoffs. Error handling, retry policies, fallback mechanisms for external service degradation, authentication/rate-limiting constraints, and versioning guarantees between pipeline stages remain undefined and require clarification in implementation documentation.
