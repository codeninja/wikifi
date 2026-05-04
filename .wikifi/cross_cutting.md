# Cross-Cutting Concerns

### Observability

Structured logging is enabled globally across all pipeline stages through a single startup hook, with a verbosity flag that switches between standard and debug output levels. Each subsystem registers its own log namespace (conversation, reporting, derivation, and others), so failures are attributable to their origin. Provider-level errors are normalized by a shared formatting helper that includes the vendor-assigned request identifier when available, ensuring consistent and traceable diagnostics regardless of which backend is active.

Token-budget issues are diagnosed explicitly at the provider level: when a structured response comes back empty, the system surfaces the stop reason, output token count, and the active limit, together with hints that distinguish budget exhaustion from a model refusal.

The quality-reporting command is strictly read-only and never modifies the wiki, making it safe to invoke repeatedly in automated pipelines or monitoring hooks without risk of data mutation.

---

### Resilience and Graceful Degradation

The pipeline is designed to produce output under partial failure at every stage:

- **Synthesis failures** during aggregation are caught and logged; affected sections degrade to raw-note preservation rather than raising an exception.
- **Critic and reviser failures** fall back to a zero-score sentinel and the original body, respectively; a score-regression guard prevents a poorly-guided rewrite from replacing better-quality existing content.
- **Per-chunk extraction failures** are logged as warnings; the file continues with whatever chunks succeeded, and a fully failed file increments a counter rather than being silently dropped.
- **Configuration parse failures** are logged as warnings and the system falls back gracefully to environment-derived settings.
- **Provider failures during interactive sessions** are reported to the user without terminating the session.

Incremental cache persistence — a per-section callback invoked after each successfully aggregated section — converts a mid-stage crash or out-of-memory event into a survivable event, preserving all aggregation progress up to the last completed section.

---

### Data Integrity and Evidence Traceability

Every finding produced by the pipeline carries a structured source reference containing the originating file path, an optional line range, and a content fingerprint captured at extraction time. This fingerprint is a 12-character prefix of a cryptographic hash — providing 48 bits of entropy, sufficient to be collision-resistant across any realistic repository — and allows any claim to be re-verified against the original source after a subsequent repository walk.

Deduplication is enforced within each file: identical (section, finding-text) pairs arising from overlapping processing chunks are discarded before being written to the notes store, preventing count inflation.

Contradictions between source files are never silently merged. They are surfaced as high-priority signals in the rendered output, on the explicit rationale that legacy systems routinely hide tribal knowledge in disagreements; making contradictions visible is therefore a non-functional invariant of the documentation pipeline.

Introspection-stage responses are validated against a strict schema, making that stage's output deterministic to validate and straightforward to diff between successive runs — a consistency guarantee that carries forward into extraction.

After incremental (surgical) edits, citation integrity is actively maintained: cached claims are preserved or selectively dropped, new claims carry resolved source references, and contradiction records are fully replaced rather than partially updated. A companion content-integrity invariant requires that any sentence in the cached body not affected by a changed finding must appear verbatim in the revised output.

A heuristic scans upstream section bodies for known sentinel strings before synthesis begins, preventing derivative sections from being generated from boilerplate or placeholder content and guarding against fabricated findings.

All per-file extraction notes are persisted with a UTC timestamp on every record, providing a lightweight audit trail of when each finding was recorded.

A startup validation routine enforces referential integrity across the section dependency graph, raising a descriptive error if any cross-reference names an unknown or out-of-order section. This check runs at module load time so misconfiguration is detected before any pipeline work begins.

---

### Cache and Storage Integrity

All cache writes are atomic: content is first written to a sibling temporary file and then renamed into place, so a crash during writing leaves the previous valid cache file intact. Cache files are stored in a dedicated subdirectory co-located with the wiki output; a programmatically managed ignore file ensures that only the final section markdown is committed to source control, while intermediate extraction notes and the cache are excluded. Missing or corrupt cache files are silently treated as empty (a fresh start), and malformed individual entries are logged as warnings and dropped.

A monotonically incremented schema version gates all cache reads: any cache file written under an older version is rejected entirely and treated as empty, forcing a clean re-run rather than consuming structurally incompatible data. Cache entries for files that leave scope are pruned at the start of each walk to prevent unbounded growth.

