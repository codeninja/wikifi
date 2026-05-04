# Core Entities

The system's information model spans six concern areas: wiki structure, evidence tracing, extraction and aggregation, repository analysis, caching, and pipeline orchestration. The entities below are described domain-first; implementation details such as storage format are noted only where they affect the entity's invariants.

---

## Wiki Structure

A **Section** is the fundamental organisational unit of the generated wiki. It carries:

| Field | Description |
|---|---|
| Unique identifier | Stable key used throughout the pipeline |
| Title | Human-readable heading |
| Brief | Prose description of what belongs in the section |
| Tier | Either *primary* (populated from per-file evidence) or *derivative* (synthesised from primary sections) |
| Upstream list | Ordered tuple of section identifiers this section depends on (derivative sections only) |

Derivative sections declare explicit upstream dependencies, forming a directed acyclic graph. The system enforces topological ordering at startup: every section's upstreams must appear earlier in the canonical section list.

A **WikiLayout** anchors all on-disk path resolution to a single project root, exposing named locations for the wiki directory, configuration file, gitignore, notes directory, cache directory, and per-section markdown and notes files. Its existence is a precondition for the conversational query and report commands.

A **LoadedSection** pairs a Section descriptor with its rendered markdown body, representing one populated section ready for downstream use (such as building a conversational context).

A **SectionReport** captures the per-section view for reporting: a reference to the Section definition, the count of contributing files, the count of findings, the character length of the written body, an emptiness flag, and an optional quality critique. A **WikiReport** aggregates all SectionReports together with overall coverage statistics and an optional mean quality score across populated sections.

---

## Evidence and Citation Model

Every factual sentence in the generated wiki is traceable back through a three-layer evidence hierarchy.

**SourceRef** — the lowest-level pointer. Carries a repo-relative file path, an optional inclusive line range, and a short content fingerprint captured at extraction time. Renders as `path:start–end` or just `path` when no line range is available.

**Claim** — a single markdown assertion placed in a section's narrative. Backed by zero or more SourceRefs. A claim with no sources is explicitly considered *unsupported*.

**Contradiction** — groups two or more conflicting Claims under a one-sentence summary of the conflict; each conflicting position retains its own SourceRefs.

**EvidenceBundle** — the aggregator's structured handoff to the renderer for one section: the markdown narrative body, the ordered list of Claims, and the list of Contradictions.

During the language-model aggregation pass, an intermediate form is used: an **AggregatedClaim** pairs a prose assertion with 1-based indices into the input notes (rather than resolved file paths), and an **AggregatedContradiction** wraps a one-sentence summary around multiple such indexed positions. These are resolved into full SourceRefs and Claims before the EvidenceBundle is assembled.

---

## Extraction Layer

**IntrospectionResult** captures the Stage 1 decision: include patterns, exclude patterns, a one-paragraph hypothesis about the system's purpose, an informational list of primary technologies detected, and the rationale for the filtering choices.

**SectionFinding** is the atomic extraction unit from one source file for one section. Fields:
- Target section identifier
- Technology-agnostic markdown description (one to five sentences)
- Optional inclusive line range within the source chunk

**FileFindings** groups all SectionFindings produced for a single file, together with a one-sentence summary of that file's role. It is the unit exchanged between an extraction call and the notes store.

Specialised extractors — handling schema definition languages, API contracts, and data-definition files — produce **SpecializedFindings** rather than relying on general LLM inference. Each carries a section identifier, finding text, and one or more source references. Multiple SpecializedFindings are collected into a **SpecializedResult**, which additionally carries an optional summary string.

For data-definition schema files, an intermediate **table record** is derived first (table name, source line, raw body, column list, and foreign-key edges expressed as local-column → referenced-table.referenced-column tuples). All downstream entity and relationship findings are derived from this intermediate form.

Domain object types from API schema files (those that are not root operation types) are surfaced directly as domain entity findings, grouped by their namespace, with closed value sets (enumerations) and shared shape contracts (interfaces, input types) captured as separate finding categories.

