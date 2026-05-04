# Cross-Cutting Concerns

The cross-cutting concerns span six domains: observability, cache and data integrity, crash survivability, graceful degradation, auditability, and storage invariants. Each represents a non-functional requirement that any migration must explicitly preserve.

### Observability and Monitoring

Structured logging is configured globally before any processing begins, gated by a verbosity flag. Log entries are emitted at every major pipeline stage boundary—scope classification, dependency graph construction, extraction, aggregation, derivative synthesis, and short-circuit decisions—providing continuous operational visibility into pipeline progress.

Cache efficiency is tracked per pipeline scope (extraction, aggregation, derivation) through hit and miss counters, giving operators a quantitative view of work reused versus recomputed across runs.

Error reporting from external AI service calls is normalised across all backends: every diagnostic includes the provider name, a request identifier where available, and the error message, ensuring consistent observability regardless of which backend is active. When a structured response returns empty, the system inspects the stop reason and output token count and surfaces actionable remediation hints at the failure site.

The reporting subsystem enforces a strict read-only invariant over the wiki: it consumes notes, section markdown, and the walk cache but never writes to any of them. Quality scoring is decoupled from structural coverage reporting; the structural report is usable in automated pipelines without any AI dependency, while scoring is opt-in and requires a live provider.

### Cache and Data Integrity

The persistence layer is content-addressed with several explicit integrity invariants:

- **Atomic writes**: Cache files are first committed to a sibling temporary file, then renamed over the target, preventing a half-written file from corrupting subsequent runs.
- **Schema versioning**: The cache carries an explicit integer version number. Entries whose stored version does not match the current version are silently dropped and recomputed on the next run, with a documented change history.
- **Fingerprint coherence**: A single shared fingerprinting primitive covers cache key generation, evidence citation, and the dependency graph, so a change to any source file triggers correct cross-file invalidation across all subsystems.[12]
- **Partial-failure protection**: A file's cache entry is written only when every processing chunk succeeds; a partial failure leaves the file uncached so the next run reprocesses it in full.[13]
- **Error-body exclusion**: Bodies produced by failed synthesis attempts are never stored in the cache, preventing a transient failure from being replayed until upstream content changes.[14]
- **Empty-section tracking**: Sections with no notes receive a dedicated cache entry recording zero notes seen, distinguishing them from sections that were never aggregated and preventing stale prose from persisting undetected when a file deletion drains a section's evidence.
- **Derivative cache validation**: Derivative section cache freshness is validated on two axes simultaneously—a hash of upstream section bodies (content integrity) and a flag recording whether a critic review loop ran (review-mode parity). A cache hit requires both to match the current run's parameters.
- **Selective invalidation**: A runtime flag disables cache reads and resets the entire persisted cache state, ensuring stale findings are never carried forward.[17]
- **Scope pruning**: Out-of-scope files are removed from the extraction cache at the start of each walk, keeping cache size proportional to the live in-scope file set.[18]

Citation integrity is separately maintained across incremental section updates: surviving cached claims are tracked, new claims are resolved against their source references, and the contradiction list is replaced wholesale so the citation footer never references evidence that no longer exists.

The orchestrator enforces five strict conditions before short-circuiting downstream stages: caching must be enabled, at least one file must have been seen, every file must have been cache-served or deterministically extracted (no new AI output), the scope classification hash must match the prior walk's, and every primary and derivative section's cache must be fresh. This prevents a previously crashed mid-pipeline run from silently perpetuating stale content.

Empty-placeholder detection during derivative synthesis uses a multi-pattern heuristic covering distinct shapes of "no real content" text produced at different pipeline stages, preventing downstream sections from treating placeholder strings as substantive evidence.

For schema-centric artefacts, entities and capabilities defined across multiple partial schema files via composition directives are explicitly handled, ensuring nothing is silently dropped when schemas are assembled from many partial sources.

### Crash Survivability

