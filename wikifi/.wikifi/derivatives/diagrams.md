## Diagrams



Derived from finalized primary sections and the complete extraction-note set.



### 10000-Foot Flow

```mermaid
flowchart TD
  User[Knowledge Consumer]
  CLI[Command Interface]
  Introspection[Repository Introspection]
  Extraction[Semantic Extraction]
  Aggregation[Primary Wiki Sections]
  Derivation[Personas, Stories, Diagrams]
  Report[Execution Summary]
  User --> CLI --> Introspection --> Extraction --> Aggregation --> Derivation --> Report
```

### Entity Evidence Map

| Source | Role | Categories |
| --- | --- | --- |
| __main__.py | Main is a production source artifact in the wikified system boundary. | capabilities, domains, inline_schematics, integrations, intent |
| aggregation.py | Aggregation is a production source artifact in the wikified system boundary. | capabilities, cross_cutting, domains, external_dependencies, hard_specifications, inline_schematics, integrations, intent |
| cli.py | Cli is a production source artifact in the wikified system boundary. | capabilities, cross_cutting, domains, inline_schematics, integrations, intent |
| config.py | Config is a production source artifact in the wikified system boundary. | capabilities, cross_cutting, domains, entities, external_dependencies, hard_specifications, inline_schematics, intent |
| constants.py | Constants is a production source artifact in the wikified system boundary. | capabilities, cross_cutting, domains, entities, external_dependencies, hard_specifications, inline_schematics, integrations, intent |
| derivation.py | Derivation is a production source artifact in the wikified system boundary. | capabilities, cross_cutting, domains, hard_specifications, inline_schematics, integrations, intent |
| extraction.py | Extraction is a production source artifact in the wikified system boundary. | capabilities, cross_cutting, domains, external_dependencies, hard_specifications, inline_schematics, intent |
| introspection.py | Introspection is a production source artifact in the wikified system boundary. | capabilities, cross_cutting, domains, hard_specifications, inline_schematics, integrations, intent |
| models.py | Models is a production source artifact in the wikified system boundary. | capabilities, cross_cutting, domains, entities, external_dependencies, hard_specifications, inline_schematics, intent |
| orchestrator.py | Orchestrator is a production source artifact in the wikified system boundary. | capabilities, cross_cutting, domains, entities, external_dependencies, hard_specifications, inline_schematics, integrations, intent |

```mermaid
erDiagram
    WORKSPACE ||--o{ EXTRACTION_NOTE : contains
    EXTRACTION_NOTE }o--o{ DOCUMENTATION_SECTION : informs
    NOTE_0 {
        string source
    }
    NOTE_1 {
        string source
    }
    NOTE_2 {
        string source
    }
    NOTE_3 {
        string source
    }
    NOTE_4 {
        string source
    }
    NOTE_5 {
        string source
    }
    NOTE_6 {
        string source
    }
    NOTE_7 {
        string source
    }
    NOTE_8 {
        string source
    }
    NOTE_9 {
        string source
    }
```

### Integration Sequence

```mermaid
sequenceDiagram
  participant Operator
  participant CLI
  participant Pipeline
  participant Provider
  participant Wiki
  Operator->>CLI: request init or walk
  CLI->>Pipeline: load config and enforce stage order
  Pipeline->>Provider: request extraction or synthesis through provider boundary
  Provider-->>Pipeline: return analysis or trigger fallback gap
  Pipeline->>Wiki: write primary and derivative sections
  Wiki-->>Operator: expose report and documentation artifacts
```

### Gap Declaration

These diagrams are abstract behavior maps and intentionally omit current implementation topology.

Primary context size used for derivation: 20075 characters.