**ExtractionStats** accumulates per-run metrics: files seen, files with findings, total findings, skipped files, chunks processed, cache hits, files routed to specialised extractors, and a breakdown by file kind.

---

## Repository Analysis Entities

**FileKind** is a fixed enumeration of seven structural categories: application code, SQL, OpenAPI contract, protocol definition, GraphQL schema, migration script, and other. The classification drives routing to the appropriate extractor.

**GraphNode** represents one file's position in the cross-file import graph: its repo-relative path, the ordered set of files it imports, and the ordered set of files that import it. It exposes a combined neighbour list capped at a configurable limit for use in prompt enrichment.

**RepoGraph** is the complete repository-level import graph, keyed by repo-relative file path, providing lookup of individual GraphNodes and neighbour path lists.

**DirSummary** is a value object for a single non-recursive directory: its repo-relative path, file count, total byte size, a frequency map of the top-10 file extensions, and a tuple of notable filenames (manifests, readmes).

---

## Caching Entities

| Entity | Cache key | Stored payload |
|---|---|---|
| **CachedFindings** | Content fingerprint of the source file | Findings list, one-sentence file summary, chunk count |
| **CachedSection** | Hash of the notes payload | Rendered markdown body, claims list, contradictions list |

**WalkCache** is the in-memory aggregate of both caches. It tracks four counters — extraction hits, extraction misses, aggregation hits, aggregation misses — supporting efficiency reporting across a full pipeline run.

---

## Quality-Review Entities

A **Critique** captures the quality assessment of one section:
- Integer score (0–10)
- Short overall judgment
- List of unsupported claims
- List of gaps relative to the section brief
- List of concrete revision suggestions

A **ReviewOutcome** tracks the lifecycle of a single section review: the section identifier, the initial Critique, the current body text, a boolean flag indicating whether a revision was applied, and an optional follow-up Critique produced after revision.

A **WikiQualityReport** aggregates the full-wiki audit: an overall numeric score, a mapping from section identifiers to individual Critiques, and optional **CoverageStats** (total files, files with findings, and per-section finding and file counts).

---

## Pipeline Orchestration Entities

**WalkConfig** encapsulates the parameters for file traversal. Notes from two different pipeline layers describe it somewhat differently (see Conflicts below), but the agreed-upon core fields are: repository root, file-size limits, minimum content thresholds, and extra exclusion patterns. It is treated as immutable once constructed.

**Notes records** are the ephemeral per-section extraction state persisted during a walk. Each record carries a UTC timestamp and arbitrary key-value metadata. Records for a section are accumulated in insertion order.

**WalkReport** is the primary return value from a complete pipeline run. It carries the IntrospectionResult, ExtractionStats, AggregationStats, DerivationStats, the WalkCache state, and the RepoGraph.

**AggregationStats** tracks three counters for a single aggregation pass: sections written fresh, sections skipped due to empty notes, and sections served from cache.

**DerivationStats** accumulates pipeline metrics for the derivation stage: count of sections derived, skipped, and revised, plus the full list of ReviewOutcomes as an audit trail.

---

## Interaction Entities

A **ChatMessage** carries a role identifier and a content string, representing one turn in a multi-turn exchange.

A **ChatSession** holds a reference to the language-model provider, the frozen system prompt built from populated wiki sections, and the accumulated conversation history (an ordered list of ChatMessages). It supports appending user and assistant turns and clearing the history while retaining the wiki context.

---

## Configuration and Provider Entities

**Settings** captures all runtime knobs for a wiki-generation run: provider and model identity, inference endpoint, request timeout, file-size and chunk thresholds, pipeline feature flags (caching, graph building, specialised extractors, review loop), the quality threshold that triggers revision, and provider-specific credentials and token caps.

An **LLMProvider** carries a provider name and a specific model variant. It is the sole point of contact between the pipeline and any language-model backend, exposing exactly three interaction modes used throughout the system.

