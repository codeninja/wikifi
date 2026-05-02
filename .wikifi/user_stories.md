# User Stories

## Feature: Wiki Workspace Initialisation

**As a Wiki Operator, I want the workspace to be initialised idempotently, so that re-running setup does not destroy work that has already been completed.**

```gherkin
Given a target project root that already contains a partially populated wiki workspace
When the workspace initialisation command is invoked again
Then the existing directory structure, configuration file, version-control ignore rules,
  and per-section placeholder documents are left untouched
And no previously generated section bodies are overwritten
```

---

## Feature: Technology-Agnostic Wiki Generation

**As a Migration Architect, I want the wiki to express all findings in domain terms rather than in the vocabulary of the legacy technology stack, so that the new system design is not inadvertently shaped by the old implementation's structure.**

```gherkin
Given a legacy codebase built on any technology stack
When a full wiki generation run completes
Then every wiki section body is expressed in technology-agnostic, domain-level language
And no technology-specific constructs, naming conventions, or structural patterns
  from the source appear in the generated output
```

**As a Migration Architect, I want the wiki to be organised into all defined sections covering domains, intent, capabilities, integrations, entities, cross-cutting concerns, and hard specifications, so that I have a complete set of artefacts to brief the wider delivery team.**

```gherkin
Given a completed wiki generation run against a legacy repository
When I inspect the generated wiki workspace
Then eight primary sections are populated with evidence-backed content
And three derivative sections (user personas, user stories, and architectural diagrams)
  are synthesised from the completed primary sections
And any section for which no evidence was found contains an explicit placeholder
  declaring the gap rather than fabricated content
```

---

## Feature: Source Traceability

**As a Migration Developer, I want every assertion in the wiki to carry a numbered citation back to its originating file and line range, so that I can verify any claim without re-reading the entire codebase.**

```gherkin
Given a populated wiki section body
When I read a claim made in that section
Then the claim is annotated with a numbered citation
And the citation resolves to a specific repo-relative file path
  and an inclusive line range in the source repository
And a content fingerprint is stored alongside the citation to enable staleness detection
```

**As a Migration Developer, I want claims that have no source backing to be explicitly flagged as unsupported, so that I know which assertions require further investigation rather than assuming all claims are verified.**

```gherkin
Given a wiki section that contains a claim for which no source reference could be identified
When the section is rendered
Then the claim is explicitly marked as unsupported
And no citation number is fabricated or silently omitted without a visible notice
```

---

## Feature: Conflict Surfacing

**As a Migration Architect, I want contradictory assertions from different parts of the codebase to be surfaced explicitly, so that I can treat disagreements as high-priority migration risks rather than discovering them later in the build.**

```gherkin
Given two or more source files that make incompatible assertions about the same topic
When the section aggregation stage processes their findings
Then a dedicated "Conflicts in source" block is included in the relevant section body
And each conflicting position is listed with its own source references
And no silent resolution or averaging of the conflict is performed
```

---

## Feature: Cross-File Context Enrichment

**As a Migration Developer, I want extraction findings to reflect inter-file flows rather than isolated per-file summaries, so that I understand how components in an assigned domain area interact with one another.**

```gherkin
Given an in-scope file that imports other in-scope files or is imported by them
When the extraction pipeline processes that file
Then the file's import neighbourhood (files it depends on and files that depend on it)
  is included as context during extraction
And the resulting findings describe cross-file interactions
  rather than treating the file in isolation
```

---

## Feature: Specialised Schema Parsing

**As a Migration Architect, I want structured schema files — including SQL definitions, API contract specifications, interface definition files, graph schemas, and database migrations — to be parsed deterministically, so that entity and relationship extraction from these files is reliable and reproducible.**

```gherkin
Given a repository that contains structured schema artifacts
When the extraction pipeline classifies and routes those files
Then each schema file is processed by a purpose-built deterministic parser
And the resulting findings describe entities, relationships, operations, and constraints
And no AI model invocation is required for the deterministic parsing path
```

**As a Wiki Operator, I want unparseable schema files to produce an advisory finding directing reviewers to inspect the file manually, so that a single malformed file does not silently omit domain knowledge from the wiki.**

```gherkin
Given a schema file that cannot be parsed by the deterministic parser
When the specialised extraction path attempts to process that file
Then an advisory finding is produced directing reviewers to inspect the file manually
And no silent failure or empty result is returned without notice
```

---

## Feature: Large File Handling

**As a Migration Developer, I want large source files to be fully analysed regardless of size, so that no content is silently missed during AI-assisted extraction.**

```gherkin
Given a source file whose size exceeds the processing capacity of a single extraction pass
When the extraction pipeline routes the file through the AI-assisted extraction path
Then the file is recursively split into overlapping chunks
And each chunk is processed independently
And findings from all chunks are combined so that no content is omitted
```

---

## Feature: Incremental and Resumable Processing

**As a Migration Developer, I want incremental runs to skip files and sections that have not changed, so that iterating on a large codebase does not require waiting for a full re-walk each time.**

```gherkin
Given a repository that has been walked at least once
And a subsequent run in which only a subset of files has changed
When the pipeline runs again
Then only files whose content fingerprint has changed are re-extracted
And only wiki sections whose contributing notes payload has changed are re-aggregated
And all unchanged results are served from the content-addressed cache
```

**As a Wiki Operator, I want an interrupted pipeline run to resume from the last processed file, so that no completed extraction work is lost when a run is cut short.**

```gherkin
Given a pipeline run that was interrupted before processing all in-scope files
When the pipeline is restarted
Then processing resumes from the first unprocessed file
And all previously persisted extraction results are retained and not re-run
```

