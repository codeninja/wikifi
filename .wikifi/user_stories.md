# User Stories

## Feature: Repository Triage and Scoping

### As a Documentation Engineer, I want the system to classify which paths contain production source before any deep analysis begins, so that analysis effort is focused on meaningful content and costs are bounded.

```gherkin
Given a repository containing production source alongside vendored dependencies, build artifacts, generated files, and CI configuration
And file-size bounds are configured in the pipeline settings
When Stage 1 triage runs
Then paths classified as vendored dependencies, build artifacts, generated files, or CI configuration are excluded from analysis
And files outside the configured size bounds are filtered before any extraction begins
And the rationale for every filtering choice is recorded in the IntrospectionResult
```

---

## Feature: Per-File Extraction

### As a Documentation Engineer, I want well-structured files to be routed to deterministic extractors rather than AI inference, so that extraction is more accurate and cost-effective for those artifact types.

```gherkin
Given a repository containing relational schema files, API contract files, interface definitions, and migration scripts alongside general source files
When the extraction stage begins
Then well-structured files are routed to dedicated deterministic extractors
And general-purpose source files are analyzed via AI inference
And every finding carries a citation recording the repo-relative file path and line range
```

### As a Documentation Engineer, I want large source files to be split into overlapping chunks during extraction, so that no content is lost at chunk boundaries.

```gherkin
Given a source file whose size exceeds the configured chunk threshold
When the file is processed during extraction
Then the file is divided into overlapping chunks using the coarsest available boundary first
And findings are deduplicated across chunk boundaries to avoid double-counting
And each finding retains its citation to the originating path and line range
```

### As a Migration Architect, I want each file's extraction to be enriched with its import-graph neighbourhood, so that findings describe cross-file flows rather than treating each file in isolation.

```gherkin
Given a repository with interdependent files
And the cross-file import graph option is enabled in settings
When per-file extraction runs
Then the system builds a cross-file import and reference graph before extraction begins
And each file's extraction pass is enriched with the files it depends on and the files that depend on it
And findings can assert cross-file relationships rather than single-file observations
```

---

## Feature: Section Synthesis and Derivative Generation

### As a Documentation Engineer, I want primary wiki sections to be synthesized from per-file findings with full citation trails, so that every assertion in the output is traceable to a specific source location.

```gherkin
Given a set of per-file findings accumulated for a primary section
When the aggregation stage runs for that section
Then a coherent markdown body is produced from the findings
And every assertion in the body is backed by numbered citations traceable to the source files and line ranges from which it was inferred
And claims present in the supporting evidence but absent from the narrative body are collected into a separate supporting-claims list rather than silently dropped
```

### As a Documentation Engineer, I want derivative sections to be synthesized only after all their upstream primary sections are finalized, so that personas, user stories, and diagrams are grounded in complete evidence.

```gherkin
Given a wiki configuration where derivative sections declare upstream dependencies
When the pipeline reaches the derivation stage
Then sections are processed in topological order enforced at startup
And no derivative section is synthesized until all of its declared upstream sections are finalized
And if an upstream section is absent or empty, a placeholder is emitted rather than fabricated content
```

---

## Feature: Wiki Scaffolding

### As a Pipeline Operator, I want wiki initialization to be idempotent, so that re-running the scaffold command in an automated pipeline does not overwrite existing content.

```gherkin
Given a project with a partially populated wiki directory structure
When the wiki scaffold command is run again
Then existing content is left untouched
And only missing structural pieces are created
```

---

## Feature: Conflict Detection and Evidence Traceability

### As a Migration Architect, I want incompatible assertions across source files to be surfaced explicitly rather than silently resolved, so that my team can identify and resolve tribal knowledge conflicts before re-implementation.

```gherkin
Given a codebase where two or more source files make incompatible assertions about the same domain topic
When the aggregation stage produces the section body
Then the conflict is surfaced under a dedicated heading in the output
And each conflicting position retains its own source references
And the narrative does not silently choose one position over another
```

### As a Migration Architect, I want every factual claim in the wiki traceable to the file and line range from which it was inferred, so that I can verify assertions against the original source.

```gherkin
Given a generated wiki section containing factual assertions
When I inspect any claim in the narrative body
Then the claim is backed by one or more SourceRefs each identifying a repo-relative file path and line range
And a claim with no SourceRefs is explicitly marked as unsupported
```

