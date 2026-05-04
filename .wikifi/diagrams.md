# Diagrams

Three diagrams follow: a domain map, an entity–relationship view, and an integration flow. All representations are technology-agnostic and derived solely from the documented system model.

## Domain Map

Subdomains, their responsibilities, and the directed dependency chain that governs pipeline ordering. No subdomain reaches backwards; the arrows below are the authoritative expression of inter-subdomain dependency.

```mermaid
graph TD
    subgraph CORE["Core Domain — Automated Documentation Synthesis"]
        RI[Repository Introspection]
        KE[Knowledge Extraction]
        SS[Section Synthesis]
        APW[Artefact Persistence — working state]
        APC[Artefact Persistence — committed wiki]
    end

    RI -->|include and exclude scope| KE
    KE -->|extraction notes| APW
    KE -->|evidential record| SS
    SS -->|rendered section markdown| APC
```

## Entity Relationship View

Core entities across all concern areas. Cardinality follows the documented information model.

```mermaid
erDiagram
    SECTION {
        string id PK
        string title
        string brief
        string tier
    }
    SECTION ||--o{ SECTION : "upstream-of"
    WIKI_LAYOUT ||--o{ SECTION : "resolves paths for"
    SECTION_REPORT }o--|| SECTION : "describes"
    WIKI_REPORT ||--|{ SECTION_REPORT : "aggregates"
    LOADED_SECTION ||--|| SECTION : "pairs body with"

    SECTION ||--o{ SECTION_FINDING : "collects"
    FILE_FINDINGS ||--|{ SECTION_FINDING : "groups"

    SOURCE_REF {
        string file_path
        string line_range
        string fingerprint
    }
    CLAIM }o--|{ SOURCE_REF : "backed by"
    CONTRADICTION }|--|{ CLAIM : "groups conflicting"
    EVIDENCE_BUNDLE ||--|{ CLAIM : "contains"
    EVIDENCE_BUNDLE ||--o{ CONTRADICTION : "contains"

    WALK_REPORT ||--|| INTROSPECTION_RESULT : "carries"
    WALK_REPORT ||--|| EXTRACTION_STATS : "carries"
    WALK_REPORT ||--|| AGGREGATION_STATS : "carries"
    WALK_REPORT ||--|| DERIVATION_STATS : "carries"
    WALK_REPORT ||--|| WALK_CACHE : "carries"
    WALK_REPORT ||--|| REPO_GRAPH : "carries"
    WALK_CACHE ||--o{ CACHED_FINDINGS : "holds"
    WALK_CACHE ||--o{ CACHED_SECTION : "holds"
    REPO_GRAPH ||--|{ GRAPH_NODE : "indexes"

    DERIVATION_STATS ||--o{ REVIEW_OUTCOME : "audit trail"
    REVIEW_OUTCOME ||--|| CRITIQUE : "initial"
    REVIEW_OUTCOME ||--o| CRITIQUE : "follow-up"

    CHAT_SESSION ||--|| LLM_PROVIDER : "uses"
    CHAT_SESSION ||--|{ CHAT_MESSAGE : "history"
```

## Integration Flow

End-to-end pipeline sequence from CLI invocation through all four stages, showing each stage's interactions with the LLM provider abstraction, the cache layer, the import graph, and the filesystem layout.

```mermaid
sequenceDiagram
    autonumber
    participant CLI
    participant Orchestrator
    participant Config
    participant LLMProvider
    participant ImportGraph
    participant SpecDispatch
    participant Cache
    participant FilesystemLayout

    CLI->>Config: load settings and feature flags
    CLI->>Orchestrator: walk command
    Orchestrator->>LLMProvider: Stage 1 — scope classification
    LLMProvider-->>Orchestrator: IntrospectionResult
    Orchestrator->>FilesystemLayout: initialise layout

    loop per in-scope file
        Orchestrator->>ImportGraph: fetch file neighbours
        ImportGraph-->>Orchestrator: neighbour paths
        Orchestrator->>Cache: lookup by content fingerprint
        alt cache hit
            Cache-->>Orchestrator: FileFindings cached
        else cache miss
            Orchestrator->>SpecDispatch: route by FileKind
            alt recognised kind
                SpecDispatch-->>Orchestrator: SpecializedFindings
            else general path
                SpecDispatch->>LLMProvider: Stage 2 — extraction
                LLMProvider-->>SpecDispatch: SectionFindings
                SpecDispatch-->>Orchestrator: FileFindings
            end
            Orchestrator->>Cache: store findings
        end
        Orchestrator->>FilesystemLayout: append notes per section
    end

    loop per primary section
        Orchestrator->>Cache: lookup by notes-payload hash
        alt cache hit
            Cache-->>Orchestrator: rendered section body
        else cache miss
            Orchestrator->>LLMProvider: Stage 3 — aggregation
            LLMProvider-->>Orchestrator: EvidenceBundle
            Orchestrator->>FilesystemLayout: write section markdown
            Orchestrator->>Cache: store aggregated section
        end
    end

    loop per derivative section in topological order
        Orchestrator->>FilesystemLayout: read upstream section bodies
        Orchestrator->>LLMProvider: Stage 4 — derivation
        LLMProvider-->>Orchestrator: section body
        Orchestrator->>FilesystemLayout: write section markdown
        opt quality review enabled
            Orchestrator->>LLMProvider: critique
            LLMProvider-->>Orchestrator: Critique with score
            alt score below revision threshold
                Orchestrator->>LLMProvider: revise
                LLMProvider-->>Orchestrator: revised body
                Orchestrator->>FilesystemLayout: overwrite section markdown
            end
        end
    end

    Orchestrator-->>CLI: WalkReport
    Note over CLI,FilesystemLayout: chat and report subcommands read finished wiki via FilesystemLayout
```
