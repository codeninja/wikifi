# Cross-Cutting Concerns

## Observability

Logging is a first-class, globally applied concern. At startup, a verbosity flag controls whether the runtime emits debug-level or INFO-level output; this choice is applied before any pipeline stage executes, so every downstream component inherits a consistent logging posture. Structured log lines are emitted at the entry point of each pipeline stage, giving operators a reliable breadcrumb trail across introspection, extraction, aggregation, and derivation.

Diagnostic quality is also enforced at the inference boundary: when a model call produces no usable output, the system surfaces the stop reason, token counts, and the configured budget, together with actionable remediation hints. All backend providers share a single error-formatting routine that extracts any vendor-issued request identifier when present, ensuring failure messages are uniformly attributable regardless of which backend is in use.

## Graceful Degradation

The pipeline is designed so that no single failure propagates to a total abort:

- **Per-chunk and per-file extraction failures** are isolated; a failed chunk does not stop the rest of the file, and a failed file does not stop the walk. Single-chunk files that fail entirely are counted as skipped rather than silently lost.
- **Aggregation failures** are logged at WARNING level and result in a fallback body that preserves the raw notes verbatim, guaranteeing that every section is written.
- **Derivation failures** likewise produce a fallback body that retains upstream evidence, keeping the wiki inspectable after partial failures.
- **Critic and reviser failures** degrade gracefully by returning the original body and recording a score of zero with a diagnostic message.
- **Cache I/O failures** (missing files, malformed records, bad individual entries) are logged as warnings and fall back to an empty cache, preserving pipeline continuity.
- **Chat-session inference failures** are surfaced as inline messages rather than terminating the interactive session.

A per-request timeout is enforced on all inference calls, preventing indefinite hangs during long reasoning passes.

## Data Integrity and Provenance

Full source provenance is a non-negotiable invariant. Every finding emitted by any extraction path carries the relative file path, an absolute line range (chunk-relative ranges are translated to file-absolute positions before storage), and a content fingerprint. This citation chain is preserved through caching and replay, so the aggregation stage can always render accurate source links.

Contradictions discovered in source material are **never silently resolved**. They are always surfaced explicitly in the output so that incompatibilities visible in the source are escalated to the migration team rather than hidden.

Finding deduplication is enforced within a single file across all its chunks, preventing overlapping analysis windows from producing duplicate wiki entries.

### Hallucination Prevention

Grounding in real evidence is enforced at multiple levels:

| Level | Mechanism |
|---|---|
| Prompt contract | The assistant is instructed to acknowledge explicitly when the wiki does not cover a topic rather than extrapolating.[15] |
| Output terminology | The synthesiser is instructed to translate all observations into domain terms, never naming implementation-specific artefacts.[16] |
| Derivative sections | A heuristic filters placeholder bodies before they can be treated as real upstream evidence; an optional critic-and-reviser loop then scores and revises each derivative section before it is written. |
| Placeholder detection | A fixed set of sentinel strings identifies unpopulated sections; these are excluded from quality scoring and cannot seed downstream derivation. |

Revision events are counted in run statistics so operators can observe how often the quality loop intervenes.

## Caching and Cache Integrity

Content fingerprints (short, stable hashes derived from raw bytes rather than decoded text) serve three cross-cutting roles simultaneously: keying the extraction and aggregation caches, anchoring source-evidence citations, and tracking file identity inside the dependency graph.

The aggregation cache key is designed to be maximally conservative: it includes each referenced source file's fingerprint **and** its line range alongside the finding text. This means that when any referenced file changes, the cache misses and citations are re-derived from fresh evidence rather than replayed from stale data.

Cache files are stored in a designated subdirectory co-located with the wiki output and governed by the same repository-ignore rules, keeping them out of version control without extra configuration. When caching is explicitly disabled, the cache store is reset at run start to prevent stale data from influencing results; when caching is enabled, entries for files no longer in scope are pruned to keep cache size proportional to the live working set.

Operators can also force a full cache invalidation at the command line to guarantee a fresh analysis after source changes.

## Configuration Safety

Configuration resolution follows a strict, documented precedence order: a project's own configuration file overrides process-wide environment variables, which override compiled-in defaults. This ensures that a wiki initialised for a specific backend continues to use that backend regardless of the operator's shell environment.