---

## Feature: Quality Assurance

### As a Quality Reviewer, I want sections evaluated against a structured rubric and revised when they fall below a quality threshold, so that the generated wiki meets a minimum standard before publication.

```gherkin
Given the critic-and-reviser loop is enabled in settings
And a minimum quality threshold score is configured
When a section body is synthesized
Then the section is scored on a 0–10 rubric identifying unsupported claims and coverage gaps
And if the score falls below the configured threshold a revision pass is triggered
And the revised body is accepted only if it improves or matches the prior score
And if synthesis fails entirely raw notes are emitted directly preserving information at the cost of polish
```

### As a Pipeline Operator, I want the critic-and-reviser loop to be disabled by default, so that generation time remains predictable in routine runs.

```gherkin
Given a pipeline run with default settings
When the pipeline generates and derives sections
Then the critic-and-reviser loop is not executed
And generation time is predictable
When the loop is explicitly enabled via settings
Then it is applied to all sections and is most beneficial for derivative sections where single-shot synthesis is most likely to stray from evidence
```

---

## Feature: Coverage and Readiness Reporting

### As a Pipeline Operator, I want a single-page readiness report listing per-section metrics, so that I can assess documentation completeness in an automated pipeline without requiring an AI provider.

```gherkin
Given a wiki with one or more generated sections
When the report command is run
Then a markdown table is produced listing each section with its contributing file count, finding count, body character length, quality score, and most prominent gap or unsupported claim
And the coverage portion of the report executes without an AI provider
And the report output is safe for automated pipelines
```

---

## Feature: Incremental and Crash-Resumable Operation

### As a Pipeline Operator, I want unchanged files and sections to be served from cache on re-runs, so that the pipeline completes quickly when only a subset of files has changed.

```gherkin
Given a repository that has been walked at least once with caching enabled
And some files have not changed since the last run
When the pipeline runs again
Then files whose content fingerprint matches the cache are skipped without re-extraction
And sections whose notes-payload hash matches the cache are served from cache without re-synthesis
And the cache is written after each individual file completes so that a mid-run crash leaves previously completed work intact
```

### As a Pipeline Operator, I want cache entries to be automatically invalidated when the cache format changes, so that obsolete data from a previous version never silently corrupts a rebuild.

```gherkin
Given a pipeline upgrade that changes the internal cache format version
When the pipeline runs after the upgrade
Then the version number embedded in existing cache files is compared to the current version
And a mismatch triggers a clean rebuild discarding all stale entries
And cache files are written atomically so that a crash during persistence never leaves a corrupted cache
```

### As a Documentation Engineer, I want a force-reanalysis mode that drops all cached data, so that I can guarantee a completely fresh walk when cache state is suspect.

```gherkin
Given a pipeline run invoked with force-reanalysis mode enabled
When the pipeline begins
Then the on-disk cache is dropped entirely before any files are processed
And all files are re-extracted and all sections re-synthesized from scratch regardless of cached state
```

### As a Documentation Engineer, I want stale cache entries for removed files to be prunable in bulk, so that the cache does not accumulate entries for files that no longer exist in the repository.

```gherkin
Given a repository from which one or more files have been deleted since the last walk
When the cache pruning operation is run
Then cache entries for files no longer present in the repository are removed
And remaining entries for current files are left intact
```

---

## Feature: Interactive Query Interface

### As a Codebase Explorer, I want to open a conversational session grounded in the generated wiki, so that I can ask natural-language questions about the codebase without reading raw source files.

```gherkin
Given a wiki with one or more sections containing meaningful content
When I open a conversational session
Then only sections with meaningful content are loaded as context
And placeholder sections are excluded from the context
And I can ask multi-turn questions drawing on the loaded wiki sections
And I can inspect which sections are currently loaded as context
```

### As a Codebase Explorer, I want to reset the conversation history without losing the wiki context, so that I can start a fresh line of questioning without reloading the wiki.

```gherkin
Given an active conversational session with accumulated conversation history
When I issue a history-reset command
Then the conversation history is cleared
And the frozen system prompt built from the wiki sections is retained
And subsequent questions are answered using the same wiki context without the prior exchanges
```
