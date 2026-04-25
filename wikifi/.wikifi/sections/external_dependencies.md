## External-System Dependencies

Third-party services, infrastructure, and standards the system depends on.


### Dependency Roles

- wikifi.cli module
- No concrete third-party or infrastructure dependencies were detected inside the production source boundary.
- Authentication, rate limiting, and provider-side quota behavior are not inferable unless source evidence states them.
- wikifi.models.Settings
- tomllib
- os
- pathlib
- dataclasses
- AI Provider: 'local reasoning service' (indicated by SUPPORTED_PROVIDERS).
- wikifi.constants.DERIVATIVE_SECTIONS
- wikifi.models (AggregationStats, ExtractionNote, IntrospectionAssessment, WorkspaceLayout)
- wikifi.text (bullet_list, dedupe, markdown_table)
- References external or host-provided services through an abstract boundary via the LLMProvider interface.
- wikifi.models (DirectorySummary, IntrospectionAssessment, SourceFile)
- wikifi.text (dedupe, first_sentence, summarize_text)
- AI Provider (e.g., local reasoning service) for introspection and extraction
- File System for workspace operations
- wikifi.aggregation
- wikifi.config
- wikifi.constants
- wikifi.derivation
- wikifi.extraction
- wikifi.introspection
- wikifi.models
- wikifi.providers
- wikifi.reporting
- wikifi.traversal
- wikifi.workspace
- local reasoning service API (network interface endpoint)
- wikifi.constants.SUPPORTED_PROVIDERS
- wikifi.models (AggregationStats, ExtractionNote, PipelineResult, WorkspaceLayout)
- wikifi.text (markdown_table)
- re (regular expressions)
- collections.abc.Iterable
- wikifi.constants (IMMUTABLE_EXCLUDED_DIRS, IMMUTABLE_EXCLUDED_FILE_PATTERNS, PRODUCTION_EXTENSIONS, STRUCTURAL_FILENAMES, TEST_FILE_PATTERNS, TEST_PATH_PARTS)
- wikifi.models (DirectorySummary, Settings, SkippedFile, SourceFile)
- wikifi.constants (DERIVATIVE_SECTIONS, PRIMARY_SECTIONS)
- wikifi.models (Settings, WorkspaceLayout)

### Gap Declaration

Authentication, rate limiting, and provider-side quota behavior are not inferable unless source evidence states them.