Crash resumability is a first-class design property implemented at every stage boundary. During extraction, the cache is persisted after each file completes, allowing interrupted runs to resume from the last successful file.[22] During aggregation, an incremental-persist callback fires after each successful section update, so a mid-run crash loses at most the current section's work. Each pipeline stage also persists its own cache slice immediately upon completion, leaving the on-disk state in the most-advanced-consistent position rather than requiring all stages to succeed atomically.

### Graceful Degradation

Failures are isolated rather than propagated:

- Extraction failures are scoped per-file and per-chunk; they are logged and counted as skipped without aborting the overall walk.[25] An orchestrator-level invariant ensures a failed specialized extraction does not increment the specialized-files counter, which the pipeline uses as proof that no AI work was silently lost.
- Aggregation failures are logged as warnings; the incremental-edit path falls through to a full rewrite on any exception so sections are never silently absent from the output.
- Critic and reviser failures are logged as warnings; a failed critic returns a score of zero with a diagnostic summary rather than halting execution.[28]
- AI service failures during interactive sessions are reported to the user without terminating the session; conversation history is preserved in memory for the lifetime of the session.

All AI service calls are subject to a per-request timeout to prevent indefinite hangs. Files exceeding a configurable size threshold are unconditionally skipped as likely vendored or generated noise; files whose content falls below a minimum byte count after stripping are skipped to avoid runaway reasoning on stubs.

Directory traversal prunes ignored subtrees before descent, so excluded directories are never visited at all; this is both a performance and a correctness invariant that must be preserved across any reimplementation.

### Auditability and Traceability

Every generated claim is structurally required to carry source references back to specific files and optional line ranges. Unsupported claims are explicitly distinguishable via a predicate, making auditability a structural invariant of the pipeline rather than a best-effort annotation.

All specialized extractors share a uniform output contract that includes provenance (source file path, fingerprint, and line range), ensuring every wiki note can be traced to its exact origin regardless of which extractor produced it.

Per-file extraction notes are timestamped at write time in coordinated universal time, providing an audit trail of when each finding was recorded.[34] The scope classification stage produces output under a strict typed schema, making its results deterministic to parse and straightforward to diff across runs.

The section dependency graph's referential integrity is enforced eagerly at module load time: unknown upstream references and out-of-order dependencies both raise errors before any files are processed, preventing silent misconfiguration.

Empty or unpopulated sections are detected by scanning body text for known sentinel strings and are excluded from quality scoring while being explicitly flagged in coverage reports.[37]

Notes and cache directories are excluded from version control via a managed ignore file, with a backfill mechanism that appends missing entries to existing ignore files during initialization. Only finalized section markdown is committed.

### Authentication and Authorization

Authentication contracts discovered in API contract files are formally captured as cross-cutting invariants. The declared authentication mechanisms—including API key schemes, bearer tokens, and OAuth flows—are surfaced as structured wiki findings and are explicitly treated as requirements that must be preserved through any migration.

### Storage Invariants

Unique and non-null constraints on table definitions are recorded as storage invariants the replacement system must honour. Indexes are separately recorded as query-time performance invariants. Both categories carry precise line-level citations back to the schema source.

Database migration scripts are distinguished from general schema definition files, enabling the wiki to separate the current authoritative schema from the forward-only incremental change history.[42] This distinction is recognized for a wide range of common migration tooling conventions.

### Cost Control and Reproducibility

Cost control is treated as a first-class non-functional requirement. The large, repeated system prompt is placed at a consistent message position across all call types to exploit upstream API prefix-caching, amortising prompt processing costs across every per-file call in a walk.

Structured-output calls pin temperature to zero, ensuring the same input produces identical structured results across runs. Free-text and conversational calls leave temperature at the model default, accepting variability in exchange for naturalness.

A reasoning-depth parameter serves as a system-wide quality-versus-latency tradeoff knob; the system's stated preference is output quality over wall-clock speed, particularly for derivative-section generation. Operators must be aware that adjusting this parameter affects both schema adherence and processing duration.

