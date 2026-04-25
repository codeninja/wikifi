## Core Entities

Domain entities, important structures, and relationships.


### Entity and Structure Findings

- Source-to-concept trace maps file references to roles and evidence categories.
- Entity structures are extracted from selected source files.
- Settings
- ConfigError
- SectionDefinition: A frozen structured record representing a documentation section with key, filename, title, purpose, and derivative flag.
- SUPPORTED_PROVIDERS: A set of supported AI backends.
- IMMUTABLE_EXCLUDED_DIRS: A frozenset of directories to ignore.
- IMMUTABLE_EXCLUDED_FILE_PATTERNS: A tuple of file patterns to ignore.
- STRUCTURAL_FILENAMES: A frozenset of important configuration/readme files.
- PRODUCTION_EXTENSIONS: A frozenset of source code file extensions.
- TEST_PATH_PARTS: A frozenset of directory names indicating tests.
- TEST_FILE_PATTERNS: A tuple of filename patterns indicating tests.
- PRIMARY_SECTIONS: A tuple of SectionDefinition instances for core documentation.
- DERIVATIVE_SECTIONS: A tuple of SectionDefinition instances for generated documentation.
- STAGE_ORDER: A tuple defining the processing pipeline stages.
- WorkspaceLayout
- IntrospectionAssessment
- ExtractionNote
- AggregationStats
- DERIVATIVE_SECTIONS
- Defines structured concepts: Extraction Note, Introspection Assessment, Source File, LLM Provider, Provider Error, Primary Sections.
- DirectorySummary
- SourceFile
- LANGUAGE_BY_EXTENSION mapping
- SkippedFile
- PipelineResult
- PipelineError
- UnsupportedProviderError
- Layout
- Provider
- Notes
- Assessment
- StageMetrics
- DerivativeStats
- LLMProvider (Abstract Base Class)
- OllamaProvider (Concrete Implementation)
- Settings (Configuration structured record)
- ProviderError (Exception)
- UnsupportedProviderError (Exception)
- IMPLEMENTATION_WORDS (mapping of technical terms to domain descriptions)
- Text values
- String collections
- Table headers and rows
- Config file
- Gitignore file
- Primary sections
- Derivative sections
- Notes directory
- Reports directory
- Run log

### Source-to-Concept Trace

| Source | Role | Evidence Categories |
| --- | --- | --- |
| __main__.py | Entry point for the Wikifi CLI application, responsible for invoking the main CLI function and handling process termination. | capabilities, cross_cutting, domains, external_dependencies, hard_specifications, intent |
| aggregation.py | Aggregation module that synthesizes extracted domain knowledge into structured wiki sections, preserving traceability and explicitly declaring gaps. | capabilities, cross_cutting, domains, entities, external_dependencies, hard_specifications, inline_schematics, integrations, intent |
| cli.py | Cli is a production source artifact in the wikified system boundary. | capabilities, cross_cutting, domains, inline_schematics, integrations, intent |
| config.py | Configuration loader and validator for a system named 'wikifi', managing settings via environment variables and local local configuration files. | capabilities, cross_cutting, domains, entities, external_dependencies, hard_specifications, inline_schematics, integrations, intent |
| constants.py | Defines static configuration constants and structural metadata for a system that processes code repositories to extract and aggregate domain knowledge. | capabilities, cross_cutting, domains, entities, external_dependencies, hard_specifications, intent |
| derivation.py | Derives secondary documentation artifacts (personas, user stories, diagrams) from primary wiki content and extraction notes, writing them to a derivatives directory and returning aggregation statistics. | capabilities, cross_cutting, domains, entities, external_dependencies, hard_specifications, inline_schematics, integrations, intent |
| extraction.py | Extraction orchestrator that converts source files into structured, technology-agnostic domain knowledge notes, with deterministic fallbacks when the AI provider is unavailable. | capabilities, cross_cutting, domains, entities, external_dependencies, hard_specifications, inline_schematics, integrations, intent |
| introspection.py | The system performs static analysis of a repository to infer its primary programming languages, purpose, and structural characteristics without parsing source code content. It relies on file extensions, directory structure, and documentation files to generate an assessment. | capabilities, cross_cutting, domains, entities, external_dependencies, hard_specifications, inline_schematics, integrations, intent |
| models.py | Defines the core data structures and configuration models for a file analysis and knowledge extraction pipeline. | capabilities, cross_cutting, domains, entities, external_dependencies, hard_specifications, inline_schematics, integrations, intent |
| orchestrator.py | Orchestrates a multi-stage content processing pipeline that discovers source files, extracts notes, aggregates sections, and derives additional content, while managing workspace setup, configuration, and execution metrics. | capabilities, cross_cutting, domains, entities, external_dependencies, hard_specifications, inline_schematics, integrations, intent |
| providers.py | The file defines an abstraction for interacting with Large Language Model (LLM) providers, specifically implementing a concrete provider for local reasoning service. It establishes a contract for text and structured data generation, handles network interface communication with the provider's API, and includes a factory function to instantiate providers based on configuration. | capabilities, cross_cutting, domains, entities, external_dependencies, hard_specifications, inline_schematics, integrations, intent |
| reporting.py | Reporting module responsible for generating and writing execution summaries, extraction notes, and log entries in structured formats (structured data, Markdown) after pipeline stages complete. | capabilities, cross_cutting, domains, entities, external_dependencies, hard_specifications, inline_schematics, integrations, intent |
| text.py | Text processing and formatting utility module providing functions for normalization, summarization, list/table generation, deduplication, and domain language translation. | capabilities, cross_cutting, domains, entities, external_dependencies, hard_specifications, inline_schematics, intent |
| traversal.py | The system performs file discovery and filtering within a directory tree to identify production source files while excluding tests, binaries, and structural artifacts. It aggregates metadata about the directory structure and file distribution. | capabilities, cross_cutting, domains, entities, external_dependencies, hard_specifications, inline_schematics, integrations, intent |
| workspace.py | The system manages a structured workspace for generating and organizing technology-agnostic documentation. It initializes directories, configuration files, and placeholder files for primary and derivative content sections, while also providing mechanisms to reset intermediate data and generate a workspace README. | capabilities, cross_cutting, domains, entities, external_dependencies, hard_specifications, inline_schematics, integrations, intent |

