# User Stories

## Feature: Repository Analysis and Pipeline Execution

**As a Migration Planner, I want to run the full four-stage analysis pipeline against a target repository, so that I can establish a shared, authoritative understanding of what the system does before any migration work begins.**

```gherkin
Given a target repository has been registered with the system
And a project configuration file is present at the expected location
When I invoke the walk command
Then the system performs repository introspection and produces an IntrospectionResult
  with include/exclude patterns, a purpose hypothesis, and filtering rationale
And each included file produces FileFindings containing section-level descriptions
  and a one-sentence file-role summary
And all findings are synthesized into coherent markdown narratives for each of the
  eight primary wiki sections
And derivative sections are generated only after all primary sections are finalized
And a WalkReport is returned carrying IntrospectionResult, ExtractionStats,
  AggregationStats, DerivationStats, WalkCache state, and RepoGraph
```

---

## Feature: Evidence Traceability

**As a Migration Planner, I want every claim in the generated wiki traceable to a precise source location, so that I can verify assertions and investigate discrepancies before committing to migration decisions.**

```gherkin
Given the pipeline has completed a walk of the repository
When I read any narrative section of the generated wiki
Then each factual sentence is backed by at least one SourceRef identifying a
  repo-relative file path and an optional inclusive line range
And numbered citations in section narratives resolve to the originating files
And any Claim with no supporting sources is explicitly marked as unsupported
  rather than silently presented as fact
```

---

## Feature: Contradiction and Conflict Surfacing

**As a Migration Planner, I want conflicting assertions about the same domain topic surfaced explicitly, so that I do not inherit wrong assumptions when planning the migration.**

```gherkin
Given two or more source files contain incompatible assertions about the same
  domain topic
When the aggregation stage processes findings from those files
Then a Contradiction entity is created grouping the conflicting Claims
And each conflicting Claim retains its own SourceRefs pointing to its
  originating file path and line range
And the disagreement is rendered explicitly in the relevant section narrative
  rather than being silently merged into a single assertion
```

---

## Feature: Pre-Migration Coverage Reporting

**As a Migration Planner, I want a coverage report after each pipeline run, so that I can confirm the walk reached all intent-bearing areas of the repository before acting on the output.**

```gherkin
Given a pipeline walk has completed
When I invoke the report command
Then a WikiReport is produced aggregating all SectionReports
And each SectionReport shows contributing file count, findings count,
  body character length, and an emptiness flag
And a WikiQualityReport is available with CoverageStats showing total files,
  files with findings, and per-section finding and file counts
And sections with zero findings are flagged as empty rather than omitted
```

---

## Feature: Integration Inventory

**As a Migration Planner, I want a structured inventory of external integration touchpoints, so that I can identify dependencies that must be preserved, replaced, or renegotiated during migration.**

```gherkin
Given the repository contains API contract files, interface definition files,
  or data-definition schema files
When the schema-aware extraction stage routes those files to specialized extractors
Then HTTP endpoints with operation, path, and summary are surfaced as structured findings
And remote procedure calls including streaming legs are extracted from interface
  definition files
And foreign-key constraints and persisted entity relationships are extracted from
  data-definition files
And each finding carries one or more SourceRefs traceable to the originating
  file and line range
And the integrations section of the wiki consolidates these findings into a
  readable inventory
```

---

## Feature: Schema-Aware Extraction

**As a Migration Planner, I want schema and contract files processed by format-specific extractors, so that persisted entity structures and external contracts are surfaced accurately without relying solely on general inference.**

```gherkin
Given the repository contains files whose kind is classified as SQL data-definition,
  API contract, interface definition, or query/mutation schema
When the extraction stage routes these files by FileKind to the appropriate
  specialized extractor
Then persisted entities with their columns, foreign-key edges, uniqueness and
  nullability invariants, and index definitions are captured as SpecializedFindings
And closed value sets and shared shape contracts from schema files are captured
  as separate finding categories
And every SpecializedFinding carries one or more SourceRefs traceable to the
  source file and line range
And a SpecializedResult collects all findings for the file along with an optional
  summary string
```

---

## Feature: Wiki Navigation and Onboarding

**As an Onboarding Engineer, I want structured, domain-level descriptions of each file's role, so that I can build a coherent mental model of the system without reading the entire codebase.**

```gherkin
Given a wiki has been generated for the target repository
When I navigate to any primary wiki section
Then each included file is represented by at least one SectionFinding with a
  technology-agnostic description of one to five sentences
And each file's one-sentence role summary from its FileFindings is accessible
And cross-file import-graph context has been injected so relationships between
  files are reflected in section narratives
And all descriptions are free of implementation-specific terminology
```

**As an Onboarding Engineer, I want a navigable wiki covering all eight primary concerns plus derivative sections, so that I can locate relevant information without a guided tour of the codebase.**

