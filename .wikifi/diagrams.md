# Diagrams

_Derivation failed for **Diagrams** (anthropic provider: empty parsed_output and parse fallback failed: 1 validation error for DerivedSection
  Invalid JSON: EOF while parsing a value at line 1 column 0 [type=json_invalid, input_value='', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/json_invalid). Upstream evidence preserved below._

> Brief: Mermaid diagrams that visualize structural and behavioral relationships across the system: a domain map (graph or classDiagram across domains), an entity relationship view (erDiagram across entities), and an integration flow (sequence or flowchart across integrations). Tech-agnostic — no reference to current stack.


## From domains
# Domains and Subdomains

## Core Domain

The system's core domain is **codebase knowledge extraction**: ingesting an existing source base, classifying its contents, deriving domain findings from individual files, and synthesising those findings into a structured, technology-agnostic wiki. The primary consumers are migration teams who need to understand business intent, domain structure, and operational behaviour before re-implementing or replacing a legacy system.

## Subdomains

### Repository Introspection
This subdomain concerns discovering and classifying the files that make up a target codebase. Its central responsibility is distinguishing production source that encodes business intent from infrastructure, tooling, and other artefacts that do not. Tech-agnosticism is a first-class constraint here: the classification logic must not rely on recognising any specific language, framework, or runtime.

### Per-File Knowledge Extraction
Once relevant files are identified, each is analysed independently to surface domain findings. This subdomain covers the full extraction loop — examining file content, applying domain heuristics, and producing structured evidence — and forms the first phase of wiki generation (primary sections).

### Section Synthesis and Aggregation
The second phase of wiki generation operates over the evidence produced by per-file extraction. It aggregates findings across files into coherent wiki sections, derives higher-level content that cannot be inferred from any single file, and enforces the dependency ordering between primary (evidence-driven) and derivative (aggregated) sections. This ordering is a structural design constraint, not merely a runtime convention.

### Wiki Authoring and Organisation
A secondary domain governs how extracted knowledge is structured and stored. It defines the taxonomy of sections, distinguishes primary from derivative content, and produces output that a migration team can navigate and consume independently of the source codebase.

### Interactive Knowledge Retrieval
A supporting subdomain exposes the generated wiki to conversational or query-driven access, allowing stakeholders to interrogate extracted knowledge without directly inspecting raw wiki files.

## Cross-Cutting Constraint: Tech-Agnosticism
Tech-agnosticism spans every subdomain. All analysis, extraction, and synthesis must produce domain-level descriptions that are free of references to specific languages, frameworks, or libraries. This constraint is enforced at both the classification stage (repository introspection) and the output stage (section content).

## Subdomain Relationships

| Subdomain | Role | Depends On |
|---|---|---|
| Repository Introspection | Identifies source worth analysing | — |
| Per-File Knowledge Extraction | Produces primary section evidence | Introspection |
| Section Synthesis & Aggregation | Produces derivative sections | Per-File Extraction |
| Wiki Authoring & Organisation | Structures and stores the wiki | Synthesis |
| Interactive Knowledge Retrieval | Queries the completed wiki | Authoring |

## Sources
1. `README.md:28-52`
2. `VISION.md:3-20`
3. `wikifi/cli.py:1-8`
4. `wikifi/introspection.py:19-44`
5. `wikifi/sections.py:1-19`

## From entities
# Core Entities

The system's domain model spans five functional layers — wiki structure, file classification, extraction, evidence, and review — plus supporting entities for caching, derivation, and chat.

---

## Wiki Structure

**Section** is the central organizing entity. Each section carries a unique identifier, a human-readable title, a prose description of what belongs in it, and a tier (primary or derivative). Derivative sections additionally declare an ordered list of upstream section identifiers they depend on, forming an explicit dependency graph. An invariant holds at startup: every upstream identifier in a derivative section's dependency list must refer to a section that appears earlier in the canonical ordering (topological sort enforced).

**WikiLayout** is an immutable value object that encodes the on-disk structure of a wiki workspace. Given a project root, it derives all canonical sub-paths: the wiki directory, configuration file, gitignore file, notes directory, per-section markdown files, and per-section note files. No fields are mutable after construction.

**WalkConfig** is an immutable configuration record consumed by the filesystem walker. It captures the repository root, extra exclusion patterns, a flag for honouring ignore rules, a maximum file size in bytes, and a minimum stripped-content size in bytes.

---

## File Classification and Graph

**FileKind** is a closed enumeration of seven mutually exclusive file roles: application code, SQL, OpenAPI, Protobuf, GraphQL, migration, and other. This classification determines whether a file is routed to a specialised deterministic parser or the general-purpose extraction path.

**GraphNode** represents a single file's position in the repository's import graph. It carries the file's repo-relative path, the ordered set of files it imports, and the ordered set of files that import it. It exposes a capped combined-neighbour list for inclusion in extraction prompts.

**RepoGraph** holds the complete import-edge map for a repository scan. It supports node lookup by path and retrieval of a capped neighbour list for any given file, providing cross-file context during extraction.

**DirSummary** is a value object holding aggregate statistics for a single (non-recursive) directory: its repo-relative path, file count, total byte size, a frequency map of the top-10 file extensions, and a tuple of notable filenames (manifests, readmes) present in that directory.

---

## Extraction Layer

**SectionFinding** represents one file's contribution to one wiki section. It carries the target section identifier, a technology-agnostic prose description of the contribution, and an optional inclusive line range within the source chunk.

**FileFindings** groups a one-sentence summary of a file with all `SectionFinding` records produced for it.

**SpecializedFinding** is the output unit of the deterministic parsing paths. It carries a section identifier, a human-readable description, and a list of source references. **SpecializedResult** groups zero or more such findings with an optional summary string; this is the uniform output contract for all specialised extractors, ensuring interoperability with the general extraction path downstream.

**ExtractionStats** is a walk-level counter record, accumulating: total files seen, files yielding at least one finding, total findings, skipped files, chunks processed, cache hits, specialised-extractor invocations, and a per-kind file breakdown.

---

## Evidence Layer

**SourceRef** represents a single span of source: a repo-relative file path, an optional inclusive line range, and a short content fingerprint captured at extraction time for change detection.

**Claim** represents one assertion placed in a wiki section. It carries the markdown text and a list of `SourceRef` values that justify it. A claim with no sources is explicitly marked unsupported — this is a first-class state, not an error.

**Contradiction** groups two or more conflicting `Claim` objects about the same topic under a single summary sentence. Each disagreeing position retains its own source references, preserving full traceability.

**EvidenceBundle** is the aggregator's structured output for a single wiki section. It combines the narrative body text, a list of `Claim` records, and a list of `Contradiction` records. The renderer uses the bundle to thread numbered citations and a conflicts block into the final markdown.

During aggregation, the pipeline works with intermediate forms: **AggregatedClaim** pairs a single prose assertion with the 1-based indices of the input notes that support it, and **AggregatedContradiction** holds a one-sentence summary alongside multiple conflicting positional claims, each with its own note indices. These are the structured forms that the language model produces before being resolved into the full evidence model.

---

## Cache Entities

**CachedFindings** stores the extraction result for a single file: the file's content fingerprint, the list of structured findings produced, a one-sentence summary, and a count of processed chunks. Its invariant is content-addressed — the fingerprint is the cache key.

**CachedSection** stores the aggregation result for a single wiki section: the hash of the notes payload that produced it, the rendered markdown body, and lists of claims and contradictions. It too is content-addressed on the notes hash.

**WalkCache** is the in-memory container for both caches. It holds extraction and aggregation entries alongside hit and miss counters, enabling observability into cache effectiveness across a run.

---

## Quality and Review Layer

**Critique** captures the quality assessment of a single section: an integer score (0–10), a short overall judgment, a list of unsupported claims, a list of gaps relative to the section brief, and a list of concrete revision suggestions.

**ReviewOutcome** tracks a section's review lifecycle: the section identifier, the initial critique, the current body text, a flag indicating whether a revision was applied, and the optional follow-up critique produced after revision.

**WikiQualityReport** aggregates the full-wiki audit: an overall numeric score, a mapping from section identifiers to their individual `Critique` records, and optional coverage statistics.

**CoverageStats** records total files seen, files with findings, and per-section breakdowns of finding counts and contributing file counts; it exposes a coverage-percentage computation.

**SectionReport** captures the per-section view for reporting: the section descriptor, count of contributing files, total findings count, body size in characters, an emptiness flag, and an optional quality critique.

**WikiReport** aggregates all `SectionReport` records alongside overall coverage statistics and an optional mean quality score across populated sections.

---

## Derivation and Pipeline Outputs

**IntrospectionResult** captures the Stage 1 decision about which files are worth deeper analysis: a list of gitignore-style include patterns, a list of exclude patterns, a list of primary languages (informational), a one-paragraph guess at the system's purpose, and a rationale for the choices made.

**AggregationStats** records, for a single aggregation run, how many sections were written fresh, skipped due to empty notes, or served from cache.

**DerivationStats** accumulates pipeline metrics for the derivation stage: counts of sections derived, skipped, and revised, plus the full list of `ReviewOutcome` records. It acts as an audit trail for the synthesis stage.

**WalkReport** is the single return value of a completed wiki-generation run, aggregating the introspection result, extraction statistics, aggregation statistics, derivation statistics, the live cache state, and the repository import graph.

---

## Chat Layer

**ChatMessage** carries a role and a content field, representing a single turn in a multi-turn conversation. Lists of these are accumulated to maintain conversation history.

**LoadedSection** pairs a `Section` descriptor with its rendered markdown body, representing a single populated section ready for inclusion in a chat context.

**ChatSession** holds a provider reference, the frozen system prompt built from wiki sections, and the accumulated conversation history as an ordered list of `ChatMessage` records. It supports appending user and assistant turns and clearing history while retaining the wiki context.

---

## Relationships and Invariants Summary

| Entity | Key relationships | Notable invariants |
|---|---|---|
| Section | depends on upstream Sections (derivative tier only) | Dependency graph must be topologically ordered |
| WikiLayout | derived from a project root | Immutable; all paths are computed, not stored independently |
| SourceRef | referenced by Claim, SpecializedFinding | Fingerprint enables staleness detection |
| Claim | groups SourceRefs; composed into EvidenceBundle | Sourceless claims are explicitly flagged unsupported |
| Contradiction | groups ≥2 conflicting Claims | Each position retains its own SourceRefs |
| CachedFindings | keyed on file content fingerprint | Cache miss if fingerprint changes |
| CachedSection | keyed on notes-payload hash | Cache miss if any upstream note changes |
| ReviewOutcome | holds pre- and post-revision Critique | Revision flag distinguishes touched from untouched sections |
| WalkReport | aggregates all four stage outputs | Single return value for a complete run |

## Sources
1. `wikifi/sections.py:30-40`
2. `wikifi/deriver.py:112-116`
3. `wikifi/cli.py:166-172`
4. `wikifi/wiki.py:34-61`
5. `wikifi/walker.py:61-79`
6. `README.md:31-33`
7. `wikifi/repograph.py:41-52`
8. `wikifi/repograph.py:148-167`
9. `wikifi/repograph.py:170-181`
10. `wikifi/walker.py:144-153`
11. `wikifi/extractor.py:106-123`
12. `wikifi/specialized/__init__.py:29-38`
13. `wikifi/extractor.py:126-135`
14. `wikifi/evidence.py:37-52`
15. `README.md:37-39`
16. `wikifi/evidence.py:55-67`
17. `wikifi/aggregator.py:166-186`
18. `wikifi/evidence.py:70-77`
19. `wikifi/aggregator.py:74-101`
20. `README.md:46-48`
21. `wikifi/evidence.py:80-85`
22. `wikifi/cache.py:44-51`
23. `wikifi/cache.py:54-60`
24. `wikifi/cache.py:63-70`
25. `wikifi/aggregator.py:103-107`
26. `wikifi/critic.py:67-84`
27. `wikifi/critic.py:91-96`
28. `wikifi/critic.py:99-114`
29. `wikifi/report.py:85-94`
30. `wikifi/report.py:28-42`
31. `wikifi/introspection.py:47-64`
32. `wikifi/deriver.py:57-62`
33. `wikifi/orchestrator.py:54-61`
34. `wikifi/cli.py:118-153`
35. `wikifi/providers/base.py:28-30`
36. `wikifi/chat.py:42-45`
37. `wikifi/chat.py:46-57`
38. `wikifi/specialized/sql.py:64-84`
39. `wikifi/specialized/sql.py:99-111`
40. `wikifi/specialized/graphql.py:32-81`
41. `wikifi/specialized/protobuf.py:44-68`
42. `wikifi/specialized/openapi.py:94-108`

## From integrations
# Integrations

### Inbound: Entry Points into the System

The system is distributed as a library installed directly into a target project. The command-line interface (CLI) is the primary inbound entry point, exposing subcommands that drive the full pipeline from repository introspection through wiki generation, interactive querying, and quality reporting. The CLI delegates all pipeline coordination to the orchestrator, which is also the central hub wiring together every downstream stage.

---

### Outbound: AI Model Backends

All pipeline stages — introspection, per-file extraction, section aggregation, derivative content derivation, quality critique, and interactive chat — communicate with an AI model backend exclusively through a shared provider abstraction. No stage calls a specific backend directly. Three interaction shapes are exposed through this abstraction: schema-validated structured output, free-text completion, and multi-turn stateful conversation.

Three backends are available and are interchangeable without altering any pipeline code:

| Backend type | Hosting model |
|---|---|
| Local self-hosted inference runtime | On-premise / developer machine |
| Hosted AI service (Anthropic-compatible) | Remote cloud |
| Hosted AI service (OpenAI-compatible) | Remote cloud or self-managed endpoint |

The active backend is selected via an environment variable or a per-invocation flag at the CLI level. OpenAI-compatible endpoints — including corporate reverse proxies and managed cloud deployments — are supported by overriding the base URL alone, with no other changes to the calling code.

---

### Outbound: Development-Time Tool Servers (MCP)

A separate set of external capability providers is declared through an MCP client configuration used during development or runtime. Four tool servers are wired up: a local AI utility, a local web crawler, a remote documentation-context service, and a remote search-and-stitching service. The system acts as an MCP client that fans requests out to these providers as needed.

---

### Outbound: Filesystem and Persistence Layer

All reading and writing of wiki artifacts — extraction notes, finished section bodies, and cache entries — flows through a centralized layout abstraction that manages the `.wikifi/` output directory inside the target project. The extractor, aggregator, deriver, CLI, and orchestrator all resolve paths through this abstraction rather than independently.

A content-addressed cache layer sits between the orchestrator and the AI backend, consulting a fingerprinting service to derive content hashes as cache keys. The extractor, aggregator, and orchestrator each consult the cache before issuing AI calls, enabling both incremental re-runs and resumability for large codebases.

---

### Integration Touchpoints Discovered in Target Codebases

When analyzing a target codebase, the system identifies and surfaces integration touchpoints from high-signal artifact files through specialized parsers:

- **HTTP API surfaces** — Parsed from API contract files; each contract contributes a finding recording the count of externally exposed endpoints, establishing the public-facing API surface as a documented integration point.
- **RPC service definitions** — Each declared service and its remote procedures are mapped, capturing procedure names, request and response message types, and whether either channel is streaming.
- **Event-driven channels** — Subscription roots found in schema definition files are classified as real-time integration touchpoints rather than ordinary capabilities, reflecting their role as channels that external consumers attach to.
- **Relational links** — Foreign key declarations (both explicit and inline) are surfaced as hard relational links between domain entities, identifying cross-entity data dependencies.

The dispatcher that routes files to these specialized parsers uses the file-kind classification produced by the repository graph module, ensuring each artifact type reaches the appropriate parser while preserving a uniform output contract for downstream aggregation.

## Sources
1. `README.md:8-12`
2. `wikifi/cli.py:98-101`
3. `wikifi/orchestrator.py:40-60`
4. `wikifi/providers/base.py:30-48`
5. `wikifi/providers/anthropic_provider.py:115-175`
6. `wikifi/providers/ollama_provider.py:58-95`
7. `wikifi/providers/openai_provider.py:1-8`
8. `README.md:46-51`
9. `TESTING-AND-DEMO.md:232-235`
10. `.mcp.json:2-36`
11. `wikifi/wiki.py:34-61`
12. `wikifi/cache.py:244-246`
13. `wikifi/cache.py:30`
14. `wikifi/specialized/openapi.py:83-92`
15. `wikifi/specialized/protobuf.py:70-87`
16. `wikifi/specialized/graphql.py:88-91`
17. `wikifi/specialized/sql.py:86-96`
18. `wikifi/specialized/__init__.py:46-57`
