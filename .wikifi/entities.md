# Core Entities

The system's domain is built from several coherent groups of entities that span the four pipeline stages — introspection, extraction, aggregation, and derivation — plus cross-cutting concerns for caching, quality review, and evidence tracing.

---

## Section Taxonomy

A **Section** is the atomic unit of the generated wiki. It carries a stable identifier, a human-readable title, a prose description brief, and a *tier* classification of either **primary** (fed directly by per-file evidence) or **derivative** (synthesized from upstream primary sections). Derivative sections must explicitly declare an ordered tuple of upstream section identifiers they depend on; this dependency ordering is validated at startup.

---

## Extraction Entities

The extraction stage produces three entity types:

- **SectionFinding** — a single contribution from one source file to one wiki section. It carries the target section identifier, a technology-agnostic description, and an optional line range within the source file.
- **FileFindings** — groups all findings produced from a single file alongside a one-sentence summary of that file's role.
- **ExtractionStats** — a run-level accumulator recording files seen, files with at least one finding, total findings, files skipped, chunks processed, cache hits, specialized-extractor files, and a breakdown of file kinds encountered.

Specialized (non-LLM) extractors emit **SpecializedFinding** and **SpecializedResult** types that mirror the same shape: a finding carries a target section identifier, finding text, and a list of source references; a result aggregates zero or more findings with an optional file-level summary.

---

## Evidence and Citation Model

Every assertion in the wiki is grounded by a three-layer evidence model:

| Entity | Key fields | Invariant |
|---|---|---|
| **SourceRef** | repo-relative path, optional line range, content fingerprint | Lines are optional when a finding spans an entire module |
| **Claim** | markdown text, list of SourceRefs | A claim with no SourceRefs is classified as *unsupported* |
| **Contradiction** | conflict summary sentence, two or more Claim positions | Each position carries its own SourceRefs so disagreeing files are traceable |
| **EvidenceBundle** | markdown narrative body, list of Claims, list of Contradictions | Unit handed from aggregator to renderer |

During the aggregation stage, the LLM-facing variants of these types — **AggregatedClaim** (assertion text + 1-based note indices) and **AggregatedContradiction** (summary + list of AggregatedClaim positions) — are collected into a **SectionBody**, which adds the markdown body string. The EvidenceBundle is the resolved, renderer-ready form after source references are expanded.

---

## Cache Entities

The persistence layer maintains four scoped cache entities, all held in memory by a single **WalkCache** aggregate that tracks hit/miss counters per scope and supports pruning of stale entries:

- **CachedFindings** — keyed by repo-relative file path; holds the file's content fingerprint, the extractor's structured findings, a file-role summary, and the chunk count.
- **CachedSection** — holds the hash of the notes payload that produced it, the rendered markdown body, resolved claims and contradictions, and an ordered list of stable finding identifiers used for surgical-diff classification.
- **CachedDerivation** — holds the hash of upstream section bodies it was synthesized from, the rendered body, and a boolean flag recording whether the critic-and-reviser review loop was applied.
- **CachedIntrospection** — holds a hash of the include/exclude scope and the full Stage 1 payload, allowing the orchestrator to short-circuit all later stages when the walked file set is unchanged.

---

## Surgical Update Entities

When cached sections exist but findings have changed, the system uses a specialized entity group to decide how much work to redo:

- **SectionChange** — captures the per-section diff decision ('unchanged', 'surgical', or 'rewrite'), the 1-based positions of newly appearing findings, the identifiers of disappeared findings, the unchanged finding count, and the live total. A derived `churn_ratio` expresses total delta size relative to the live set.
- **SurgicalClaim** — a newly introduced assertion indexed against the added-findings list.
- **SurgicalContradiction** — a summary and a list of SurgicalClaim positions, scoped to the surgical pass.
- **SurgicalEdit** — the output of one surgical pass: an edited body, a list of new SurgicalClaims, a list of 1-based indices identifying cached claims to drop (whose evidence is gone), and the full post-edit contradictions list.

