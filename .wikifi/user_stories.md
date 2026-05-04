# User Stories

## Feature: Full Pipeline Execution

**Story 1 — Systems Architect initiates a full wiki generation run**

*As a Systems Architect, I want to trigger the complete four-stage analysis pipeline against a repository, so that I can produce a technology-agnostic, auditable wiki of the system's domain intent without manually reading every source file.*

```gherkin
Given a target repository root has been identified
And a WalkConfig has been prepared capturing the root directory, exclude patterns, gitignore flag, and file-size thresholds
When the walk command is issued
Then Stage 1 executes and produces an IntrospectionResult with include/exclude patterns, detected languages, and a likely-purpose paragraph
And Stage 2 processes every included file, emitting SectionFindings classified into the primary section taxonomy
And recognised schema and contract file kinds are routed to specialised extractors rather than general-purpose analysis
And Stage 3 synthesises per-file findings into polished markdown for each primary wiki section
And Stage 4 synthesises derivative sections from the aggregated primary sections
And a WalkReport is produced aggregating the IntrospectionResult, ExtractionStats, AggregationStats, DerivationStats, and cache snapshot
```

---

**Story 2 — Pipeline Operator initialises the wiki workspace before any analysis**

*As a Pipeline Operator, I want to initialise a browsable wiki stub before running analysis, so that the wiki structure is always present regardless of pipeline state.*

```gherkin
Given a target repository root and Settings have been configured
When the init command is issued
Then a WikiLayout is created as the single source of truth for every artefact path in the workspace
And per-section markdown stub files exist at their expected locations
And no extraction, aggregation, or derivation processing is triggered
```

---

## Feature: Traceability and Citation

**Story 3 — Systems Architect traces any assertion to its source file**

*As a Systems Architect, I want every assertion in the generated wiki to carry a citation marker linked to a specific file and line range, so that I can verify any claim against the original codebase and produce an auditable record.*

```gherkin
Given the aggregation stage has produced an EvidenceBundle for a wiki section
When the section body is rendered and written to disk
Then every Claim in the bundle carries at least one SourceRef identifying a repo-relative file path and, where applicable, a line range
And each citation marker in the prose corresponds to a sources footer entry referencing that SourceRef
And any Claim carrying no SourceRefs is classified as unsupported and surfaced as such in the associated Critique
```

---

**Story 4 — Re-implementation Engineer verifies a contract claim before coding**

*As a Re-implementation Engineer, I want to inspect the source references attached to entity and contract claims, so that I can confirm an assertion is grounded before encoding it as an assumption in the re-implementation.*

```gherkin
Given a wiki section has been generated containing Claims with SourceRefs
When I read the rendered markdown for that section
Then each SourceRef identifies a repo-relative file path and, where a finding is scoped to specific lines, a line range
And the content fingerprint on each SourceRef is available to detect stale references
And no claim is presented as fact without at least one SourceRef or an explicit unsupported declaration
```

---

## Feature: Contradiction Surfacing

**Story 5 — Systems Architect identifies drifted contracts**

*As a Systems Architect, I want conflicting information across source files to be surfaced as explicit Contradictions rather than silently merged, so that I can identify where the codebase has accumulated drift from its intended contracts.*

```gherkin
Given two or more source files contain conflicting information about the same domain concept
When the aggregation stage processes findings from those files
Then a Contradiction entity is emitted carrying a one-sentence conflict summary
And each conflicting position is represented as a Claim with its own set of SourceRefs pointing to the originating files
And the Contradiction appears in the EvidenceBundle alongside consistent Claims
And the rendered section visibly marks the disagreement rather than resolving it to a single interpretation
```

---

**Story 6 — Re-implementation Engineer reviews contradictions before writing dependent code**

*As a Re-implementation Engineer, I want to see all known contradictions in the documentation before I write code that depends on a behavioural assumption, so that I avoid encoding incorrect assumptions that are expensive to fix later.*

```gherkin
Given a wiki section contains one or more Contradiction entities in its EvidenceBundle
When I open the rendered section
Then each Contradiction presents its conflict summary and all competing Claim positions
And each position includes traceable SourceRefs to the originating files
And no Contradiction is silently suppressed or collapsed to a single authoritative interpretation
```

---

**Story 7 — Migration Lead identifies known schema-versus-usage conflicts**

*As a Migration Lead, I want unresolved conflicts between schema definitions and application-layer usage to be explicitly declared, so that I can assess the risk of acting on the current documentation before committing resources to re-implementation.*