**As a Wiki Operator, I want to force a full cache invalidation, so that I can obtain a clean re-walk when the pipeline configuration or extraction logic has materially changed.**

```gherkin
Given an existing populated cache for a repository
When a cache invalidation is requested
Then all cached extraction and aggregation results are cleared
And the next run processes every in-scope file from scratch
```

---

## Feature: Derivative Section Synthesis

**As a Migration Architect, I want Gherkin-style user stories generated automatically from the extracted wiki, so that I can brief the delivery team with structured acceptance criteria without writing them by hand.**

```gherkin
Given all primary wiki sections have been populated with evidence-backed content
When the derivative section synthesis stage runs for user stories
Then a set of Gherkin-style user stories is produced, grouped by feature
And each story is grounded only in capabilities and entities present in the primary sections
And if the required upstream primary sections are empty, a placeholder is written
  declaring the gap rather than fabricating stories
```

**As a Migration Architect, I want Mermaid architectural diagrams generated automatically from the extracted wiki, so that I have portable visual artefacts for briefing the delivery team.**

```gherkin
Given all primary wiki sections have been populated with evidence-backed content
When the derivative section synthesis stage runs for architectural diagrams
Then valid Mermaid diagram markup is produced
  reflecting entities and relationships found in the primary sections
And no diagram elements are introduced that are not supported by the primary section evidence
```

---

## Feature: Interactive Knowledge Querying

**As a Migration Developer, I want to ask targeted questions about a specific domain area through a conversational interface, so that I can find precise answers without reading multiple wiki sections sequentially.**

```gherkin
Given a wiki that has been generated for a legacy repository
When I open an interactive chat session
Then the session is grounded in all meaningfully populated wiki sections
And placeholder or empty sections are excluded from the context
And I can conduct multi-turn exchanges with conversation history retained across turns
```

**As a Domain Knowledge Consumer, I want to interrogate system behaviour conversationally without needing a technical intermediary, so that I can validate or challenge the extracted domain model directly against my own business knowledge.**

```gherkin
Given a populated wiki for a legacy system
When I open an interactive chat session and ask a question about system behaviour
Then the assistant responds using only information present in populated wiki sections
And the response is expressed in plain, domain-level language
  without implementation-specific detail
And I can reset conversation history and begin a fresh line of questioning
  within the same session while retaining the wiki context
```

**As a Migration Developer, I want to inspect which wiki sections are currently loaded as context in a chat session, so that I understand the boundaries of the assistant's knowledge before relying on its answers.**

```gherkin
Given an active interactive chat session
When I request a context introspection
Then the session reports which sections are currently loaded as grounding context
And sections that are empty or contain only placeholders are listed as excluded
```

---

## Feature: Quality Assurance Pass

**As a Wiki Operator, I want each synthesised section to be scored against its brief and the upstream evidence, so that I can identify sections containing unsupported claims before the wiki is shared with the team.**

```gherkin
Given a synthesised wiki section and the upstream evidence it was derived from
When the critic-and-reviser pass runs
Then a quality score between 0 and 10 is produced for that section
And the critique itemises unsupported claims, gaps relative to the section brief,
  and concrete revision suggestions
```

**As a Wiki Operator, I want sections that score below a configurable threshold to be automatically revised, so that low-quality sections are improved before the wiki reaches the broader team.**

```gherkin
Given a synthesised section whose quality score falls below the configured threshold
When automatic revision is triggered
Then a revised body is produced informed by the critique's suggestions
And the revised section is accepted only if its score matches or improves on the original
And if the revision would regress the score, it is rejected
  and the original body is retained
```

---

## Feature: Coverage and Dead-Zone Reporting

**As a Wiki Operator, I want a coverage report showing per-section file counts, finding counts, body sizes, and quality scores, so that I can assess the completeness of the wiki before distributing it.**

```gherkin
Given a completed wiki-generation run
When the report command is invoked
Then a markdown table is produced listing every wiki section
  with its contributing file count, finding count, body size, and emptiness status
And where a critic pass has been run, the quality score and highest-priority content gap
  are included for each section
```

**As a Wiki Operator, I want files that were processed but produced no findings to be surfaced as dead zones in the coverage report, so that I can identify blind spots in the analysis and decide whether to investigate them further.**

```gherkin
Given a repository walk in which some in-scope files yielded no findings for any section
When the coverage report is generated
Then a list of dead-zone files is included in the report
And those files are distinguished from files that were excluded during the classification stage
```

---

## Feature: AI Backend Configuration

**As a Wiki Operator, I want to select and override the active AI backend via an environment variable or a per-invocation flag, so that the pipeline can run in air-gapped or data-sensitive environments without requiring code changes.**

```gherkin
Given a deployment environment that requires a privately hosted or on-premise AI backend
When the pipeline is invoked with a backend selection flag or the corresponding
  environment variable set
Then all AI-assisted extraction, aggregation, derivation, and critic calls
  are routed to the specified backend
And no modification to pipeline code or shared configuration files is required
```

---

## Feature: Graceful Degradation

**As a Wiki Operator, I want the pipeline to recover gracefully from AI synthesis failures on individual sections, so that a single failed section does not prevent the rest of the wiki from being produced.**

```gherkin
Given a wiki section for which AI synthesis fails during aggregation
When the pipeline handles the failure
Then the raw collected notes for that section are emitted directly in the section body
And the error is surfaced inline in the section rather than silently suppressed
And all remaining sections continue to be generated normally
```
