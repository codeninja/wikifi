## Capabilities

What the system does for its users in domain language.


### Extracted Capabilities

- Invoke the main CLI routine.
- Handle process exit with appropriate status codes.
- Given a repository with mixed source and non-source artifacts, when wikifi walks the repository through the configured source boundary, then it produces domain-focused documentation from included production artifacts.
- Traversal result reports selected file count versus total traversable files.
- Cli exposes behavior for main.
- Environment variable parsing
- local configuration file parsing
- Type coercion (int, bool, tuple)
- Configuration validation
- Error handling for configuration issues
- Identify supported AI providers (currently 'local reasoning service').
- Filter directories and files based on immutable exclusion lists.
- Recognize structural configuration files across multiple ecosystems (source implementation, JS, Rust, Java, Go, etc.).
- Distinguish between production code extensions and test-related paths/patterns.
- Define metadata for primary and derivative documentation sections.
- Load and aggregate primary markdown context
- Render persona descriptions based on capabilities and dependencies
- Generate Gherkin-style user stories from capability evidence
- Produce Mermaid flowcharts, entity maps, and sequence diagrams
- Record aggregation statistics for generated files
- Exposes behavior for extract notes, provider note, heuristic note, heuristic categories, capability findings, entity findings, hard spec findings, fallback role, fallback finding, meaningful terms, human name, evidence, payload string, payload categories.
- Map file extensions to language categories
- Rank languages by file count
- Extract and summarize README content for purpose inference
- Derive purpose from source file names when documentation is absent
- Identify and report missing structural elements (gaps)
- Workspace layout generation and normalization
- File content ingestion with size limits and truncation handling
- Directory summarization with extension distribution and manifest detection
- Introspection assessment of repository purpose and languages
- Extraction note creation with categorized findings and evidence
- Aggregation statistics tracking for section writes and gaps
- Pipeline result compilation with stage metrics and status reporting
- Initialize and validate workspace layout
- Load and validate configuration settings
- Discover and filter source files based on settings
- Assess repository structure and content
- Extract notes using a configurable provider with fallback support
- Aggregate content into sections
- Derive additional content sections
- Collect and report stage-level performance metrics
- Maintain execution logs and summaries
- Reset intermediate state between runs
- Generate plain text responses from LLM
- Generate structured structured data responses from LLM
- Configure LLM parameters (model, temperature, think mode)
- Handle network interface network client and responses for provider API
- Validate structured data schema compliance in responses
- Factory instantiation of providers based on settings
- Write extraction notes as structured data lines to a specified file path
- Generate and write a structured data summary of pipeline execution
- Generate and write a Markdown summary with metrics, stage status, skipped counts, and readiness statements
- Append log messages to a file
- Normalize whitespace in strings
- Summarize text with configurable length limits
- Generate bullet lists with deduplication
- Create markdown-formatted tables
- Deduplicate string collections
- Translate technical terms to domain language
- Extract first sentence from text
- Clean table cell content
- Recursive directory traversal
- Pattern-based file exclusion
- Binary content detection
- File size enforcement and truncation
- Content digest computation
- Metadata aggregation (file counts, sizes, extensions)
- Create directory structure for wiki, notes, sections, derivatives, and reports
- Generate default configuration file with provider and model settings
- Generate .gitignore file to exclude intermediate data
- Create placeholder files for primary and derivative sections
- Reset notes directory and clear run log
- Generate README explaining workspace contents

### Behavioral Contract

| Clause | Statement |
| --- | --- |
| Given | A repository with mixed source and non-source artifacts. |
| When | wikifi walks the repository through the configured source boundary. |
| Then | It produces domain-focused documentation from included production artifacts. |

### Traversal Result

15 source files were selected from 16 traversable files.