## Supporting claims
- A Section carries a unique identifier, human-readable title, prose brief, a tier (primary or derivative), and an ordered tuple of upstream section identifiers. [1]
- Derivative sections declare explicit upstream dependencies forming a directed acyclic graph enforced by topological ordering at startup. [2][1]
- WikiLayout anchors all on-disk path resolution to a single project root, exposing named locations for wiki, config, gitignore, notes, cache, and per-section files; its existence is a precondition for the chat and report commands. [3][4]
- A LoadedSection pairs a Section descriptor with its rendered markdown body. [5]
- A SectionReport carries the section definition reference, contributing file count, findings count, body character length, emptiness flag, and an optional quality critique. [6]
- A WikiReport aggregates all SectionReports, overall coverage statistics, and an optional mean quality score. [7]
- A SourceRef holds a repo-relative file path, an optional inclusive line range, and a short content fingerprint captured at extraction time. [8][9]
- A Claim is a single markdown assertion backed by zero or more SourceRefs; a claim with no sources is explicitly considered unsupported. [8][10]
- A Contradiction groups two or more conflicting Claims under a one-sentence summary, each position retaining its own SourceRefs. [10]
- An EvidenceBundle is the aggregator's structured handoff to the renderer: markdown body, ordered Claims list, and Contradictions list. [8][11]
- During the aggregation pass an AggregatedClaim pairs a prose assertion with 1-based input-note indices, and an AggregatedContradiction wraps a one-sentence summary around multiple such indexed positions; these are resolved into SourceRefs before the EvidenceBundle is assembled. [12]
- IntrospectionResult captures include/exclude patterns, a purpose hypothesis, an informational language list, and the filtering rationale. [13]
- A SectionFinding carries a target section identifier, a technology-agnostic markdown description of one to five sentences, and an optional line range. [14]
- A FileFindings groups all SectionFindings for one file plus a one-sentence file-role summary, and is the unit exchanged between the extraction call and the notes store. [15]
- A SpecializedFinding carries a section identifier, finding text, and one or more source references; multiple SpecializedFindings are collected into a SpecializedResult that also carries an optional summary string. [16][17]
- For data-definition schema files an intermediate table record is derived first (name, source line, raw body, column list, and foreign-key edges) and all downstream findings are derived from it. [18]
- Domain object types from schema files are surfaced as domain entity findings; closed value sets and shared shape contracts are captured as separate finding categories; a maximum of 25 items per category are rendered with elision noted. [19][20][21]
- ExtractionStats accumulates: files seen, files with findings, total findings, skipped files, chunks processed, cache hits, specialised-extractor files, and a file-kind breakdown. [22]
- FileKind is a fixed enumeration of seven structural categories: application code, SQL, OpenAPI, Protobuf, GraphQL, migration, and other; it drives routing to the appropriate extractor. [23]
- A GraphNode carries its repo-relative path, the ordered set of files it imports, and the ordered set of files that import it, with a configurable cap on the combined neighbour list. [24]
- A RepoGraph is the complete repository import graph keyed by repo-relative path. [25]
- A DirSummary holds a directory's path, file count, total byte size, top-10 extension frequency map, and a tuple of notable filenames. [26]
- CachedFindings stores a content fingerprint, findings list, one-sentence summary, and chunk count; CachedSection stores a notes-payload hash, rendered markdown body, claims list, and contradictions list. [27][28]
- WalkCache aggregates both caches and tracks four counters (extraction hits/misses, aggregation hits/misses) for efficiency reporting. [29]
- A Critique carries an integer score (0–10), a short judgment, a list of unsupported claims, a list of brief gaps, and a list of revision suggestions. [30]
- A ReviewOutcome tracks the section identifier, initial critique, current body, revision-applied flag, and optional follow-up critique. [31]
- A WikiQualityReport carries an overall numeric score, a mapping from section identifiers to individual Critiques, and optional CoverageStats (total files, files with findings, per-section finding and file counts). [32]
- WalkReport is the primary return value from a full pipeline run, carrying IntrospectionResult, ExtractionStats, AggregationStats, DerivationStats, WalkCache state, and RepoGraph. [33]
- AggregationStats tracks sections written fresh, skipped due to empty notes, and served from cache. [34]
- DerivationStats accumulates sections derived, skipped, and revised counts, plus the full list of ReviewOutcomes. [35]
- Notes records carry a UTC timestamp and arbitrary key-value metadata, stored per section in insertion order. [36]
- A ChatMessage carries a role identifier and a content string representing one turn in a multi-turn exchange. [37]
- A ChatSession holds an LLM provider reference, a frozen system prompt built from wiki sections, and an ordered conversation history; it supports appending turns and clearing history while retaining context. [38]
- Settings captures provider and model identity, inference endpoint, timeout, file-size and chunk thresholds, pipeline feature flags, revision quality threshold, and provider-specific credentials and token caps. [39]
- An LLMProvider carries a provider name and model variant and is the sole point of contact between the pipeline and any language-model backend. [37]