---

## Quality Review Entities

- **Critique** — carries an integer quality score (0–10), a summary judgment, a list of unsupported claims found in the body, a list of brief gaps not covered, and a list of concrete suggested edits.
- **ReviewOutcome** — records the section identifier, the initial Critique, the current body text, a revision-occurred flag, and an optional final Critique after revision.
- **WikiQualityReport** — aggregates an overall floating-point quality score, a mapping of section identifiers to their Critique objects, and optional coverage statistics.

Two distinct **CoverageStats** entities exist — one associated with the quality-review subsystem and one with the reporting subsystem. Both track total files analysed and files that yielded findings, and both maintain per-section finding and contributing-file counts. The quality-review variant additionally exposes a coverage percentage (files-with-findings ÷ total files); the report variant does not explicitly surface this derived ratio.

---

## Repository Graph Entities

- **FileKind** — an enumeration of seven recognized artifact categories: application code, SQL, OpenAPI, Protocol Buffer, GraphQL, migration, and other.
- **GraphNode** — represents one file's position in the dependency graph, carrying its repo-relative path, the ordered set of files it imports, and the ordered set of files that import it; exposes a capped combined neighbor list for prompt injection.
- **RepoGraph** — aggregates all GraphNode instances and exposes node lookup by path, capped neighbor lookup by path, and membership testing.

---

## Filesystem and Layout Entities

- **WalkConfig** — captures all filtering parameters for one walk: root directory, additional exclude patterns, gitignore-honouring flag, maximum file size, and minimum stripped-content size.
- **DirSummary** — captures non-recursive aggregate statistics for one directory: relative path, file count, total bytes, a top-10 extension histogram, and names of notable manifest or readme files.
- **WikiLayout** — a value object that is the single source of truth for every artefact path in the `.wikifi/` workspace: the wiki directory, provider/model config file, gitignore, per-section notes directory, content-addressed cache directory, and per-section markdown and notes files.

---

## Pipeline Reporting Entities

- **WalkReport** — aggregates all four stage outputs: introspection result, extraction statistics, aggregation statistics, derivation statistics, a cache snapshot, and the import graph, plus a flag indicating whether the run was a no-op due to full caching.
- **SectionReport** — per-section metrics: section descriptor, contributing-file count, finding count, body character length, emptiness flag, and an optional quality critique.
- **WikiReport** — aggregates a list of SectionReports, overall coverage statistics, and an optional mean quality score across populated sections.
- **AggregationStats** — tracks sections written, found empty, served from cache, surgically edited, or fully rewritten in a single aggregation run.
- **DerivationStats** — tracks sections derived, skipped (no upstream content), revised (critic loop changed the text), and served from cache, plus the list of individual critic review outcomes.
- **IntrospectionResult** — the structured output of the repository-scanning decision: include patterns, exclude patterns, detected primary languages, a free-text likely-purpose paragraph, and a rationale string. All fields default to empty, making the entity safe to parse from partial responses.

---

## Chat Session Entities

- **LoadedSection** — pairs a canonical Section descriptor with the markdown body read from disk.
- **ChatSession** — holds a reference to the LLM provider, a frozen system prompt built from all loaded sections, and a mutable message history. It exposes two operations: *send* (appends a user turn, calls the provider, appends the assistant reply) and *reset* (clears history while leaving the loaded context intact).

---

## Provider and Messaging Entities

- **ChatMessage** — a value object carrying a *role* and a *content* string, representing one turn in a multi-turn conversation.
- **LLMProvider** — carries a provider name and model identifier, and exposes exactly three call surfaces as its complete public contract.

---

## Settings

