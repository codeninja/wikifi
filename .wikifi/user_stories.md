# User Stories

Three distinct groups of stories are derived from the four confirmed personas (Onboarding Developer, Migration Lead, Legacy System Maintainer, Pipeline Operator) and the capabilities described in the upstream sections. Each story is followed by Gherkin acceptance criteria. Personas for whom no upstream evidence exists — end users of the documented system, product managers, and compliance reviewers — are out of scope and are not represented here.

---

## Feature: Repository Discovery and Structured Documentation

### Story 1 — Understand system intent without reading every source file

> *As an Onboarding Developer, I want a structured wiki generated automatically from an unfamiliar codebase, so that I can form an accurate picture of what the system accomplishes without reading every file individually.*

```gherkin
Given a repository root with no prior analysis
When the pipeline runs for the first time
Then a wiki is produced containing at minimum the eight primary sections
  (Domains, Intent, Capabilities, External Dependencies, Integrations,
   Cross-Cutting Concerns, Entities, Hard Specifications)
And each section describes the system in technology-agnostic domain terms
And every claim carries an inline citation marker linked to the originating
  file path and line range
And no section contains implementation-specific language
```

### Story 2 — Navigate cross-module flows without tracing imports manually

> *As an Onboarding Developer, I want findings to describe flows between modules rather than treating each file in isolation, so that I can understand how the system's parts interact without manually tracing every dependency.*

```gherkin
Given a codebase with inter-file dependencies recorded in the repository graph
When a source file is analysed
Then the cross-file reference graph is consulted as part of that file's analysis
And the resulting findings describe relationships and flows to neighbouring modules
And findings are not limited to the contents of the single file under analysis
```

### Story 3 — Confirm analysis covered the full system

> *As a Migration Lead, I want a coverage report showing how many files contributed findings to each wiki section, so that I can verify the analysis walked the full repository before treating the wiki as migration input.*

```gherkin
Given a completed pipeline run
When the coverage report is reviewed
Then each section entry shows the count of files that contributed findings
And sections with zero contributing files are flagged as empty
And a coverage percentage is included in the report
And the report is produced without modifying any wiki section
```

---

## Feature: Citation Traceability

### Story 4 — Trace any wiki claim back to its source before acting on it

> *As a Migration Lead, I want every wiki assertion rendered with inline citation markers linked to a numbered source footer, so that I can verify any claim against the codebase before committing to a re-implementation decision.*

```gherkin
Given a generated wiki section containing multiple claims
When I inspect any individual claim
Then it carries at least one inline citation marker
And that marker resolves to a footer entry identifying the originating file path
  and inclusive line range
And any claim carrying no source reference is explicitly identified as unsupported
  rather than silently omitted
```

---

## Feature: Contradiction Surfacing

### Story 5 — Use conflict blocks as a migration work-item list

> *As a Migration Lead, I want incompatible source claims surfaced as explicit contradiction blocks rather than silently resolved, so that the migration team has a concrete and honest list of ambiguities to resolve.*

```gherkin
Given two or more source locations that assert incompatible things about the same topic
When the wiki section covering that topic is synthesised
Then a "Conflicts in source" block is included in that section
And each conflicting position is listed with its own source references
And no silent reconciliation of the disagreement is performed
```

### Story 6 — Detect newly introduced inconsistencies after a code change

> *As a Legacy System Maintainer, I want newly introduced contradictions made visible after each incremental run, so that I know when a recent change has created an inconsistency without reviewing every file manually.*

```gherkin
Given a previous run produced no contradiction block for a given section
And a code change has introduced conflicting claims between two files
When the pipeline is re-run
Then the affected section now contains a contradiction block surfacing the conflict
And each disagreeing position retains its own source references
```

---

## Feature: Incremental Re-Analysis

### Story 7 — Avoid full analysis cost when only a few files changed

> *As a Legacy System Maintainer, I want only changed files re-processed on each run, so that I do not pay the full analysis cost every time a small part of the codebase changes.*

```gherkin
Given a prior completed pipeline run with cached results
When the pipeline is re-run and only a subset of files have changed
Then only files whose content has changed are re-extracted
And sections whose entire evidence base is unchanged are served from cache
And a run in which nothing has changed is a complete no-op with no generation work performed
```

### Story 8 — Preserve reviewed prose and citation numbering on small changes

> *As a Legacy System Maintainer, I want targeted in-place edits performed when findings change only slightly, so that carefully reviewed prose, citation numbering, and unaffected paragraphs are not erased on every run.*

```gherkin
Given a section with an established cached body
When the re-run finds that only a small subset of findings for that section has changed
And the churn ratio is at or below the configured threshold
Then the system performs a surgical edit introducing new claims and removing dropped claims
And all unaffected paragraphs and citation numbering are retained verbatim
When the churn ratio exceeds the threshold or no prior body exists
Then a full rewrite is performed instead
```