Derivation cache entries are keyed by both the hash of upstream section bodies and a flag recording whether the critic-review loop ran; entries from non-reviewed runs are not reused when a reviewed run is requested, preserving quality parity across run modes.

The short-circuit predicate that skips aggregation and derivation enforces five simultaneous conditions: caching must be enabled, at least one file must have been processed, all files must have been cache hits or handled by deterministic extractors, the introspection scope hash must match the prior walk's, and every aggregation and derivation cache entry must be fresh. This prevents a mid-run crash from permanently locking in stale sections. Introspection results are persisted to disk before extraction begins so that this predicate remains evaluable even after a crash.

For structured-output inference calls the temperature is pinned to zero, ensuring identical inputs produce identical outputs across runs. Free-text and conversational calls use the model's default temperature and may therefore vary between runs.

Prompt caching at the service level — achieved by placing the large, repeated system prompt in a predictable position in every request — reduces the cost and latency of the many per-file calls that make up a single pipeline run.

---

### Configuration Integrity

Target-specific configuration overrides are allowlisted to a small set of fields; any additional or unrecognized fields in a hand-edited or stale configuration file are silently ignored to prevent unintended behavior changes. Configuration parse failures are logged as warnings and the system falls back to environment-derived settings rather than crashing. A process-wide settings singleton is used to avoid redundant reads, with an explicit invalidation mechanism to support isolated test execution when environment variables are mutated between cases.

---

### Authentication and Authorization

Authentication and authorization contracts are extracted from API specification files: the set of scheme types (bearer tokens, API keys, OAuth flows, and similar mechanisms) that external consumers must present to access the system is surfaced as explicit wiki findings. This ensures that access-control requirements are visible to migration teams as first-class documented facts rather than being implicit in raw specification files.

---

### Data-Quality Invariants

File selection applies a cheapest-first filter chain (path pattern → size check → content read) that enforces a minimum content threshold before any analysis pass runs. This threshold is explicitly motivated by inference model behaviour — preventing speculative or runaway outputs on near-empty files — making it a data-quality invariant that must be preserved through any migration of the analysis pipeline.

Relational schema extractors capture UNIQUE and NOT NULL constraints as storage invariants and indexes as performance invariants, both annotated with the explicit requirement that they must survive migration to the target system.

The tech-agnostic output invariant — that synthesized prose must express all observations in domain terms and must never name specific technologies — is enforced both in the inference system prompt and as a stated structural design goal of the incremental update subsystem.