To prevent accidental side-effects, only a small, named set of fields (backend provider, model identifier, and local service host) may be overridden by a project-level configuration file. All other settings are controlled exclusively at the process level, so stale or hand-edited project configs cannot silently alter pipeline behaviour the user did not intend to change.

## Authentication and Authorization

Authentication schemes declared in API contract files are captured as explicit findings during extraction. The scheme categories recorded include API-key, bearer-token, and OAuth flows. These are surfaced as migration-relevant intelligence so that the target system's authentication implementation can be verified against the source contract.

## Storage Invariants

Schema analysis produces structured findings that the migration team must honour in the target system:

- **Uniqueness and nullability constraints** on any table are surfaced as explicit storage invariants.
- **Index definitions** are flagged as query-time performance invariants annotated as requirements the new system must preserve.
- **Migration history** is tracked separately from baseline schema definitions: tables touched by incremental schema-change operations are counted distinctly from those established in the original schema, ensuring that alter-only migrations are not misleadingly reported as empty.

## Input Filtering

To prevent speculative or low-quality inference, the pipeline applies size guards before any file reaches an analysis model:

- Files exceeding a fixed size threshold are dropped on the assumption that they are vendored, generated, or binary assets.
- Files whose text content is shorter than a minimum byte threshold are also dropped to prevent hallucinated findings on effectively empty inputs.
- Manifest files read for structural context are hard-truncated at a maximum byte count with a visible marker, keeping prompt payloads bounded.

Directory traversal prunes excluded subtrees before descending, so exclusion patterns are applied efficiently at the directory level rather than file-by-file.

## Audit Trail

Every per-file extraction record is stamped with a UTC timestamp at write time, providing an audit trail of when each finding was recorded. The repository-ignore file for the wiki directory is actively maintained: any required exclusion entries missing from an older configuration are backfilled on each initialisation run, preventing local working state from surfacing as untracked changes after a tool upgrade.

## Structured Output Determinism

All structured-output inference calls use a fixed temperature of zero, ensuring that the same input always produces the same structured result across runs. This is treated as a non-negotiable invariant for the extraction path. Model output is additionally constrained to a strict schema, enabling deterministic parsing and straightforward diffing between runs. Both LLM-based and specialised (deterministic) extractors write to the same notes store under the same contract, so the downstream aggregation pipeline is agnostic to which extraction path produced a given finding.