A **Settings** entity captures all pipeline tunables as a single cohesive record: provider identity and credentials, model identifier, inference endpoint, request timeout, file-size and content-size thresholds, chunk and overlap sizes, introspection depth, thinking-mode level, and a set of feature flags (caching, graph construction, specialized extractors, review loop, surgical edits) along with their associated numeric thresholds. Settings are resolved via a layered precedence model where per-project configuration overrides process-wide environment variables.[36]

## Supporting claims
- A Section carries a stable identifier, human-readable title, prose description, tier classification (primary or derivative), and an ordered tuple of upstream section identifiers it depends on. [1]
- Derivative sections must explicitly declare upstream dependencies, and this ordering is validated at startup. [1]
- A SectionFinding carries the target section identifier, a technology-agnostic description, and an optional line range. [2]
- A FileFindings groups all findings from one file alongside a one-sentence file-role summary. [3]
- ExtractionStats accumulates files seen, files with findings, total findings, skipped files, chunks processed, cache hits, specialized files, and a file-kind breakdown. [4]
- SpecializedFinding carries a target section identifier, finding text, and source references; SpecializedResult aggregates findings with an optional file-level summary. [5]
- A SourceRef carries a repo-relative file path, an optional line range, and a content fingerprint; lines are optional for cross-cutting findings. [6]
- A Claim carries markdown text and a list of SourceRefs; a claim with no SourceRefs is classified as unsupported. [7]
- A Contradiction groups two or more conflicting Claims under a one-sentence conflict summary, each position carrying its own SourceRefs. [8]
- An EvidenceBundle combines a markdown narrative body, a list of Claims, and a list of Contradictions, and is the unit handed from aggregator to renderer. [9]
- An AggregatedClaim carries assertion text and 1-based note indices; an AggregatedContradiction carries a summary and a list of AggregatedClaim positions. [10]
- A SectionBody is the LLM-facing structured output for one wiki section: a markdown body, a list of claims, and a list of contradictions. [11]
- CachedFindings is keyed by repo-relative file path and holds the content fingerprint, structured findings, file-role summary, and chunk count. [12]
- CachedSection holds the notes-payload hash, rendered markdown body, resolved claims and contradictions, and an ordered list of stable finding identifiers. [13]
- CachedDerivation holds the upstream section bodies hash, rendered body, and a boolean flag recording whether the review loop was applied. [14]
- CachedIntrospection holds a scope hash and the full Stage 1 payload, enabling the orchestrator to short-circuit later stages when the file set is unchanged. [15]
- WalkCache aggregates all four cache scopes, tracks hit/miss counters per scope, and supports pruning of stale extraction entries. [16]
- A SectionChange captures the diff decision (unchanged, surgical, or rewrite), new finding positions, disappeared finding identifiers, unchanged count, live total, and a derived churn_ratio. [17]
- A SurgicalEdit carries an edited markdown body, new SurgicalClaims, indices of cached claims to drop, and the full post-edit contradictions list. [18]
- SurgicalClaim and SurgicalContradiction mirror the regular evidence types but are indexed against the added-findings list within a surgical pass. [19]
- A Critique carries an integer quality score (0–10), a summary judgment, a list of unsupported claims, a list of brief gaps, and a list of suggested edits. [20]
- A ReviewOutcome records section identifier, initial Critique, current body, a revision-occurred flag, and an optional final Critique. [21]
- A WikiQualityReport aggregates an overall floating-point quality score, a section-to-Critique mapping, and optional coverage statistics. [22]
- FileKind is an enumeration of seven artifact categories: application code, SQL, OpenAPI, Protocol Buffer, GraphQL, migration, and other. [23]
- A GraphNode carries its repo-relative path, the ordered set of files it imports, the ordered set of files that import it, and a capped neighbor list for prompt injection. [24]
- RepoGraph aggregates all GraphNode instances and exposes node lookup by path, capped neighbor lookup, and membership testing. [25]
- WalkConfig captures root directory, additional exclude patterns, gitignore-honouring flag, maximum file size, and minimum stripped-content size. [26]
- DirSummary captures a directory's relative path, file count, total bytes, a top-10 extension histogram, and names of notable manifest or readme files. [27]
- WikiLayout is the single source of truth for every artefact path within the .wikifi/ workspace. [28][29]
- WalkReport aggregates introspection result, extraction statistics, aggregation statistics, derivation statistics, cache snapshot, import graph, and a no-op flag. [30]
- SectionReport captures per-section metrics: section descriptor, contributing-file count, finding count, body character length, emptiness flag, and optional quality critique. [31]
- WikiReport aggregates a list of SectionReports, coverage statistics, and an optional mean quality score. [31]
- AggregationStats tracks sections written, empty, cached, surgically edited, or fully rewritten in one run. [11]
- DerivationStats tracks sections derived, skipped, revised, and cached, plus the list of individual critic review outcomes. [32]
- IntrospectionResult captures include patterns, exclude patterns, primary languages, a likely-purpose paragraph, and a rationale; all fields default to empty. [33]
- A LoadedSection pairs a Section descriptor with its markdown body read from disk. [34]
- A ChatSession holds a provider reference, a frozen system prompt, and a mutable message history, and exposes send and reset operations. [34]
- ChatMessage is a value object carrying a role and content string; LLMProvider carries a name and model identifier and exposes three call surfaces. [35]
- Settings captures all pipeline tunables including provider credentials, model, endpoint, thresholds, chunk/overlap sizes, and feature flags with associated numeric thresholds. [36]