## Supporting claims
- Structured logging is enabled globally through a single startup hook with a verbosity flag; each subsystem registers its own log namespace. [1][2][3][4]
- Provider-level errors are normalized by a shared formatting helper that includes the vendor-assigned request identifier when available. [5]
- Token-budget issues are diagnosed explicitly: stop reason, output token count, active limit, and disambiguation hints are surfaced. [6]
- The quality-reporting command is strictly read-only and never modifies the wiki. [7]
- Synthesis failures during aggregation degrade to raw-note preservation rather than raising an exception. [8]
- Critic and reviser failures fall back to a zero-score sentinel and the original body respectively; a score-regression guard is present. [9]
- Per-chunk extraction failures are logged as warnings and do not abort the file walk; fully failed files increment a counter. [10]
- Configuration parse failures are logged as warnings and the system falls back to environment-derived settings. [11]
- Provider failures during interactive sessions are reported to the user without terminating the session. [12]
- Incremental cache persistence via a per-section callback makes mid-stage crashes survivable by preserving all aggregation progress up to the last completed section. [13]
- Every finding carries a structured source reference with file path, optional line range, and a content fingerprint captured at extraction time. [14][15][16][17]
- The content fingerprint is a 12-character prefix of a cryptographic hash, providing 48 bits of entropy and collision resistance across any realistic repository. [18][19]
- Deduplication of findings within each file is enforced by tracking (section, finding-text) pairs across all processing chunks. [20]
- Contradictions between source files are surfaced as high-priority signals and never silently merged; their visibility is a stated non-functional invariant. [21]
- Introspection-stage LLM responses are validated against a strict schema, making that output deterministic to validate and easy to diff between runs. [22]
- After surgical edits, citation integrity is maintained by re-anchoring references; a content-integrity invariant requires unchanged sentences to appear verbatim. [23][24]
- A heuristic scans upstream bodies for sentinel strings to prevent synthesis from placeholder or boilerplate content. [25]
- All per-file extraction notes are persisted with a UTC timestamp on every record. [26]
- A startup validation routine enforces referential integrity of the section dependency graph at module load time. [27]
- All cache writes are atomic: content is written to a sibling temporary file and then renamed into place. [28]
- Cache files are stored in a dedicated subdirectory co-located with the wiki; only final section markdown is committed to source control via a programmatically managed ignore file. [29][30]
- A monotonically incremented schema version gates all cache reads; older versions are rejected entirely and treated as empty. [31]
- Cache entries for files that leave scope are pruned at the start of each walk. [32]
- Derivation cache entries are keyed by upstream section body hash and a critic-review flag; non-reviewed entries are not reused for reviewed runs. [33]
- The short-circuit predicate enforces five simultaneous conditions before skipping aggregation and derivation stages. [34][35]
- Introspection results are persisted to disk before the extraction stage begins so the short-circuit predicate remains evaluable after a crash. [36]
- For structured-output inference calls the temperature is pinned to zero; free-text and conversational calls may vary between runs. [37]
- Prompt caching at the service level is achieved by placing the system prompt in a predictable position in every request, reducing cost and latency across many per-file calls. [38][39]
- Target-specific configuration overrides are allowlisted; unknown fields are silently ignored and parse failures fall back to environment-derived settings. [40][11]
- A process-wide settings singleton includes an explicit invalidation mechanism to support isolated test execution. [41]
- Authentication and authorization contracts are extracted from API specification files, surfacing scheme types as explicit wiki findings. [42]
- File selection applies a cheapest-first filter chain enforcing a minimum content threshold as a data-quality invariant motivated by inference model behaviour. [43]
- Relational schema extractors capture UNIQUE and NOT NULL constraints as storage invariants and indexes as performance invariants, both annotated with a migration-preservation requirement. [44]
- The tech-agnostic output invariant — no technology names in synthesized prose — is enforced in the inference system prompt and as a structural design goal. [45]

## Sources
1. `wikifi/chat.py:22`
2. `wikifi/cli.py:52-62`
3. `wikifi/deriver.py:88-95`
4. `wikifi/report.py:22`
5. `wikifi/providers/base.py:59-68`
6. `wikifi/providers/anthropic_provider.py:250-275`
7. `wikifi/report.py:13-15`
8. `wikifi/aggregator.py:195-204`
9. `wikifi/critic.py:128-145`
10. `wikifi/extractor.py:271-282`
11. `wikifi/config.py:223-227`
12. `wikifi/chat.py:126-132`
13. `wikifi/aggregator.py:162-170`
14. `wikifi/evidence.py:41-46`
15. `wikifi/extractor.py:254-265`
16. `wikifi/specialized/graphql.py:54-68`
17. `wikifi/specialized/protobuf.py:13-14`
18. `wikifi/fingerprint.py:1-17`
19. `wikifi/fingerprint.py:22-24`
20. `wikifi/extractor.py:249-253`
21. `wikifi/evidence.py:73-79`
22. `wikifi/introspection.py:43-62`
23. `wikifi/surgical.py:46-67`
24. `wikifi/surgical.py:196-234`
25. `wikifi/deriver.py:186-200`
26. `wikifi/wiki.py:135-142`
27. `wikifi/sections.py:143-156`
28. `wikifi/cache.py:298-302`
29. `wikifi/cache.py:36-42`
30. `wikifi/wiki.py:102-128`
31. `wikifi/cache.py:54-68`
32. `wikifi/orchestrator.py:120-140`
33. `wikifi/deriver.py:95-115`
34. `wikifi/aggregator.py:305-328`
35. `wikifi/orchestrator.py:243-300`
36. `wikifi/orchestrator.py:144-152`
37. `wikifi/providers/ollama_provider.py:59-69`
38. `wikifi/providers/anthropic_provider.py:195-211`
39. `wikifi/providers/openai_provider.py:8-13`
40. `wikifi/config.py:196-200`
41. `wikifi/config.py:185-193`
42. `wikifi/specialized/openapi.py:112-121`
43. `wikifi/walker.py:89-115`
44. `wikifi/specialized/sql.py:100-121`
45. `wikifi/surgical.py:57-59`
