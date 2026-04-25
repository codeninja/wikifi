## Hard Specifications

Critical behavior and requirements that must carry forward.


### Carry-Forward Requirements

- Must raise SystemExit with the return value of main().
- Gap from __main__.py: The specific functionality of the wikifi.cli.main function is not defined in this file.
- Gap from __main__.py: Configuration handling, argument parsing, and command routing are not visible here.
- Gap from __main__.py: Error handling strategies within the main function are not exposed.
- Files larger than the configured byte threshold are truncated to the configured limit before extraction.
- Unreadable, malformed, binary, or below-minimum-content files are skipped, counted, and the pipeline continues.
- Unsupported providers cause the run to fail gracefully with a clear message.
- Contradiction resolution between source files is reported but not automatically adjudicated beyond preserving evidence.
- Gap from aggregation.py: Authentication, rate limiting, and provider-side quota behavior are not inferable unless source evidence states them.
- Gap from aggregation.py: Contradiction resolution between source files is reported but not automatically adjudicated beyond preserving evidence.
- Gap from aggregation.py: Diagrams represent aggregate source relationships and must not be treated as implementation architecture.
- Gap from aggregation.py: No concrete third-party or infrastructure dependencies were detected inside the production source boundary.
- Gap from aggregation.py: No integration touchpoints were explicit in the selected source.
- Gap from aggregation.py: No additional cross-cutting findings were extracted.
- Gap from aggregation.py: No entity structures were extracted from selected source files.
- Gap from aggregation.py: No hard specifications were extracted from selected source files.
- Gap from aggregation.py: No source-level domain findings were extracted.
- Gap from aggregation.py: No capability findings were extracted from the selected source.
- Gap from aggregation.py: The allowed source did not explicitly state a deeper problem-space narrative.
- request_timeout must be greater than zero
- max_file_bytes must be greater than zero
- min_content_bytes must not be negative
- introspection_depth must be at least one
- output_dir must not be empty
- Local config must contain a [wikifi] table or top-level keys
- Environment variable names are prefixed with WIKIFI_
- Gap from config.py: The specific structure and fields of the Settings model are not defined in this file
- Gap from config.py: The default values for configuration fields are not explicitly defined in this file
- Gap from config.py: The exact behavior of the 'provider' and 'model' fields is not specified
- Gap from config.py: The purpose of 'introspection_depth' and 'think' fields is not clear from this file alone
- Exclusion lists are immutable (frozenset/tuple).
- SectionDefinition is frozen.
- Processing must follow the order: introspection, extraction, aggregation, derivation.
- Gap from constants.py: The specific logic for how these constants are consumed by the main, aggregation, cli, or config modules is not present in this file.
- Gap from constants.py: The mechanism for interacting with the 'ollama' provider is not defined here.
- Gap from constants.py: The exact criteria for 'derivative' sections and how they are generated from primary sections are not specified.
- Gap from constants.py: The file does not define how the filtering logic handles edge cases or overrides.
- Derivative sections are defined by DERIVATIVE_SECTIONS constant
- Personas section includes specific roles: Onboarding Engineering Practitioner, Technical Writer and System Architect, Portfolio Manager and Acquisition Integrator
- User stories are limited to top 4 capabilities or a default fallback
- Diagrams include a 10000-Foot Flow, Entity Evidence Map, and Integration Sequence
- Entity map limits to first 10 notes
- Output encoding is utf-8
- Gap from derivation.py: Role-based authorization, access controls, and persona-specific processing presets are not defined by source evidence.
- Gap from derivation.py: Contradictory feature evidence is not auto-resolved; consumers must review source-linked notes when conflict is reported.
- Gap from derivation.py: Diagrams are abstract behavior maps and intentionally omit current implementation topology.
- Gap from derivation.py: No derivative renderer was configured for sections other than personas, user_stories, and diagrams.
- Contains explicit guardrail language around fallback, required, and unsupported.
- Exceeded the configured file-size boundary and was truncated before analysis.
- Gap from extraction.py: AI provider output was unavailable, so this note preserves deterministic local evidence instead of fabricating unstated intent.
- Gap from extraction.py: The exact business role of some source artifacts may not be explicit and relies on heuristic term extraction.
- Gap from extraction.py: AST parsing may fail for syntactically invalid source files, limiting structural analysis capabilities.
- Primary languages are limited to top 3 by count
- README content is limited to first sentence of summarized text (max 220 chars)
- Purpose inference from file names uses first 8 source files and top 5 stems
- Gaps are reported when no production source files or manifest files are present
- Gap from introspection.py: No production source files met the traversal thresholds.
- Gap from introspection.py: No notable manifest or documentation files were present for structural routing.
- Max file size: 200,000 bytes
- Min content size: 64 bytes
- Default request timeout: 900 seconds
- Default introspection depth: 3
- Default output directory: .wikifi
- Default provider: local reasoning service
- Default model: qwen3.6:27b
- Gap from models.py: Specific AI provider implementation details are abstracted behind the provider string
- Gap from models.py: Exact logic for file skipping reasons is not defined in models
- Gap from models.py: Category keys for extraction notes are dynamic and not enumerated
- Gap from models.py: Stage metrics structure is generic (dict[str, Any]) without specific keys defined
- Gap from models.py: Provider status values are not enumerated
- Pipeline stages must execute in order defined by STAGE_ORDER
- Workspace must be initialized before pipeline execution
- Intermediate state must be reset before each run
- Metrics must be collected for each stage including duration and counts
- Exit code 2 for UnsupportedProviderError and ConfigError
- Exit code 1 for PipelineError and other exceptions
- Root path must exist and be a directory
- Provider fallback is configurable via settings
- Gap from orchestrator.py: Specific implementation details of each stage (introspection, extraction, aggregation, derivation) are not visible in this file
- Gap from orchestrator.py: Configuration schema and available settings options are not defined here
- Gap from orchestrator.py: Provider interface and supported provider types are not specified
- Gap from orchestrator.py: Workspace layout structure and directory conventions are not detailed
- Gap from orchestrator.py: Note format and structure are not defined
- Gap from orchestrator.py: Aggregation and derivation algorithms are not visible
- Gap from orchestrator.py: Logging format and summary structure are not specified
- Gap from orchestrator.py: Error recovery mechanisms beyond exit codes are not described
- Temperature is hardcoded to 0 for all network client
- Streaming is disabled (stream: False)
- structured data responses must be valid structured data objects (dicts)
- Provider ID for local reasoning service is 'local reasoning service'
- Request timeout is derived from settings.request_timeout
- Think mode value is normalized to boolean or string 'high'
- Notes are written as structured data lines with sorted keys
- Summary structured data is written with 2-space indentation and sorted keys
- Markdown summary includes specific sections: Execution Summary, Pipeline Health, Stage Metrics, Skipped Input Counts, Output Readiness
- Readiness statement warns if any primary or derivative sections are empty
- Gap from reporting.py: The exact structure of ExtractionNote and AggregationStats is not defined in this file
- Gap from reporting.py: The implementation of PipelineResult.as_summary() is not visible
- Gap from reporting.py: The specific paths within WorkspaceLayout for notes, summary JSON, and summary Markdown are not detailed here
- Gap from reporting.py: The behavior of markdown_table utility is not specified beyond its usage
- Summarization limit defaults to 500 characters
- Truncation appends '...' when text exceeds limit
- Deduplication is case-insensitive
- Bullet list fallback is used when no unique items exist
- Table cells escape pipe characters
- Gap from text.py: No explicit error handling for invalid inputs
- Gap from text.py: No documentation for function parameters and return types beyond type hints
- Gap from text.py: No test cases or verification logic included
- Gap from text.py: No configuration mechanism for IMPLEMENTATION_WORDS mapping
- Gap from text.py: No support for internationalization or locale-specific text processing
- Files are excluded if they match IMMUTABLE_EXCLUDED_DIRS or start with '.' (except '.well-known')
- Files are excluded if they match IMMUTABLE_EXCLUDED_FILE_PATTERNS or settings.exclude_patterns
- Files are excluded if they contain TEST_PATH_PARTS in their path or match TEST_FILE_PATTERNS
- Files are excluded if they are in STRUCTURAL_FILENAMES
- Files are included only if their extension is in PRODUCTION_EXTENSIONS
- Binary files are detected by presence of null bytes in first 2048 bytes
- Files are truncated if they exceed settings.max_file_bytes
- Files are skipped if content length is less than settings.min_content_bytes
- Content digest is computed using SHA-256
- Gap from traversal.py: The specific values of IMMUTABLE_EXCLUDED_DIRS, IMMUTABLE_EXCLUDED_FILE_PATTERNS, PRODUCTION_EXTENSIONS, STRUCTURAL_FILENAMES, TEST_FILE_PATTERNS, and TEST_PATH_PARTS are not defined in this file
- Gap from traversal.py: The structure of Settings, DirectorySummary, SourceFile, and SkippedFile models is not defined in this file
- Gap from traversal.py: The behavior of settings.max_file_bytes and settings.min_content_bytes is not specified in this file
- Gap from traversal.py: The handling of symbolic links is not explicitly addressed
- Gap from traversal.py: The performance implications of large directory trees are not discussed
- Default configuration includes provider 'local reasoning service', model 'qwen3.6:27b', host 'network interface://localhost:11434', timeout 900, max_file_bytes 200000, min_content_bytes 64, introspection_depth 3, think 'high', allow_provider_fallback true, exclude_patterns empty
- Gitignore excludes /notes/, /tmp/, /run.log
- README explains sections/, derivatives/, reports/, and notes/ directories
- Gap from workspace.py: The specific content and structure of PRIMARY_SECTIONS and DERIVATIVE_SECTIONS are not defined in this file
- Gap from workspace.py: The exact schema of the Settings model is not provided
- Gap from workspace.py: The WorkspaceLayout model structure and methods are not detailed
- Gap from workspace.py: The purpose and content of the run.log file are not specified beyond being cleared
- Gap from workspace.py: The mechanism for populating primary and derivative sections is not described
- Gap from workspace.py: The relationship between the workspace structure and the main aggregation/cli/config components is not explicit

### Behavioral Specifications

| Clause | Statement |
| --- | --- |
| Given | A file is larger than the configured byte threshold. |
| When | The traversal stage reads it. |
| Then | The content is truncated to the configured limit before extraction. |
| Given | A file is unreadable, malformed, binary, or below the minimum content threshold. |
| When | The traversal stage encounters it. |
| Then | The file is skipped, counted, and the pipeline continues. |
| Given | A provider other than the supported local provider is configured. |
| When | The command validates runtime settings. |
| Then | The run fails gracefully with a clear unsupported-provider message. |

### Gap Declaration

Contradiction resolution between source files is reported but not automatically adjudicated beyond preserving evidence.

