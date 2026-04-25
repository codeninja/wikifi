## Inline Schematics

Mermaid visualizations that clarify domains, entities, and integrations.


### Stage-Gated Knowledge Flow

```mermaid
graph TD
  Introspection[Repository Introspection]
  Extraction[Semantic Extraction]
  Aggregation[Section Aggregation]
  Derivation[Derivative Capture]
  Introspection --> Extraction
  Extraction --> S0[  Main  ]
  Extraction --> S1[Aggregation]
  Extraction --> S2[Cli]
  Extraction --> S3[Config]
  Extraction --> S4[Constants]
  Extraction --> S5[Derivation]
  Extraction --> S6[Extraction]
  Extraction --> S7[Introspection]
  Extraction --> Aggregation
  Aggregation --> Derivation
```

### Gap Declaration

Diagrams represent aggregate source relationships and must not be treated as implementation architecture.