## Conflicts in source
_The walker found disagreements across files. Migration teams should resolve these before re-implementation._

- **Two distinct CoverageStats entities appear in different subsystems with overlapping but not identical fields: the quality-review variant exposes a coverage percentage, while the reporting variant does not.**
  - The quality-review CoverageStats tracks total files analysed, files that yielded findings, and per-section counts of findings and contributing files, and exposes a coverage percentage derived from files-with-findings divided by total files. (`wikifi/critic.py:212-225`)
  - The reporting CoverageStats holds total files seen, files with at least one finding, a per-section finding count map, and a per-section contributing-file count map, with no explicit coverage percentage mentioned. (`wikifi/report.py:101-107`)

## Sources
1. `wikifi/sections.py:30-40`
2. `wikifi/extractor.py:97-108`
3. `wikifi/extractor.py:111-114`
4. `wikifi/extractor.py:117-125`
5. `wikifi/specialized/models.py:16-23`
6. `wikifi/evidence.py:33-52`
7. `wikifi/evidence.py:55-67`
8. `wikifi/evidence.py:70-77`
9. `wikifi/evidence.py:80-85`
10. `wikifi/aggregator.py:74-91`
11. `wikifi/aggregator.py:93-103`
12. `wikifi/cache.py:88-94`
13. `wikifi/cache.py:96-113`
14. `wikifi/cache.py:115-129`
15. `wikifi/cache.py:131-140`
16. `wikifi/cache.py:143-237`
17. `wikifi/surgical.py:100-128`
18. `wikifi/surgical.py:78-97`
19. `wikifi/surgical.py:57-77`
20. `wikifi/critic.py:67-84`
21. `wikifi/critic.py:87-92`
22. `wikifi/critic.py:95-98`
23. `wikifi/repograph.py:44-56`
24. `wikifi/repograph.py:174-196`
25. `wikifi/repograph.py:199-210`
26. `wikifi/walker.py:57-73`
27. `wikifi/walker.py:130-136`
28. `wikifi/cli.py:24`
29. `wikifi/wiki.py:54-79`
30. `wikifi/orchestrator.py:73-87`
31. `wikifi/report.py:28-40`
32. `wikifi/deriver.py:62-68`
33. `wikifi/introspection.py:47-65`
34. `wikifi/chat.py:42-60`
35. `wikifi/providers/base.py:34-56`
36. `wikifi/config.py:46-197`
37. `wikifi/critic.py:212-225`
38. `wikifi/report.py:101-107`
