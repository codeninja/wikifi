## Core Entities

Domain entities, important structures, and relationships.


### Entity and Structure Findings

- Config defines structured concepts: ConfigError.
- Constants defines structured concepts: SectionDefinition.
- Models defines structured concepts: WorkspaceLayout, Settings, SourceFile, SkippedFile, DirectorySummary, IntrospectionAssessment, ExtractionNote, AggregationStats, PipelineResult.
- Orchestrator defines structured concepts: PipelineError.
- Providers defines structured concepts: ProviderError, UnsupportedProviderError, LLMProvider, OllamaProvider.

### Source-to-Concept Trace

| Source | Role | Evidence Categories |
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
| providers.py | Providers is a production source artifact in the wikified system boundary. | capabilities, cross_cutting, domains, entities, external_dependencies, hard_specifications, inline_schematics, intent |
| reporting.py | Reporting is a production source artifact in the wikified system boundary. | capabilities, cross_cutting, domains, external_dependencies, inline_schematics, integrations, intent |
| text.py | Text is a production source artifact in the wikified system boundary. | capabilities, cross_cutting, domains, external_dependencies, hard_specifications, inline_schematics, integrations, intent |
| traversal.py | Traversal is a production source artifact in the wikified system boundary. | capabilities, cross_cutting, domains, inline_schematics, intent |
| workspace.py | Workspace is a production source artifact in the wikified system boundary. | capabilities, cross_cutting, domains, external_dependencies, hard_specifications, inline_schematics, integrations, intent |