---

## Feature: Quality Review

### Story 9 — Score and revise wiki sections before migration sign-off

> *As a Migration Lead, I want an optional critic-and-reviser cycle to score section bodies and flag unsupported claims, so that I can assess documentation quality before committing to use the wiki as migration input.*

```gherkin
Given a completed wiki generation run
When the critic loop is enabled for a section
Then the section body is scored on an integer scale from 0 to 10
And a list of unsupported claims is produced
And a list of gaps against the section brief is produced
And a concrete list of suggested edits is produced
And a revised body is generated and kept only if it scores better than the original
And per-section quality scores are included in the coverage report alongside
  an overall mean score
```

### Story 10 — Distinguish reviewed from unreviewed cached derivations

> *As a Migration Lead, I want the cache to record whether the critic loop ran for a derivative section, so that a reviewed body is never silently replaced by an unreviewed one on a subsequent run.*

```gherkin
Given a derivative section whose cached body was produced with the critic loop enabled
When the pipeline is re-run with the critic loop disabled
Then the cached reviewed body is served without being silently substituted
  by an unreviewed regeneration
And the reviewed flag in the cached derivation record remains set
```

---

## Feature: Interactive Exploration

### Story 11 — Ask follow-up questions grounded in the generated wiki

> *As an Onboarding Developer, I want an interactive conversational session grounded in the wiki, so that I can chase down specific flows or clarify ambiguous sections without re-reading the raw source.*

```gherkin
Given a wiki with at least one fully populated section
When an interactive session is opened
Then questions can be answered across multiple turns using populated sections as context
And empty or placeholder sections are excluded from the assistant's context
And conversation history can be reset while the wiki context is retained
```

### Story 12 — Know which wiki sections are informing chat answers

> *As an Onboarding Developer, I want to list the currently loaded wiki sections at any time during a session, so that I understand the scope of context informing the answers I receive.*

```gherkin
Given an active interactive session
When the user requests the list of loaded sections
Then the session returns the identifiers and titles of all fully populated sections
  currently included in the context
```

---

## Feature: Pipeline Configuration and Backend Flexibility

### Story 13 — Run the full pipeline unattended from a single entry point

> *As a Pipeline Operator, I want the full pipeline to run unattended via a single command-line entry point, so that I can integrate wiki generation into scheduled automated workflows without manual steps.*

```gherkin
Given a configured repository target and a valid settings source
When the pipeline is invoked via the command-line interface
Then the pipeline runs to completion without prompting for human input
And all domain logic is delegated to internal modules
And the run always produces some output even when individual section synthesis fails
```

### Story 14 — Swap inference backends without changing pipeline logic

> *As a Pipeline Operator, I want the inference backend selected at runtime via configuration, so that I can swap or rotate backends without modifying any pipeline code.*

```gherkin
Given a pipeline configured to use one inference backend
When the backend identifier is changed in configuration
Then the pipeline uses the new backend on the next run
And no pipeline logic changes are required
And all three call surfaces (structured extraction, free-text generation,
  multi-turn conversation) are satisfied by the new backend
```

### Story 15 — Drive per-repository settings independently

> *As a Pipeline Operator, I want configuration resolved in strict precedence order from a per-target config file, environment variables, and built-in defaults, so that each analysed repository controls its own settings without affecting others.*

```gherkin
Given multiple repository targets each with their own config file
When the pipeline is run for a given target
Then the per-target config file takes precedence over environment variables
And environment variables take precedence over built-in defaults
And settings from one target's config file do not affect another target's run
```

---

## Feature: Resilience and Graceful Degradation

### Story 16 — Resume a crashed run without restarting from scratch

> *As a Legacy System Maintainer, I want cache state persisted after each file so that a pipeline crash resumes from the last completed file, so that a failure mid-run does not force a full restart.*

```gherkin
Given a pipeline run that crashes partway through a large codebase
When the pipeline is re-invoked
Then it resumes from the last successfully cached file
And previously cached findings are not re-extracted
And no work completed before the crash is lost
```

### Story 17 — Continue a run when a file cannot be parsed

> *As a Pipeline Operator, I want unparseable files flagged for manual review rather than halting the pipeline, so that a single malformed file does not block analysis of the rest of the repository.*

```gherkin
Given a repository containing one or more malformed structured-artifact files
When the pipeline processes those files
Then each unparseable file is recorded as flagged for manual review
And pipeline execution continues with the remaining in-scope files
And the final run report identifies which files were flagged
```

### Story 18 — Always receive some wiki output even when synthesis fails

> *As a Pipeline Operator, I want raw extracted notes preserved when section synthesis fails, so that automated pipelines always receive some output and never produce blank sections.*

```gherkin
Given a section whose synthesis step fails at runtime
When the pipeline completes
Then the raw extracted notes for that section are preserved in the output
And the section is not blank
And the pipeline does not halt due to the synthesis failure
```