```gherkin
Given specialised extractors have processed schema and contract files
And the aggregation stage has compared those findings against application-layer findings in the same section
When I review the relevant wiki section
Then any disagreement between the schema definition and its application-layer usage is represented as a Contradiction
And each position in the Contradiction carries SourceRefs to the schema file and to the application file respectively
And the conflict is presented in terms of domain behaviour, not implementation mechanics
```

---

## Feature: Quality and Coverage Reporting

**Story 8 — Migration Lead assesses overall coverage before committing resources**

*As a Migration Lead, I want a structured coverage and quality report after pipeline execution, so that I can determine whether the analysis covered the entire codebase and whether the wiki is reliable enough to act on as a re-implementation specification.*

```gherkin
Given the pipeline has completed a walk run
When the report command is issued
Then a WikiReport is returned containing a list of SectionReports
And each SectionReport carries a contributing-file count, finding count, body character length, and emptiness flag
And the WikiQualityReport provides an overall floating-point quality score
And each section's Critique provides an integer score between 0 and 10, a summary judgment, lists of unsupported claims and gaps, and suggested edits
And CoverageStats include total files analysed, files with at least one finding, and a coverage percentage derived from those two counts
```

---

**Story 9 — Migration Lead identifies under-evidenced sections**

*As a Migration Lead, I want gap reporting to explicitly flag empty or under-evidenced sections, so that I can decide whether to accept a gap or request additional analysis rather than acting on a silently incomplete wiki.*

```gherkin
Given a WikiReport has been generated from the most recent pipeline run
When I review the SectionReports
Then any section with an emptiness flag set is clearly identified
And the Critique associated with that section lists specific gaps not covered by the current evidence
And the Critique includes suggested edits so the gap can be addressed without re-running the full pipeline
And no section appears populated when its evidence is insufficient to support its claims
```

---

**Story 10 — Pipeline Operator monitors run statistics for cost and completeness**

*As a Pipeline Operator, I want structured run statistics after every walk, so that I can understand what the pipeline processed, where it hit the cache, and what each stage produced.*

```gherkin
Given a walk command has completed
When I inspect the WalkReport
Then ExtractionStats show files seen, files with findings, total findings, chunks processed, cache hits, specialised-extractor files, and a file-kind breakdown
And AggregationStats show sections written, found empty, served from cache, surgically edited, and fully rewritten
And DerivationStats show sections derived, skipped due to absent upstream content, revised by the critic loop, and served from cache
And the cache snapshot in the WalkReport shows hit and miss counts per cache scope
```

---

## Feature: Interactive Grounded Query

**Story 11 — Re-implementation Engineer queries entity contracts via chat**

*As a Re-implementation Engineer, I want an interactive chat interface grounded in the wiki content, so that I can get fast answers about entity relationships and API contracts without reading every source file.*

```gherkin
Given one or more wiki sections have been read from disk as LoadedSections
And a ChatSession has been initialised with a system prompt built from those sections and a mutable message history
When I submit a question about a specific entity, contract, or integration touchpoint
Then the assistant replies with an answer grounded in the content of the loaded sections
And if the loaded sections contain no relevant information, the reply explicitly acknowledges the gap rather than inventing an answer
And I can reset the message history without losing the loaded section context
```

---

**Story 12 — Systems Architect queries system behaviour with confidence**

*As a Systems Architect, I want chat-mode answers to be grounded strictly in documented wiki content, so that I can rely on responses for decisions without risk of receiving unsupported speculation.*

```gherkin
Given a ChatSession has been established with wiki sections covering the relevant domains
When I submit a question that has a direct answer within the loaded sections
Then the response is consistent with the Claims and EvidenceBundles of those sections
And the response does not assert facts beyond what the loaded sections contain
When I submit a question that has no answer in the loaded sections
Then the response explicitly states that the information is not present in the current wiki
```

---

## Feature: Incremental Caching and Surgical Updates

**Story 13 — Pipeline Operator re-runs the pipeline incrementally after source changes**

*As a Pipeline Operator, I want unchanged files to be served from cache on re-runs, so that large-repository walks are reduced from hours-long full analyses to minutes-long incremental updates.*

```gherkin
Given a previous walk has populated CachedFindings, CachedSection, CachedDerivation, and CachedIntrospection entries
And a subset of source files have changed since the last run
When the walk command is issued again
Then files whose content fingerprint matches their CachedFindings entry are skipped and served from cache
And only files with changed fingerprints are re-extracted
And if the walked file set is unchanged, the CachedIntrospection is returned and all later stages are short-circuited
And cache hit and miss counts per scope are reported in ExtractionStats and the WalkReport cache snapshot
```

---

**Story 14 — Pipeline Operator applies surgical edits when only a small number of findings have changed**