```gherkin
Given the pipeline has completed a walk
When I open the generated wiki
Then eight primary sections are present: business domains, system intent,
  capabilities, external dependencies, integrations, cross-cutting concerns,
  core entities, and hard specifications
And three derivative sections are present: personas, user stories, and
  architectural diagrams
And any section for which no findings exist contains a placeholder declaring
  the gap rather than fabricating content
```

---

## Feature: Conversational Query Interface

**As an Onboarding Engineer, I want to ask targeted questions about the system through a conversational interface and receive answers that cite specific wiki sections, so that I can deepen my understanding without interrupting senior colleagues.**

```gherkin
Given a wiki has been generated and a WikiLayout exists at the project root
When I invoke the chat subcommand and submit a domain question
Then the ChatSession formulates its response using a frozen system prompt built
  from the populated wiki sections
And each response cites the specific sections from which it draws information
And the session accumulates conversation history across turns while retaining
  the frozen wiki context
And when the wiki does not contain information relevant to the question the
  session explicitly declares the gap rather than inventing an answer
```

**As a Non-Technical Stakeholder, I want to ask plain-language questions about system capabilities and integration points, so that I can assess scope and risk without requiring engineering background.**

```gherkin
Given a wiki has been generated and the chat subcommand is available
When I submit a plain-language question about a system capability or integration
Then the ChatSession provides an answer grounded in the business-domain,
  system-intent, and integrations sections
And the answer contains no implementation-specific terminology
And if the question falls outside what the wiki covers the session admits the
  gap explicitly rather than speculating
```

---

## Feature: Technology-Agnostic Output

**As a Non-Technical Stakeholder, I want all generated documentation expressed in domain terms, so that the wiki remains meaningful and shareable after the technology stack changes.**

```gherkin
Given the pipeline has completed a walk and generated all wiki sections
When I read any section body
Then no section contains references to specific implementation technologies,
  frameworks, or libraries
And business-level capability summaries are present in the business domains
  and system intent sections
And the integrations section describes external dependencies in terms that
  do not require an engineering background to interpret
```

---

## Feature: Incremental Re-Processing and Caching

**As a Platform or Documentation Engineer, I want the pipeline to skip unchanged files on repeated runs, so that documentation stays current without incurring the full inference cost of a fresh walk.**

```gherkin
Given a prior pipeline walk has completed and a WalkCache is populated
And only a subset of source files have changed since the last run
When I invoke the walk command again
Then files whose content fingerprint matches an existing CachedFindings entry
  are served from cache without triggering new inference calls
And section aggregations whose notes-payload hash matches an existing
  CachedSection entry are served from cache
And ExtractionStats records the count of cache hits and misses for the run
```

**As a Platform or Documentation Engineer, I want interrupted pipeline runs to resume from the point of failure, so that compute already expended on a large repository is not wasted.**

```gherkin
Given a pipeline walk was interrupted before all files were processed
And the WalkCache contains findings for files processed before the interruption
When I re-invoke the walk command
Then files already present in the cache are not re-processed
And the run completes from the point of interruption rather than restarting
And the final WalkReport reflects contributions from both cached and newly
  processed files
```

---

## Feature: Quality Review Loop

**As a Platform or Documentation Engineer, I want sections that fall below a configured quality threshold to be automatically revised, so that generated documentation meets a defined quality bar before it is distributed.**

```gherkin
Given the quality review loop feature flag is enabled in Settings
And a numeric quality threshold has been configured for the project
When the derivation stage produces a Critique for each section
Then any section whose Critique score falls below the threshold triggers an
  automatic revision pass
And a ReviewOutcome is recorded capturing the section identifier, initial
  Critique, current body text, revision-applied flag, and optional follow-up Critique
And DerivationStats accumulates counts of sections derived, revised, and skipped
```

**As a Platform or Documentation Engineer, I want a per-section quality audit report available after each run, so that I can verify coverage and quality before distributing the wiki.**

```gherkin
Given a pipeline walk has completed with the review loop enabled
When I request the quality report
Then a WikiQualityReport is produced with an overall numeric score and a
  mapping of section identifiers to individual Critiques
And each Critique declares the integer score, unsupported claims, gaps relative
  to the section brief, and concrete revision suggestions
And CoverageStats within the report show total files, files with findings,
  and per-section finding and file counts
```

---

## Feature: Per-Project Pipeline Configuration

**As a Platform or Documentation Engineer, I want each project to carry its own configuration controlling provider, model, feature flags, and quality threshold, so that different projects can express different cost-quality trade-offs independently.**

```gherkin
Given a project TOML configuration file is present at the project root
When the pipeline is initialized for that project
Then Settings are loaded from the configuration file including provider and model
  identity, inference endpoint, timeout, file-size and chunk thresholds, pipeline
  feature flags, revision quality threshold, and provider-specific credentials
And the chosen provider is the sole point of contact between the pipeline and
  any language-model backend for that run
And if the configuration file is absent or unparseable the system falls back
  to environment-derived defaults without failing
```