A configurable churn-ratio threshold determines when incremental section editing is safe versus when a full rewrite is required; exceeding the threshold forces complete re-synthesis to prevent latent inconsistencies from being silently preserved. Finding identifiers that are empty strings unconditionally force a full rewrite to avoid identity collisions.

## Supporting claims
- Structured logging is configured globally before any processing begins, controlled by a verbosity flag. [1]
- Log entries are emitted at every major pipeline stage boundary, including scope classification, graph construction, extraction, aggregation, derivative synthesis, and short-circuit decisions. [2]
- Cache efficiency is tracked per pipeline scope (extraction, aggregation, derivation) via hit and miss counters. [3]
- Error reporting from external AI service calls is normalised across all backends, including provider name, request identifier, and error message. [4][5][6]
- When a structured response returns empty, the system diagnoses the root cause by inspecting the stop reason and token count and surfaces actionable remediation hints at the failure site. [7]
- The reporting subsystem enforces a strict read-only invariant over the wiki, never writing to notes, section markdown, or the walk cache. [8]
- Quality scoring is decoupled from structural coverage reporting; the structural report is usable in automated pipelines without any AI dependency. [9]
- All cache files are written atomically via a sibling temporary file and rename, preventing half-written files from corrupting subsequent runs. [10]
- The cache carries an explicit integer version number; entries whose stored version does not match the current version are silently dropped and recomputed on the next run. [11]
- Sections with no notes receive a dedicated cache entry recording zero notes seen, distinguishing them from sections that were never aggregated. [15]
- Derivative section cache freshness is validated on two axes simultaneously: a hash of upstream section bodies and a flag recording whether the critic review loop ran. [16]
- Citation integrity is maintained across incremental section updates: surviving cached claims are tracked, new claims resolved against source references, and the contradiction list replaced wholesale. [19]
- The orchestrator enforces five strict conditions before short-circuiting downstream stages: caching enabled, files seen, all files cache-served or deterministically extracted, scope hash matching prior walk, and all section caches fresh. [20]
- Empty-placeholder detection in derivative synthesis uses a multi-pattern heuristic covering distinct shapes of 'no real content' text, preventing downstream sections from treating placeholders as substantive evidence. [21]
- An incremental-persist callback fires after each successful section update during aggregation, so a mid-run crash loses at most the current section's work. [23]
- Each pipeline stage persists its own cache slice immediately upon completion, leaving on-disk state in the most-advanced-consistent position rather than requiring all stages to succeed atomically. [24]
- An orchestrator-level invariant ensures a failed specialized extraction does not increment the specialized-files counter, preserving the pipeline's accounting proof that no AI work was silently lost. [26]
- Aggregation failures are logged as warnings and the incremental-edit path falls through to a full rewrite on any exception, so sections are never silently absent. [27]
- AI service failures during interactive sessions are reported to the user without terminating the session; conversation history is preserved in memory for the session lifetime. [29]
- All AI service calls are subject to a per-request timeout; files exceeding a size threshold are unconditionally skipped; files below a minimum content byte count are also skipped. [30]
- Directory traversal prunes ignored subtrees before descent, so excluded directories are never visited; this is both a performance and correctness invariant. [31]
- Every generated claim is structurally required to carry source references back to specific files and optional line ranges; unsupported claims are explicitly distinguishable via a predicate. [32]
- All specialized extractors share a uniform output contract that includes provenance (source file path, fingerprint, and line range), ensuring traceability regardless of which extractor produced the note. [33]
- The scope classification stage produces output under a strict typed schema, making results deterministic to parse and straightforward to diff across runs. [35]
- The section dependency graph's referential integrity is enforced eagerly at module load time; unknown upstream references and out-of-order dependencies raise errors before any files are processed. [36]
- Notes and cache directories are excluded from version control via a managed ignore file, with a backfill mechanism that appends missing entries during initialization. [38][34][39]
- Authentication contracts from API contract files—including API key, bearer token, and OAuth flows—are surfaced as structured wiki findings and treated as cross-cutting invariants that must be preserved through migration. [40]
- Unique and non-null constraints on table definitions are recorded as storage invariants the replacement system must honour; indexes are separately recorded as query-time performance invariants, both with line-level citations. [41]
- The large system prompt is placed at a consistent message position across all call types to exploit upstream API prefix-caching, amortising prompt processing costs across every per-file call. [43][44]
- Structured-output calls pin temperature to zero, ensuring the same input produces identical structured results across runs; free-text and conversational calls leave temperature at the model default. [45]
- A reasoning-depth parameter serves as a quality-versus-latency tradeoff knob; the system's stated preference is output quality over wall-clock speed, particularly for derivative-section generation. [46]
- A configurable churn-ratio threshold determines when incremental section editing is safe versus when a full rewrite is required; empty finding identifiers unconditionally force a full rewrite to avoid identity collisions. [47][48]
- Section-level caching uses a digest of the notes payload; the cache key is intentionally left stale when only line ranges or summaries drift to prevent the orchestrator from locking stale citations in place. [49]
- Entities and capabilities defined across multiple partial schema files via composition directives are explicitly handled, ensuring nothing is silently dropped when schemas are assembled from many partial sources. [50]