## Supporting claims
- Logging verbosity is controlled by a runtime flag applied globally before any pipeline stage executes. [1]
- Structured log lines are emitted at the entry point of each pipeline stage. [2]
- When a model call produces no usable output, the system surfaces the stop reason, token counts, and configured budget with actionable remediation hints. [3]
- All backend providers share a single error-formatting routine that extracts any vendor-issued request identifier, ensuring uniform failure attribution. [4]
- Per-chunk and per-file extraction failures are isolated; a failed chunk does not stop the rest of the file, and a failed file does not stop the walk. [5]
- Aggregation failures are logged at WARNING level and produce a fallback body that preserves the raw notes verbatim. [6]
- Derivation failures produce a fallback body retaining upstream evidence verbatim. [7]
- Critic and reviser failures degrade gracefully by returning the original body and recording a score of zero with a diagnostic message. [8]
- Cache I/O failures are logged as warnings and fall back to an empty cache, preserving pipeline continuity. [9]
- Chat-session inference failures are surfaced as inline messages rather than terminating the interactive session. [10]
- A per-request timeout is enforced on all inference calls to prevent indefinite hangs. [11]
- Every finding carries the relative file path, absolute line range, and content fingerprint as source provenance. [12]
- Contradictions discovered in source material are never silently resolved; they are always surfaced explicitly. [13]
- Finding deduplication is enforced within a single file across all its chunks. [14]
- A heuristic filters placeholder bodies before they can be treated as real upstream evidence, and an optional critic-and-reviser loop scores and revises each derivative section. [17]
- A fixed set of sentinel strings identifies unpopulated sections, which are excluded from quality scoring and cannot seed downstream derivation. [18][19]
- Revision events are counted in run statistics for observability. [17]
- Content fingerprints are derived from raw bytes rather than decoded text, ensuring consistent hashing regardless of encoding assumptions. [20]
- Content fingerprints serve three cross-cutting roles: cache keying, source-evidence citation anchoring, and dependency-graph invalidation. [21]
- The aggregation cache key includes each referenced source file's fingerprint and line range, so any change causes a cache miss and fresh re-derivation. [22]
- Cache files are stored in a designated subdirectory co-located with wiki output and governed by repository-ignore rules. [23]
- When caching is disabled the cache store is reset at run start; when enabled, out-of-scope entries are pruned. [24]
- Operators can force full cache invalidation at the command line. [25]
- Configuration resolution follows a strict precedence: project config file overrides environment variables, which override compiled-in defaults. [26]
- Only a small named set of fields may be overridden by a project-level configuration file; all other settings are process-level only. [27]
- Authentication scheme categories declared in API contract files are captured as explicit findings. [28]
- Uniqueness and nullability constraints are surfaced as explicit storage invariants the target system must honour. [29]
- Index definitions are flagged as query-time performance invariants the new system must preserve. [29]
- Migration history is tracked separately from baseline schema, ensuring alter-only migrations are not reported as touching zero tables. [30]
- Files exceeding a maximum size threshold are dropped; files shorter than a minimum byte threshold are also dropped to prevent hallucinated findings. [31]
- Manifest files read for structural context are hard-truncated at a maximum byte count with a visible marker. [32]
- Directory traversal prunes excluded subtrees before descending, applying exclusion patterns at the directory level. [33]
- Every per-file extraction record is stamped with a UTC timestamp at write time. [34]
- The repository-ignore file for the wiki directory is backfilled with any missing required entries on each initialisation run. [35]
- All structured-output inference calls use a fixed temperature of zero, ensuring deterministic structured results across runs. [36]
- Model output is constrained to a strict schema enabling deterministic parsing and diffing between runs. [37]
- Both LLM-based and specialised extractors write to the same notes store under the same contract, making the aggregation pipeline agnostic to extraction path. [38]
- API errors from hosted backends are caught and re-raised as a uniform internal error type, preventing provider-specific error shapes from leaking into the orchestration layer. [39][40]

## Sources
1. `wikifi/cli.py:53-61`
2. `wikifi/orchestrator.py:103-145`
3. `wikifi/providers/anthropic_provider.py:255-275`
4. `wikifi/providers/base.py:54-63`
5. `wikifi/extractor.py:192-198`
6. `wikifi/aggregator.py:143-152`
7. `wikifi/deriver.py:96-107`
8. `wikifi/critic.py:158-165`
9. `wikifi/cache.py:162-168`
10. `wikifi/chat.py:120-125`
11. `wikifi/config.py:56-57`
12. `wikifi/extractor.py:240-256`
13. `wikifi/evidence.py:1-18`
14. `wikifi/extractor.py:224-234`
15. `wikifi/chat.py:27-31`
16. `wikifi/aggregator.py:54-67`
17. `wikifi/deriver.py:110-135`
18. `wikifi/deriver.py:118-135`
19. `wikifi/report.py:103-108`
20. `wikifi/fingerprint.py:44-50`
21. `wikifi/fingerprint.py:1-18`
22. `wikifi/cache.py:243-255`
23. `wikifi/cache.py:18-20`
24. `wikifi/orchestrator.py:108-116`
25. `wikifi/cli.py:107-110`
26. `wikifi/config.py:28-44`
27. `wikifi/config.py:161-167`
28. `wikifi/specialized/openapi.py:118-126`
29. `wikifi/specialized/sql.py:100-121`
30. `wikifi/specialized/sql.py:123-130`
31. `wikifi/walker.py:61-79`
32. `wikifi/walker.py:220-231`
33. `wikifi/walker.py:133-143`
34. `wikifi/wiki.py:136-141`
35. `wikifi/wiki.py:103-126`
36. `wikifi/providers/ollama_provider.py:58-68`
37. `wikifi/introspection.py:5-9`
38. `wikifi/specialized/models.py:4-8`
39. `wikifi/providers/anthropic_provider.py:119-127`
40. `wikifi/providers/openai_provider.py:128-135`
