# Diagrams

_Derivation failed for **Diagrams** (1 validation error for DerivedSection
  Invalid JSON: EOF while parsing a string at line 1 column 4334 [type=json_invalid, input_value='{"body": "Three diagrams... INTRO[Introspection]\\', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/json_invalid). Upstream evidence preserved below._

> Brief: Mermaid diagrams that visualize structural and behavioral relationships across the system: a domain map (graph or classDiagram across domains), an entity relationship view (erDiagram across entities), and an integration flow (sequence or flowchart across integrations). Tech-agnostic — no reference to current stack.


## From domains
# Domains and Subdomains

The system is organized around a single **core domain**: automated codebase documentation — the systematic transformation of a living software repository into a structured, technology-agnostic wiki that is kept coherent as the codebase evolves.

Within that core domain, five supporting subdomains have been identified.

---

### Codebase Analysis

This subdomain is responsible for reading every source file and producing structured, section-aligned findings. It breaks into two tightly coupled concerns:

- **File Classification** — assigning each file a semantic kind (e.g., schema definition, migration script, API contract, or general prose). Path-level disambiguation handles ambiguous files.
- **Knowledge Extraction** — consuming the classification to select the appropriate reading strategy (a specialized structured extractor or a general prose extraction path), then producing normalized findings for each predefined wiki section.

### Source Traceability

This subdomain bridges raw analysis and the human-readable wiki. Every claim written into a section must be anchored to a precise location in the source code. The subdomain also surfaces contradictions — cases where two sources make incompatible assertions about the same topic — so that the final wiki reflects genuine uncertainty rather than silent resolution.

### Incremental Content Maintenance

When the underlying evidence for a section changes, this subdomain decides how much of the previously synthesized content to preserve. It models the decision as a three-way classification — **unchanged**, **surgical** (small targeted edits), or **rewrite** (full regeneration) — driven by a churn ratio derived from the delta in the finding set.

### Wiki Persistence

This subdomain owns the authoritative on-disk representation of the wiki: directory naming and layout conventions, idempotent scaffolding, and all read/write operations against section bodies, per-file extraction notes, configuration, and the cache directory.

### Knowledge Presentation

Once a wiki exists, this subdomain makes it accessible. It encompasses two capabilities: conversational question-and-answer over the generated content, and coverage or quality reporting that surfaces gaps or weak sections.

---

### Domain Relationships

| Subdomain | Depends on | Feeds into |
|---|---|---|
| File Classification | — | Knowledge Extraction |
| Knowledge Extraction | File Classification | Source Traceability, Wiki Persistence |
| Source Traceability | Knowledge Extraction | Wiki Persistence, Knowledge Presentation |
| Incremental Content Maintenance | Wiki Persistence, Knowledge Extraction | Wiki Persistence |
| Wiki Persistence | All upstream | Knowledge Presentation |
| Knowledge Presentation | Wiki Persistence | (end user) |

The boundaries described here are defined by domain responsibility, not by any particular module or technology choice.

## Supporting claims
- The core domain is automated codebase documentation: the systematic transformation of a software repository into a structured, technology-agnostic wiki. [1][2]
- A file classification subdomain tags every file with a semantic kind and handles path-level disambiguation for ambiguous files. [3]
- A knowledge extraction subdomain consumes the file classification to select the appropriate reading strategy and produces normalized findings per wiki section. [2][3]
- A source traceability subdomain anchors every narrative claim to a precise codebase location and surfaces contradictions between sources. [4]
- An incremental content maintenance subdomain classifies section updates as unchanged, surgical, or rewrite based on a churn ratio derived from changes in the finding set. [5]
- A wiki persistence subdomain owns the authoritative on-disk layout, idempotent scaffolding, and all read/write operations for section bodies, extraction notes, configuration, and cache. [6]
- A knowledge presentation subdomain provides conversational Q&A over the generated wiki and coverage/quality reporting. [1]

## Sources
1. `wikifi/cli.py:1-11`
2. `wikifi/extractor.py:1-20`
3. `wikifi/specialized/dispatch.py:36-60`
4. `wikifi/evidence.py:1-18`
5. `wikifi/surgical.py:1-34`
6. `wikifi/wiki.py:1-55`

## From entities
# Core Entities

## Evidence Primitives

The traceability model is anchored by three small, composable entities.

**SourceRef** is the atomic pointer into the codebase: a repo-relative file path, an optional inclusive line range, and a short content fingerprint captured at extraction time. It renders as `path:start–end`, `path:line`, or bare `path` depending on available information.

**Claim** is one assertion placed into a wiki section. It pairs the markdown text of the assertion with a list of `SourceRef` objects that justify it. A claim that carries no source references is explicitly considered unsupported.

**Contradiction** captures two or more conflicting `Claim` objects about the same topic. It carries a one-sentence summary of the disagreement and, for each disagreeing position, the full `Claim` with its own source references.

At the aggregation stage, the LLM expresses the same concepts through index-based counterparts. An **AggregatedClaim** carries claim text plus a list of 1-based indices into the ordered input notes list. When an `AggregatedClaim` is resolved against the notes list, it converges with the `Claim` / `SourceRef` model.

An **EvidenceBundle** (defined in the evidence model) and a **SectionBody** (defined as the LLM's structured response schema) both represent the aggregator's complete output for one wiki section: a markdown narrative body, a list of claims, and a list of contradictions. `SectionBody` is the schema the LLM fills in during generation (claims are index-based); `EvidenceBundle` is the broader domain concept once indices have been resolved to `SourceRef` objects.

---

## Extraction Layer

| Entity | Key fields | Invariants / notes |
|---|---|---|
| **SectionFinding** | Target section ID, tech-agnostic markdown description (1–5 sentences), optional line range | One contribution from one file to one section |
| **FileFindings** | List of `SectionFinding` records, one-sentence file-role summary | Unit of output from one extractor call |
| **SpecializedFinding** | Target section ID, descriptive finding string, list of `SourceRef` objects | Produced by deterministic schema-aware extractors |
| **SpecializedResult** | List of `SpecializedFinding` records, optional summary | Mirrors the output shape of the LLM extractor |
| **ExtractionStats** | Files seen, files with findings, total findings, skipped files, chunks processed, cache hits, specialized-extractor files, file-kind breakdown | Run-level accumulators only; no identity |

Schema-aware extractors surface specialised sub-types of `SpecializedFinding`. GraphQL schema files yield five entity categories: named domain object types, interface contracts, input types (request-payload shapes), enum types (closed value sets), and root operation types. Protocol-buffer IDL files yield named protocol entities (from `message` declarations, grouped by package) and closed value sets (from `enum` declarations). SQL DDL files yield a richer internal record — a **_TableHit** — that adds the raw column-definition body, a parsed column list, and a list of foreign-key edges expressed as (local column, referenced table, referenced column) triples. API-contract files yield named request and response schemas from the component section, capped at 25 inline names.[14]

---

## Wiki Taxonomy

A **Section** is the unit of wiki organisation. Its fields are: a stable identifier, a human-readable title, a descriptive text, a tier classification (`primary` or `derivative`), and an ordered set of upstream section identifiers it depends on. The entity is immutable once created. The full set of sections forms a dependency graph governed by a hard topological invariant: derivative sections may only reference sections that appear earlier in the canonical sequence.

A **WikiLayout** is an immutable value object. It holds the project root path and derives every well-known filesystem path from it — wiki directory, config file, gitignore, notes directory, cache directory, and per-section markdown and notes files. It is the single source of truth for path resolution across all pipeline stages.

A **LoadedSection** pairs a `Section` descriptor with the markdown body read from disk. It is the unit of context fed into the chat system prompt.

---

## Cache Entities

Four typed cache scopes are unified into a single **WalkCache** object that is passed through the entire pipeline. It exposes typed lookup and record methods per scope and maintains hit/miss counters for each.

| Cache entity | Keyed by | Content |
|---|---|---|
| **CachedFindings** | Repo-relative file path | Content fingerprint, structured findings, file-role summary, chunk count |
| **CachedSection** | Hash of the notes that produced the section | Markdown body, structured claims, contradictions, ordered finding-ID list |
| **CachedDerivation** | Hash of upstream primary-section bodies | Rendered body, `reviewed` flag |
| **CachedIntrospection** | Include/exclude scope hash | Stage 1 introspection result |

Two invariants deserve emphasis. `CachedSection` stores an ordered list of stable finding identifiers aligned with note position so that 1-based claim source indices remain meaningful across sessions. `CachedDerivation` records whether the critic-and-reviser loop ran; a reviewed body is never silently substituted for an unreviewed one. `CachedIntrospection` deliberately excludes descriptive fields (primary languages, rationale) from its key hash, so model-run variation in those fields does not invalidate an otherwise valid scope result.

---

## Surgical Edit Entities

When the finding set changes only slightly, the pipeline performs an in-place update rather than a full rewrite.

**SectionChange** captures the diff result for one section: a decision value (`unchanged`, `surgical`, or `rewrite`), the 1-based indices of live findings absent from the cache, the cached finding IDs no longer in the live set, a count of unchanged findings, the total live count, and a churn ratio derived from those counts.

**SurgicalClaim** pairs an assertion text with 1-based indices into the added-findings list. **SurgicalContradiction** pairs a summary sentence with a list of `SurgicalClaim` objects representing disagreeing positions.

**SurgicalEdit** is the structured output of one surgical pass: an edited markdown body, the list of newly introduced `SurgicalClaim` records, a list of 1-based indices into the cached claims to drop, and a full replacement list of `SurgicalContradiction` records.

---

## Aggregation Output

**AggregationStats** tracks, across a single pipeline walk, how many sections were written fresh, left empty, served from cache, updated via surgical edit, or fully rewritten.

---

## Derivation

**DerivedSection** is the final markdown body produced for one derivative section. Its single invariant is that it contains no top-level heading; the wiki writer adds the heading separately.

**DerivationStats** accumulates, across one run, counts of derivative sections derived, skipped, revised by the critic loop, and served from cache, together with the list of individual review outcomes.

---

## Quality and Review

**Critique** captures the quality assessment of one section: an integer score (0–10), a one-to-two sentence summary judgment, a list of unsupported claims, a list of gaps against the section brief, and a list of concrete suggested edits.

**ReviewOutcome** records the full lifecycle of a section review: the section identifier, the initial `Critique`, the current body text, a boolean indicating whether a revision was accepted, and the follow-up `Critique` if revision occurred.

**WikiQualityReport** aggregates a whole-wiki scoring run: an overall numeric score, a map from section identifiers to their individual `Critique` objects, and optional coverage statistics.

**CoverageStats** records extraction coverage: total files seen, files that contributed findings, per-section counts of both findings and contributing files, and a coverage percentage derived from those counts.

---

## Reporting

**SectionReport** is a read-only per-section summary: contributing file count, finding count, body character length, an empty flag, and an optional quality `Critique`.

**WikiReport** aggregates coverage statistics across all sections, the list of `SectionReport` records, and an optional overall quality score computed as the mean of all scored sections.

---

## Pipeline Orchestration

**IntrospectionResult** is the output of Stage 1: include patterns, exclude patterns, primary languages, a likely-purpose paragraph, and a rationale string. Patterns are gitignore-style and relative to the repository root.

**WalkConfig** is an immutable record governing one filesystem enumeration: root directory, supplemental exclude patterns, a flag to respect the project's own ignore file, maximum file size, and minimum stripped-content size.

**DirSummary** holds non-recursive aggregate statistics for one directory: repo-relative path, file count, total byte size, a top-10 map of file extensions to counts, and a list of notable manifest or readme filenames. It is produced in pre-order depth-first traversal.

**WalkReport** is the top-level result for a complete pipeline run. It carries the `IntrospectionResult`, extraction statistics, aggregation statistics, derivation statistics, the `WalkCache` snapshot, the repo import graph, and a boolean indicating whether the run was a full cache hit with no generation work performed.

---

## Repository Graph

**GraphNode** represents one in-scope file: its repo-relative path, the tuple of files it imports, the tuple of files that import it, and a capped combined-neighbor accessor used for prompt enrichment.

**RepoGraph** is the aggregate of all `GraphNode` records for the in-scope file set. It supports lookup by path and neighbor-path retrieval with a configurable cap.

---

## Provider and Chat Entities

**ChatMessage** is one turn in a conversation: a role identifier and a content string.

**LLMProvider** is the abstract contract every generation backend must satisfy. It carries a provider name and a model identifier and must implement three call surfaces: structured extraction (schema-constrained, returns a validated document), free-text generation, and multi-turn conversation.

**ChatSession** holds a reference to the configured provider, the frozen system prompt built from wiki content, and the growing message history for the current session. It exposes two operations: *send* (appends the user turn, calls the provider, appends the reply) and *reset* (clears history while keeping the system context).

---

## Settings

**Settings** is the single runtime configuration entity. Its fields span: LLM provider identity and model identifier, Ollama endpoint URL, per-request timeout, file-size thresholds (maximum, chunk, overlap, minimum content), introspection tree depth, thinking-mode level, pipeline feature flags (caching, graph analysis, specialized extractors, critic loop, surgical edits), surgical-edit churn threshold, and provider-specific API keys, base URLs, and token caps.

## Supporting claims
- A SourceRef points to a specific location in the codebase: a repo-relative file path, an optional inclusive line range, and a short content fingerprint captured at extraction time. [1]
- A Claim pairs the markdown text of an assertion with a list of SourceRef objects that justify it; a claim carrying no source references is explicitly considered unsupported. [2]
- A Contradiction captures two or more conflicting Claim objects about the same topic, with a one-sentence summary and each disagreeing position retaining its own source references. [3]
- An AggregatedClaim carries claim text plus a list of 1-based indices into the ordered input notes list. [4]
- EvidenceBundle and SectionBody both represent the aggregator's complete output for one wiki section: a markdown narrative body, claims, and contradictions. [5][6]
- A SectionFinding carries the target section identifier, a technology-agnostic markdown description of 1–5 sentences, and an optional line range within the source chunk. [7]
- FileFindings groups all findings produced for a single file together with a one-sentence file-role summary; it is the unit of output from one extractor call. [8]
- A SpecializedFinding carries a target section identifier, a descriptive finding string, and a list of source references linking back to originating file locations. [9]
- A SpecializedResult aggregates a list of SpecializedFindings together with an optional summary string, mirroring the output shape of the LLM extractor. [9]
- ExtractionStats accumulates run-level counters: files seen, files with findings, total findings, skipped files, chunks processed, cache hits, specialized-extractor files, and a file-kind breakdown. [10]
- GraphQL schema files yield five entity categories: named domain object types, interface contracts, input types, enum types, and root operation types. [11]
- Protocol-buffer IDL files yield named protocol entities from message declarations (grouped by package) and closed value sets from enum declarations. [12]
- SQL DDL files yield a _TableHit internal record with table name, source line, raw column-definition body, parsed column names, and foreign-key edges as (local column, referenced table, referenced column) triples. [13]
- A Section carries an identifier, title, description, tier classification (primary or derivative), and ordered upstream dependencies; it is immutable and participates in a topologically ordered dependency graph where derivatives may only reference earlier sections. [15]
- WikiLayout is an immutable value object that holds the project root and derives all well-known filesystem paths from it; it is the single source of truth for path resolution. [16]
- A LoadedSection pairs a Section descriptor with the markdown body read from disk and is the unit of context fed into the chat system prompt. [17]
- WalkCache is the unified in-memory view of all four cache scopes plus hit/miss counters for each; it is the single cache object passed through the pipeline. [18]
- CachedFindings is keyed by repo-relative file path and holds the content fingerprint, structured findings, file-role summary, and chunk count. [19]
- CachedSection holds the notes hash, rendered markdown body, structured claims, contradictions, and an ordered list of stable finding identifiers so that 1-based claim source indices map to finding IDs across sessions. [20]
- CachedDerivation holds the hash of upstream primary-section bodies, the rendered body, and a flag recording whether the critic-and-reviser review loop ran, preventing a reviewed body from being silently substituted for an unreviewed one. [21]
- CachedIntrospection deliberately excludes descriptive fields (primary languages, rationale) from its key hash so model-run variation does not invalidate an otherwise valid scope result. [22]
- SectionChange captures a per-section diff: a decision (unchanged/surgical/rewrite), new finding indices, dropped finding IDs, unchanged count, total live count, and a derived churn ratio. [23]
- A SurgicalClaim pairs assertion text with 1-based indices into the added-findings list; a SurgicalContradiction pairs a summary sentence with a list of SurgicalClaims. [24]
- SurgicalEdit is the structured output of one surgical pass: an edited markdown body, newly introduced claims, 1-based indices of cached claims to drop, and a full replacement list of contradictions. [25]
- AggregationStats tracks how many sections were written, left empty, served from cache, surgically edited, or fully rewritten in a single walk. [5]
- DerivedSection holds the final markdown body for one derivative section with the invariant that it contains no top-level heading. [26]
- DerivationStats counts derivative sections derived, skipped, revised by the critic loop, and served from cache, plus the list of review outcomes. [27]
- Critique captures an integer score (0–10), a one-to-two sentence summary judgment, unsupported claims, gaps against the section brief, and concrete suggested edits. [28]
- ReviewOutcome records the section identifier, initial critique, current body text, revision-accepted flag, and the follow-up critique if revision occurred. [29]
- WikiQualityReport aggregates an overall numeric score, a map from section identifiers to individual critiques, and optional coverage statistics. [30]
- CoverageStats records total files seen, files with findings, per-section counts of findings and contributing files, and a coverage percentage. [31]
- SectionReport is a read-only per-section summary: contributing file count, finding count, body character length, empty flag, and optional quality critique. [32]
- WikiReport aggregates coverage statistics, the list of SectionReport records, and an optional overall quality score computed as the mean of all scored sections. [33]
- IntrospectionResult captures Stage 1 output: include patterns, exclude patterns, primary languages, a purpose paragraph, and a rationale string; patterns are gitignore-style and relative to the repository root. [34]
- WalkConfig is an immutable record capturing: root directory, supplemental exclude patterns, ignore-file flag, maximum file size, and minimum stripped-content size. [35]
- DirSummary holds non-recursive aggregate statistics for one directory: repo-relative path, file count, total byte size, a top-10 extension-to-count map, and notable manifest/readme filenames; it is produced in pre-order depth-first traversal. [36]
- WalkReport is the top-level result for a pipeline run, carrying introspection result, extraction stats, aggregation stats, derivation stats, walk cache snapshot, repo import graph, and a full-cache-hit flag. [37]
- GraphNode carries a file's repo-relative path, the tuple of files it imports, the tuple of files that import it, and a capped combined-neighbor accessor. [38]
- RepoGraph aggregates all GraphNode records for the in-scope file set and supports lookup by path and neighbor-path retrieval with a configurable cap. [39]
- ChatMessage carries a role identifier and a content string. [40]
- LLMProvider carries a provider name and model identifier and must implement structured extraction, free-text generation, and multi-turn conversation call surfaces. [40]
- ChatSession holds a reference to the configured provider, the frozen system prompt, and the growing message history; it exposes send and reset operations. [41]
- Settings captures LLM provider identity, model identifier, endpoint URL, timeout, file-size thresholds, introspection tree depth, thinking-mode level, pipeline feature flags, surgical-edit churn threshold, and provider-specific API keys, base URLs, and token caps. [42]

## Sources
1. `wikifi/evidence.py:35-57`
2. `wikifi/evidence.py:60-70`
3. `wikifi/evidence.py:73-79`
4. `wikifi/aggregator.py:76-97`
5. `wikifi/aggregator.py:100-115`
6. `wikifi/evidence.py:82-87`
7. `wikifi/extractor.py:97-107`
8. `wikifi/extractor.py:110-113`
9. `wikifi/specialized/models.py:17-27`
10. `wikifi/extractor.py:116-124`
11. `wikifi/specialized/graphql.py:44-93`
12. `wikifi/specialized/protobuf.py:43-64`
13. `wikifi/specialized/sql.py:48-55`
14. `wikifi/specialized/openapi.py:98-110`
15. `wikifi/sections.py:31-38`
16. `wikifi/wiki.py:54-76`
17. `wikifi/chat.py:42-44`
18. `wikifi/cache.py:146-166`
19. `wikifi/cache.py:89-96`
20. `wikifi/cache.py:98-116`
21. `wikifi/cache.py:118-131`
22. `wikifi/cache.py:133-143`
23. `wikifi/surgical.py:127-150`
24. `wikifi/surgical.py:72-92`
25. `wikifi/surgical.py:95-120`
26. `wikifi/deriver.py:58-62`
27. `wikifi/deriver.py:64-71`
28. `wikifi/critic.py:63-78`
29. `wikifi/critic.py:85-90`
30. `wikifi/critic.py:93-96`
31. `wikifi/critic.py:216-232`
32. `wikifi/report.py:29-36`
33. `wikifi/report.py:39-41`
34. `wikifi/introspection.py:43-62`
35. `wikifi/walker.py:57-74`
36. `wikifi/walker.py:148-157`
37. `wikifi/orchestrator.py:76-91`
38. `wikifi/repograph.py:151-170`
39. `wikifi/repograph.py:172-183`
40. `wikifi/providers/base.py:31-57`
41. `wikifi/chat.py:46-58`
42. `wikifi/config.py:44-181`

## From integrations
# Integrations

## External Integrations

### Outbound: Language-Model Providers

All communication with external or locally-hosted language models is routed through a single shared provider abstraction that declares three call surfaces: schema-validated structured output, unstructured free-text completion, and stateful multi-turn conversation. Every pipeline stage that needs inference (extraction, aggregation, derivation, quality critique, surgical editing, and the chat REPL) calls exclusively through this interface rather than directly into any particular backend.

Three concrete provider backends are available and are selected at runtime via configuration:

| Backend | Activation | Destination |
|---|---|---|
| Hosted (large-model API) | Default or explicit flag | External hosted inference API |
| Alternative hosted | Provider selector | Separate external hosted API |
| Local | Provider selector | Locally-running inference service |

All three backends normalize API errors into uniform runtime errors before surfacing them, so the rest of the pipeline can apply a single fallback strategy regardless of which provider is active. The hosted backends additionally support features such as prompt caching and adaptive reasoning modes to make large-scale codebase walks economically viable.

### Inbound: CLI Entry Point

The command-line interface is the sole external entry point for human operators. It exposes four sub-commands and delegates entirely to internal modules — it contains no domain logic of its own. Configuration is resolved from up to three sources in strict precedence order: a per-target config file stored inside the target repository's own wiki directory, process-level environment variables (including a `.env` file), and built-in field defaults. The per-target config wins, so each analysed repository can drive its own pipeline settings.

---

## Internal Integration Topology

### Orchestrator as Central Hub

The orchestrator is the primary internal integration point. It sequences five subsystems in order:

1. **Repository introspection** — classifies the directory tree and decides which paths are worth analysing.
2. **Extraction** — walks each included file, calling the provider for structured findings or delegating to deterministic specialized extractors.
3. **Aggregation** — synthesizes per-file notes into coherent, citation-backed section bodies.
4. **Derivation** — generates derivative content (personas, user stories, diagrams) from the finished primary sections.
5. **Cache layer** — consulted and updated at every stage to avoid redundant work.

### On-Disk State via the Wiki Layout

All read and write access to wiki artifacts — section markdown files, per-section extraction note stores (JSONL), and related paths — flows through a single canonical layout abstraction. The extraction, aggregation, caching, orchestration, derivation, chat, and CLI modules all resolve their file paths through this shared type, making it the de facto integration bus for persistent state between pipeline stages.

### Cache and Fingerprint Subsystems

The cache module is consumed by the orchestrator, extractor, aggregator, and deriver to check and record results. It delegates all content hashing to a dedicated fingerprinting subsystem (stable short-form SHA-256 prefixes). The fingerprinting subsystem is also used independently by the evidence citation layer (pairing source paths with fingerprints and line ranges) and by the dependency graph subsystem (propagating cache invalidation across files that import one another).

### Extraction Stage

The extractor calls the language-model provider once per file chunk for unstructured source files and writes results to the notes store via an `append_note` interface consumed downstream by the aggregator. For structured file kinds (relational schema, API contract, service definition, graph schema, and migration files), it delegates to a dispatch layer that selects a deterministic specialized extractor and bypasses the model entirely. The dispatch layer in turn depends on the file classifier from the repository analysis module.

The repository analysis module also builds an import/reference graph. The orchestrator uses this graph to inject neighbor-file context into each extraction prompt.

### Aggregation and Surgical Editing

The aggregator coordinates with three internal subsystems: the cache (to determine whether a full rewrite or a surgical patch is needed), the surgical editor (which sits between the cache and the rendering layer for small deltas, calling the provider for targeted JSON-output edits), and the evidence renderer (which formats citation footers and conflict blocks from structured claim data).

### Quality Reporting and Critic

The report module reads section markdown and notes files from disk via the wiki layout, reads the walk cache to determine total files processed, and optionally calls the critic subsystem to score section bodies. For derivative sections, the report also collects upstream section text to give the critic the context needed to evaluate how well the derivative synthesizes its sources. The critic and reviser themselves call the shared provider abstraction with structured schemas, keeping the quality pipeline independent of the active model.

### Chat REPL

The interactive chat feature has two integration dependencies: it reads all populated section files from disk via the wiki layout to assemble a grounding context, and it delegates each user turn to the configured provider through the shared interface, passing the full message history on every call.

### Walker

The filesystem walker is called by the introspection stage (to produce a compressed structural summary) and by the orchestrator/extractor stages (to supply the actual file list). It has no outbound integrations beyond the local filesystem and applies gitignore semantics plus hardcoded exclusion rules before any model pass runs.

---

## Integration Surfaces Detected in Analysed Codebases

When the system analyses a target codebase, several specialized extractors surface integration touchpoints in the target's own code:

- **Service definition files** — each declared service and its remote-procedure calls are recorded as integration touchpoints, including input/output message types and streaming direction per operation.
- **API contract files** — the total number of endpoints exposed to external HTTP consumers is recorded, characterising the inbound HTTP integration surface.
- **Graph schema files** — subscription roots are classified as integration touchpoints (event-driven outbound signals or real-time feeds) rather than as capabilities.
- **Relational schema files** — foreign-key references between tables are emitted as directed relational links, recording the exact columns that form each join.

## Supporting claims
- All communication with language models is routed through a single shared provider abstraction that declares three call surfaces: schema-validated structured output, unstructured free-text completion, and stateful multi-turn conversation. [1]
- Every pipeline stage that needs inference (extraction, aggregation, derivation, quality critique, surgical editing, and the chat REPL) calls exclusively through this interface. [2][3][4][5][6][1]
- Three concrete provider backends are available: two externally hosted and one local, selected at runtime via configuration. [7][8][9]
- All three backends normalize API errors into uniform runtime errors before surfacing them. [7][9]
- The command-line interface is the sole external entry point and delegates entirely to internal modules, containing no domain logic of its own. [10]
- Configuration is resolved from up to three sources in strict precedence order: a per-target config file, process-level environment variables, and built-in field defaults, with the per-target config winning. [11]
- The orchestrator sequences five internal subsystems: introspection, extraction, aggregation, derivation, and the cache layer. [12]
- All read and write access to wiki artifacts flows through a single canonical wiki layout abstraction shared by extraction, aggregation, caching, orchestration, derivation, chat, and CLI modules. [13]
- The cache module is consumed by the orchestrator, extractor, aggregator, and deriver, and delegates all content hashing to a dedicated fingerprinting subsystem. [14][15]
- The fingerprinting subsystem is also used by the evidence citation layer and the dependency graph subsystem. [15]
- For structured file kinds, the extractor delegates to a deterministic dispatch layer that bypasses the language model entirely. [16][17]
- The dispatch layer depends on the file classifier from the repository analysis module. [18][17]
- The repository analysis module builds an import/reference graph used by the orchestrator to inject neighbor-file context into extraction prompts. [18]
- Completed extraction results are written to a notes store (one JSONL file per section) via an append_note interface consumed downstream by the aggregator. [19]
- The aggregator coordinates with the cache, the surgical editor, and the evidence renderer as internal subsystems. [2]
- The surgical editor sits between the cache and the rendering layer for small deltas, calling the provider for targeted structured edits. [6][20]
- The report module reads section files and notes from disk, reads the walk cache for total file counts, and optionally calls the critic to score section bodies. [21]
- For derivative sections, the report collects upstream section text to give the critic context-aware scoring capability. [22]
- The chat REPL reads all populated section files from disk via the wiki layout and delegates each user turn to the configured provider with the full message history. [23][3]
- The filesystem walker is called by the introspection stage and by the orchestrator/extractor stages, and has no outbound integrations beyond the local filesystem. [24]
- Service definition files surface each declared service and its remote-procedure calls as integration touchpoints, including input/output message types and streaming direction per operation. [25]
- API contract files surface the total number of endpoints exposed to external HTTP consumers as an inbound integration surface finding. [26]
- Graph schema subscription roots are classified as integration touchpoints rather than capabilities, reflecting their event-driven nature. [27]
- Relational schema foreign-key references are emitted as directed relational links recording the exact columns that form each join. [28]

## Sources
1. `wikifi/providers/base.py:37-57`
2. `wikifi/aggregator.py:118-210`
3. `wikifi/chat.py:50-55`
4. `wikifi/critic.py:27-29`
5. `wikifi/extractor.py:228-241`
6. `wikifi/surgical.py:196-220`
7. `wikifi/providers/anthropic_provider.py:117-145`
8. `wikifi/providers/ollama_provider.py:43-100`
9. `wikifi/providers/openai_provider.py:1-20`
10. `wikifi/cli.py:21-29`
11. `wikifi/config.py:1-26`
12. `wikifi/orchestrator.py:57-240`
13. `wikifi/wiki.py:54-76`
14. `wikifi/cache.py`
15. `wikifi/fingerprint.py:1-17`
16. `wikifi/extractor.py:216-235`
17. `wikifi/specialized/dispatch.py:18-60`
18. `wikifi/repograph.py:1-16`
19. `wikifi/extractor.py:265-268`
20. `wikifi/surgical.py:196-234`
21. `wikifi/report.py:72-130`
22. `wikifi/report.py:153-163`
23. `wikifi/chat.py:62-82`
24. `wikifi/walker.py:1-11`
25. `wikifi/specialized/protobuf.py:66-97`
26. `wikifi/specialized/openapi.py:90-96`
27. `wikifi/specialized/graphql.py:103-106`
28. `wikifi/specialized/sql.py:87-98`