## Conflicts in source
_The walker found disagreements across files. Migration teams should resolve these before re-implementation._

- **Two sources describe a 'WalkConfig' entity with partially different field sets, suggesting either two distinct same-named entities at different pipeline layers or a single entity incompletely described in each source.**
  - WalkConfig (orchestrator layer) encapsulates repository root, byte-size limits, minimum content thresholds, and an optional introspection-derived exclusion list; it is constructed twice per run — once before introspection and once after with the exclusion list populated. (`wikifi/orchestrator.py:83-101`)
  - WalkConfig (filesystem-walker layer) encapsulates repository root, extra exclusion patterns beyond defaults, a flag for honouring gitignore rules, maximum file size in bytes, and minimum stripped-content size in bytes; it is immutable once constructed. (`wikifi/walker.py:61-79`)

## Sources
1. `wikifi/sections.py:30-40`
2. `wikifi/deriver.py:112-116`
3. `wikifi/cli.py:172-183`
4. `wikifi/wiki.py:55-80`
5. `wikifi/chat.py:42-45`
6. `wikifi/report.py:29-36`
7. `wikifi/report.py:39-44`
8. `wikifi/aggregator.py:166-186`
9. `wikifi/evidence.py:35-55`
10. `wikifi/evidence.py:57-80`
11. `wikifi/evidence.py:82-87`
12. `wikifi/aggregator.py:74-101`
13. `wikifi/introspection.py:47-64`
14. `wikifi/extractor.py:113-125`
15. `wikifi/extractor.py:128-131`
16. `wikifi/specialized/models.py:19-22`
17. `wikifi/specialized/models.py:25-27`
18. `wikifi/specialized/sql.py:50-58`
19. `wikifi/specialized/graphql.py:56-95`
20. `wikifi/specialized/openapi.py:105-116`
21. `wikifi/specialized/protobuf.py:42-60`
22. `wikifi/extractor.py:134-142`
23. `wikifi/repograph.py:43-56`
24. `wikifi/repograph.py:143-162`
25. `wikifi/repograph.py:165-177`
26. `wikifi/walker.py:144-153`
27. `wikifi/cache.py:60-66`
28. `wikifi/cache.py:69-74`
29. `wikifi/cache.py:77-88`
30. `wikifi/critic.py:67-84`
31. `wikifi/critic.py:91-96`
32. `wikifi/critic.py:99-114`
33. `wikifi/orchestrator.py:60-70`
34. `wikifi/aggregator.py:103-107`
35. `wikifi/deriver.py:57-62`
36. `wikifi/wiki.py:136-152`
37. `wikifi/providers/base.py:33-52`
38. `wikifi/chat.py:46-57`
39. `wikifi/config.py:46-155`
40. `wikifi/orchestrator.py:83-101`
41. `wikifi/walker.py:61-79`
