# Diagrams

The three diagrams below cover the subdomain structure of the core domain, the structural relationships between the principal entities, and the end-to-end pipeline integration flow.

---

## Domain Map

The four subdomains that compose the core domain of automated documentation synthesis form a strict directed dependency chain. No subdomain reaches backward; the ordering is a first-class design constraint.

```mermaid
graph LR
    RI["Repository Introspection"]
    KE["Knowledge Extraction"]
    SS_P["Section Synthesis - Primary"]
    SS_D["Section Synthesis - Derivative"]
    AP_W[("Working-State Persistence")]
    AP_C[("Committed Wiki Persistence")]

    RI --> KE
    KE --> AP_W
    KE --> SS_P
    SS_P --> SS_D
    SS_P --> AP_C
    SS_D --> AP_C
```

---

## Entity Relationship View

The diagram spans six concern areas: wiki structure, evidence tracing, extraction, pipeline orchestration, caching, and quality review. The self-referential edge on **Section** represents the directed acyclic graph of upstream declarations enforced by topological ordering at startup.

```mermaid
erDiagram
    SECTION ||--o{ SECTION : "upstream-of"
    SECTION ||--o{ LOADED_SECTION : "has loaded form"
    SECTION ||--o{ SECTION_REPORT : "reported by"
    WIKI_REPORT ||--o{ SECTION_REPORT : aggregates
    EVIDENCE_BUNDLE ||--o{ CLAIM : contains
    EVIDENCE_BUNDLE ||--o{ CONTRADICTION : contains
    CLAIM ||--o{ SOURCE_REF : "backed by"
    CONTRADICTION ||--|{ CLAIM : groups
    FILE_FINDINGS ||--|{ SECTION_FINDING : groups
    WALK_REPORT ||--|| INTROSPECTION_RESULT : carries
    WALK_REPORT ||--|| WALK_CACHE : carries
    WALK_REPORT ||--|| REPO_GRAPH : carries
    REPO_GRAPH ||--o{ GRAPH_NODE : contains
    WALK_CACHE ||--o{ CACHED_FINDINGS : stores
    WALK_CACHE ||--o{ CACHED_SECTION : stores
    WIKI_QUALITY_REPORT ||--o{ CRITIQUE : maps
    REVIEW_OUTCOME ||--|{ CRITIQUE : tracks
    CHAT_SESSION ||--o{ CHAT_MESSAGE : history
    CHAT_SESSION ||--|| LLM_PROVIDER : uses
```

---

## Pipeline Integration Flow

The sequence below traces a complete pipeline run triggered by the `walk` command. The provider abstraction is the sole contact point for all inference calls; the filesystem layout abstraction mediates all reads and writes; the cache layer short-circuits calls when prior results remain valid. Derivative sections are excluded from the aggregation stage and are handled exclusively in the derivation stage.

```mermaid
sequenceDiagram
    actor Operator
    participant CLI
    participant Orchestrator
    participant LLMProvider as LLM Provider
    participant ImportGraph as Import Graph
    participant Cache
    participant Layout as Filesystem Layout

    Operator->>CLI: walk command
    CLI->>Orchestrator: initialise pipeline

    Note over Orchestrator,LLMProvider: Stage 1 - Repository Introspection
    Orchestrator->>LLMProvider: structured completion (classify repository paths)
    LLMProvider-->>Orchestrator: IntrospectionResult

    Note over Orchestrator,ImportGraph: Build Cross-File Import Graph
    Orchestrator->>ImportGraph: traverse in-scope files
    ImportGraph-->>Orchestrator: RepoGraph ready

    Note over Orchestrator,Layout: Stage 2 - Knowledge Extraction (per file)
    loop each in-scope file
        Orchestrator->>Cache: check content fingerprint
        Cache-->>Orchestrator: hit or miss
        Orchestrator->>ImportGraph: fetch neighbour paths
        Orchestrator->>LLMProvider: structured completion (findings schema)
        LLMProvider-->>Orchestrator: FileFindings
        Orchestrator->>Layout: append notes
    end

    Note over Orchestrator,Layout: Stage 3 - Section Aggregation (primary sections only)
    loop each primary section
        Orchestrator->>Cache: check notes-payload hash
        Cache-->>Orchestrator: hit or miss
        Orchestrator->>LLMProvider: structured completion (section-body schema)
        LLMProvider-->>Orchestrator: EvidenceBundle
        Orchestrator->>Layout: write section markdown
    end

    Note over Orchestrator,Layout: Stage 4 - Section Derivation (topological order)
    loop each derivative section
        Orchestrator->>Layout: read upstream section bodies
        Orchestrator->>LLMProvider: structured completion (synthesis)
        LLMProvider-->>Orchestrator: section body
        Orchestrator->>LLMProvider: structured completion (quality critique)
        LLMProvider-->>Orchestrator: Critique
        Orchestrator->>Layout: write section markdown
    end

    Orchestrator-->>CLI: WalkReport
    CLI-->>Operator: run summary
```

> **External capability providers**: The system is additionally configured as a client that fans out to multiple external capability providers via a tool-server protocol — a local AI utility, a local web crawler, a remote documentation context service, and a remote stitching/search service. The upstream sections do not specify at which pipeline call sites these providers are invoked.
