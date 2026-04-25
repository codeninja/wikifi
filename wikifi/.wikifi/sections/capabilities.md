## Capabilities

What the system does for its users in domain language.


### Extracted Capabilities

- Main defines internal behavior without public source-level entry points.
- Aggregation exposes behavior for aggregate sections, node id.
- Cli exposes behavior for main.
- Config exposes behavior for ConfigError, load settings.
- Constants exposes behavior for SectionDefinition.
- Derivation exposes behavior for derive sections.
- Extraction exposes behavior for extract notes.
- Introspection exposes behavior for assess repository.
- Models exposes behavior for utc now, normalize path, WorkspaceLayout, Settings, SourceFile, SkippedFile, DirectorySummary, IntrospectionAssessment.
- Orchestrator exposes behavior for PipelineError, init workspace, walk, explain error.
- Providers exposes behavior for ProviderError, UnsupportedProviderError, LLMProvider, OllamaProvider, build provider, generate text, generate json.
- Reporting exposes behavior for write notes, write summary, append log.
- Text exposes behavior for normalize space, summarize text, bullet list, markdown table, dedupe, domain language, first sentence.
- Traversal exposes behavior for discover source files.
- Workspace exposes behavior for ensure workspace, reset intermediate, write workspace readme.

### Behavioral Contract

| Clause | Statement |
| --- | --- |
| Given | A repository with mixed source and non-source artifacts. |
| When | wikifi walks the repository through the configured source boundary. |
| Then | It produces domain-focused documentation from included production artifacts. |

### Traversal Result

15 source files were selected from 16 traversable files.

