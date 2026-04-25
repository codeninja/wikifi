## Integrations

Internal and external touchpoints and handoffs.


### Touchpoints

- Given a user invokes the command interface, when the orchestrator receives the request, then it delegates work through introspection, extraction, aggregation, and derivation in sequence.
- Cli coordinates handoffs between user commands and internal processing stages.
- Environment variables (WIKIFI_*)
- Local local configuration configuration file (config.local configuration)
- Writes to layout.derivatives_dir
- Consumes layout.sections_dir for primary context
- Uses assessment.inferred_purpose for narrative context
- Coordinates handoffs between user commands and internal processing stages through the extraction pipeline and provider orchestration.
- Consumes DirectorySummary and SourceFile tuples from upstream traversal logic
- Produces IntrospectionAssessment for downstream consumption
- Configuration file (config.local configuration) for settings persistence
- JSONL format for extraction notes storage
- Markdown and structured data for summary reports
- Provider system for note extraction with fallback mechanism
- Workspace layout management for consistent directory structure
- Configuration system for pipeline settings
- Logging system for execution tracking
- Metrics collection for performance monitoring
- local reasoning service local/remote instance via network interface POST to /api/generate
- Consumes PipelineResult and WorkspaceLayout to determine output paths and content
- Uses markdown_table utility to format tabular data in Markdown summaries
- Consumes Settings configuration for exclusion patterns and size limits
- Produces DirectorySummary, SourceFile, and SkippedFile entities for downstream processing
- File system operations for directory and file creation
- Configuration management for provider and model settings

### Behavioral Handoff

| Clause | Statement |
| --- | --- |
| Given | A user invokes the command interface. |
| When | The orchestrator receives the request. |
| Then | It delegates work through introspection, extraction, aggregation, and derivation in sequence. |