*As a Pipeline Operator, I want the pipeline to surgically patch only affected portions of a cached section when findings have changed minimally, so that I avoid the full rewrite cost for sections where most content remains valid.*

```gherkin
Given a CachedSection exists for a wiki section
And a SectionChange has been computed showing a low churn_ratio with a small number of new or disappeared findings
When the aggregation stage processes that section
Then a surgical pass is executed rather than a full rewrite
And the SurgicalEdit output carries the edited body, new SurgicalClaims, indices of cached claims to drop, and the updated contradictions list
And AggregationStats record the section as surgically edited rather than fully rewritten
When the churn_ratio exceeds the configured surgical threshold
Then the section is fully rewritten instead and AggregationStats record it accordingly
```

---

## Feature: Provider and Model Configuration

**Story 15 — Pipeline Operator switches AI backend without altering pipeline logic**

*As a Pipeline Operator, I want to select among multiple AI provider backends — including on-premises options — without changing pipeline behaviour, so that I can meet cost, latency, or data-residency requirements without custom pipeline changes.*

```gherkin
Given the Settings entity has been configured with a provider name, model identifier, inference endpoint, and request timeout
When the walk or chat command is issued
Then an LLMProvider is initialised from the configured provider name and model identifier
And all three LLMProvider call surfaces operate identically regardless of which backend is selected
And changing the provider identity in Settings requires no changes to extraction, aggregation, derivation, or chat logic
```

---

## Feature: Specialised Contract and Schema Extraction

**Story 16 — Systems Architect extracts schema and contract definitions deterministically**

*As a Systems Architect, I want recognised schema and interface-definition files to be processed by purpose-built extractors rather than general-purpose analysis, so that contract information is captured accurately and at reduced cost.*

```gherkin
Given the repository contains files of recognised kinds (such as SQL, OpenAPI, Protocol Buffer, GraphQL, or migration artifacts as classified by the FileKind enumeration)
When Stage 2 of the pipeline processes those files
Then each file is routed to the appropriate specialised extractor rather than general-purpose analysis
And the extractor emits SpecializedFinding entities carrying a target section identifier, finding text, and source references
And these findings are classified under the same Section taxonomy as general-purpose findings
And ExtractionStats record the count of specialised-extractor files separately from general files
```

---

**Story 17 — Re-implementation Engineer reads structured contract surfaces from the wiki**

*As a Re-implementation Engineer, I want the generated wiki to include structured descriptions of API surfaces, data schemas, and integration touchpoints extracted from source artifacts, so that I can design the replacement system against documented contracts.*

```gherkin
Given specialised extractors have processed recognised contract and schema files
And their SpecializedFindings have been aggregated into the relevant primary wiki sections
When I read the integrations or entities sections of the wiki
Then the content describes inbound and outbound contract surfaces in technology-agnostic domain terms
And each assertion is backed by SourceRefs pointing to the originating schema or contract file and, where applicable, a line range
And any conflict between a schema definition and its application-layer usage is represented as a Contradiction with traceable positions on each side
```

---

## Feature: Derivative Content Synthesis

**Story 18 — Systems Architect receives synthesised derivative sections from primary content**

*As a Systems Architect, I want derivative content — personas, user stories, and relationship diagrams — to be automatically generated from the primary wiki sections, so that I receive a complete picture of domain intent without manually authoring supplementary documentation.*

```gherkin
Given the aggregation stage has produced populated primary wiki sections
When Stage 4 (derivation) runs
Then each derivative Section synthesises its content from the upstream primary sections declared in its dependency tuple
And each CachedDerivation records the hash of the upstream section bodies it was produced from
And if the upstream bodies are unchanged since the last derivation, the cached derivative body is served without re-synthesis
And DerivationStats record each section as derived, skipped (no upstream content), revised by the critic loop, or served from cache
```

---

**Story 19 — Migration Lead confirms derivative documentation reflects the latest primary analysis**

*As a Migration Lead, I want derivative sections to be automatically invalidated and re-synthesised when their upstream primary sections change, so that personas, stories, and diagrams never misrepresent the current state of the analysis.*

```gherkin
Given a CachedDerivation exists for a derivative section
And one or more of its declared upstream primary sections have been updated since the last derivation run
When Stage 4 runs
Then the cached derivation hash no longer matches the current upstream bodies
And the derivative section is re-synthesised from the updated upstream content
And DerivationStats record the section as newly derived rather than served from cache
And if the critic-and-reviser review loop is configured, a ReviewOutcome is recorded capturing the initial Critique, any revised body, and a revision-occurred flag
```