## Sources
1. `wikifi/cli.py:54-63`
2. `wikifi/orchestrator.py:93-218`
3. `wikifi/cache.py:148-155`
4. `wikifi/providers/anthropic_provider.py:147-157`
5. `wikifi/providers/base.py:58-68`
6. `wikifi/providers/openai_provider.py:126-135`
7. `wikifi/providers/anthropic_provider.py:271-296`
8. `wikifi/report.py:13-15`
9. `wikifi/report.py:78-85`
10. `wikifi/cache.py:323-327`
11. `wikifi/cache.py:52-63`
12. `wikifi/fingerprint.py:1-18`
13. `wikifi/extractor.py:317-330`
14. `wikifi/deriver.py:181-186`
15. `wikifi/aggregator.py:143-157`
16. `wikifi/deriver.py:141-162`
17. `wikifi/cli.py:119-122`
18. `wikifi/orchestrator.py:117-121`
19. `wikifi/surgical.py:222-270`
20. `wikifi/orchestrator.py:197-232`
21. `wikifi/deriver.py:208-219`
22. `wikifi/extractor.py:163-168`
23. `wikifi/aggregator.py:116-121`
24. `wikifi/orchestrator.py:148-226`
25. `wikifi/extractor.py:207-215`
26. `wikifi/extractor.py:218-227`
27. `wikifi/aggregator.py:193-209`
28. `wikifi/critic.py:143-148`
29. `wikifi/chat.py:130-138`
30. `wikifi/config.py:60-83`
31. `wikifi/walker.py:127-145`
32. `wikifi/evidence.py:60-67`
33. `wikifi/specialized/models.py:16-26`
34. `wikifi/wiki.py:131-143`
35. `wikifi/introspection.py:7-10`
36. `wikifi/sections.py:155-166`
37. `wikifi/report.py:111-119`
38. `wikifi/cache.py:285-298`
39. `wikifi/wiki.py:110-130`
40. `wikifi/specialized/openapi.py:111-120`
41. `wikifi/specialized/sql.py:109-141`
42. `wikifi/repograph.py:97-115`
43. `wikifi/providers/anthropic_provider.py:200-218`
44. `wikifi/providers/openai_provider.py:10-20`
45. `wikifi/providers/ollama_provider.py:59-69`
46. `wikifi/providers/ollama_provider.py:6-31`
47. `wikifi/config.py:88-94`
48. `wikifi/surgical.py:130-185`
49. `wikifi/aggregator.py:155-175`
50. `wikifi/specialized/graphql.py:7-11`
