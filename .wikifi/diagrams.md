# Diagrams

## Domain Map

The four subdomains, their classification types, and the direction of data and storage dependencies. Solid arrows carry artifacts; dashed arrows indicate storage-contract or orchestration dependencies. The orchestration seam does not own domain logic — it wires the subdomains together end-to-end.

```mermaid
graph LR
    ORC["Orchestration Seam"]

    subgraph CA["Codebase Analysis"]
        RA["Repository Analysis (Supporting)"]
        EX["Extraction (Supporting)"]
    end

    subgraph KM["Knowledge Management"]
        ES["Evidence Synthesis (Core)"]
        WM["Wiki Management (Generic)"]
    end

    RA -->|file-inventory| EX
    EX -->|classified-findings| ES
    ES -->|section-narratives| WM
    WM -.->|storage| EX
    WM -.->|storage| ES
    ORC -.->|wires| RA
    ORC -.->|wires| EX
    ORC -.->|wires| ES
    ORC -.->|wires| WM
```

---

## Entity Relationship View

Key entities across the extraction, aggregation, derivation, caching, and review subsystems. Only structurally significant relationships are shown; fields are representative rather than exhaustive.

```mermaid
erDiagram
    Section {
        string id
        string tier
        array upstream_ids
    }
    SectionFinding {
        string section_id
        string description
    }
    FileFindings {
        string file_path
        string role_summary
    }
    SourceRef {
        string file_path
        string fingerprint
    }
    Claim {
        string markdown_text
    }
    Contradiction {
        string summary
    }
    EvidenceBundle {
        string narrative_body
    }
    WalkCache {
        int hits
        int misses
    }
    CachedFindings {
        string fingerprint
        int chunk_count
    }
    CachedSection {
        string notes_hash
        string markdown_body
    }
    CachedDerivation {
        string upstream_hash
        bool review_applied
    }
    CachedIntrospection {
        string scope_hash
    }
    Critique {
        int quality_score
        string summary
    }
    ReviewOutcome {
        string section_id
        bool revision_occurred
    }
    RepoGraph {
        string root
    }
    GraphNode {
        string file_path
    }

    Section ||--o{ SectionFinding : "receives"
    FileFindings ||--o{ SectionFinding : "groups"
    Claim }o--o{ SourceRef : "cites"
    EvidenceBundle ||--o{ Claim : "contains"
    EvidenceBundle ||--o{ Contradiction : "surfaces"
    Contradiction ||--o{ Claim : "positions"
    WalkCache ||--o{ CachedFindings : "holds"
    WalkCache ||--o{ CachedSection : "holds"
    WalkCache ||--o{ CachedDerivation : "holds"
    WalkCache ||--o{ CachedIntrospection : "holds"
    ReviewOutcome ||--|{ Critique : "records"
    RepoGraph ||--o{ GraphNode : "aggregates"
```

---

## Integration Flow

A full pipeline run from command invocation to quality reporting. The AI provider is shown as a single abstract surface; the three concrete backends are not distinguished here. The wiki layout acts as the internal artifact bus linking extraction, aggregation, and derivation stages, and the walk cache provides a parallel fingerprint-keyed channel.

```mermaid
sequenceDiagram
    actor Human
    participant CLI
    participant Orchestrator
    participant FilesystemLayer
    participant Dispatcher
    participant AIProvider
    participant WikiLayout
    participant WalkCache
    participant Critic

    Human->>CLI: initiate command
    CLI->>Orchestrator: execute pipeline (settings, provider, layout)

    Orchestrator->>FilesystemLayer: enumerate repository
    FilesystemLayer-->>Orchestrator: file list + structural summary

    Orchestrator->>AIProvider: introspect repository
    AIProvider-->>Orchestrator: IntrospectionResult

    loop Per source file
        Orchestrator->>Dispatcher: classify and route by file kind
        alt Recognized contract or schema artifact
            Dispatcher-->>Orchestrator: parsed findings (specialized extractor)
        else General source file
            Dispatcher->>AIProvider: extract findings
            AIProvider-->>Dispatcher: SectionFindings
            Dispatcher-->>Orchestrator: SectionFindings
        end
        Orchestrator->>WikiLayout: append_note
        Orchestrator->>WalkCache: store fingerprint-keyed result
    end

    loop Per primary section
        Orchestrator->>WikiLayout: read_notes
        WikiLayout-->>Orchestrator: section evidence
        Orchestrator->>AIProvider: aggregate into narrative
        AIProvider-->>Orchestrator: SectionBody and EvidenceBundle
        Orchestrator->>WikiLayout: write_section
    end

    loop Per derivative section
        Orchestrator->>WikiLayout: read upstream section bodies
        WikiLayout-->>Orchestrator: upstream markdown
        Orchestrator->>AIProvider: synthesize derivative body
        AIProvider-->>Orchestrator: rendered body
        opt Review loop enabled
            Orchestrator->>Critic: critique and revise
            Critic->>AIProvider: structured evaluation and revision
            AIProvider-->>Critic: ReviewOutcome
            Critic-->>Orchestrator: revised body
        end
        Orchestrator->>WikiLayout: write_section
    end

    CLI->>Critic: generate quality report
    Critic->>WalkCache: read file coverage
    Critic->>AIProvider: evaluate section quality
    AIProvider-->>CLI: WikiQualityReport
```
