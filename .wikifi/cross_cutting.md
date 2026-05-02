# Cross-Cutting Concerns

## Observability

A consistent, pipeline-wide observability model spans every stage of the system. Structured logging is initialised once and reused across all subcommands; a single verbose flag activates debug-level output globally without each subsystem needing its own toggle. Stage-boundary log events are emitted at each major transition — repository introspection, dependency-graph construction, file extraction, section aggregation, and derivative synthesis — so operators can pinpoint where a long walk is spending time. Revision and quality-scoring events are counted in the run's statistics, and cache hit counts are surfaced in the post-walk report, giving a quantitative picture of incremental efficiency.

## Resilience and Error Handling

The system is designed so that no single failure can abort an entire pipeline run. Extraction failures — whether caused by an inference provider or a specialised deterministic parser — are logged and tallied but never propagated upward; a file whose processing fails entirely is recorded as skipped, and partially-recovered files retain whatever findings were salvaged. Aggregation and derivation failures follow the same pattern: errors are caught and logged at warning level, and a fallback body that preserves the raw upstream evidence is written so the wiki remains inspectable. Quality-assurance (critic and reviser) failures degrade gracefully to returning the original body with a diagnostic score of zero rather than halting. Provider failures during interactive query sessions are surfaced inline without terminating the session. Across all provider backends, raw infrastructure errors are caught at the provider boundary and re-raised as a normalised internal error type carrying the upstream request identifier when available, so the rest of the pipeline does not branch on provider-specific exception shapes.

## Content-Addressed Caching and Crash Resumability

All expensive inference work is protected by a two-scope content-addressed cache stored under a dedicated hidden subdirectory within the wiki output directory, inheriting the same version-control ignore rules as other working-state artifacts.

- **Extraction scope:** each file's results are keyed by the combination of its relative path and a stable hash of its raw bytes. Any unchanged file is skipped on re-walk with no inference call.
- **Aggregation scope:** each section's synthesised body is keyed by a deterministic digest of its note payload. Unchanged inputs reuse the stored body and evidence bundle.

Cache entries are written after every individual file completes, so a mid-walk crash loses at most one file's work. Writes are performed atomically — content is first written to a temporary location and then renamed into place — preventing corrupt partial writes. Malformed entries are silently dropped and logged rather than causing a hard failure, so a partially corrupt cache degrades gracefully to a fresh extraction for only the affected entries. A monotonically increasing version tag is embedded in every persisted cache file; a version mismatch on load causes the entire cache to be discarded and rebuilt, providing a controlled invalidation path across software upgrades. Between runs, entries for files no longer in scope are pruned automatically.

## Input Integrity Guards

A layered set of guards prevents low-signal or pathological inputs from ever reaching the inference layer.

| Guard | Threshold | Effect |
|---|---|---|
| Minimum content size | 64 bytes (stripped) | File silently skipped |
| Maximum file size | 2 MB | File silently skipped |
| Large-file windowing | 150 KB – 2 MB | File split into overlapping chunks with 8 KB overlap |
| Manifest truncation | 20 000 bytes | Hard-truncated with visible marker |
| Per-request timeout | 900 seconds | Uniform backstop across all providers |

Directory traversal prunes excluded subtrees before descending into them, so ignore patterns are applied efficiently at the directory level rather than file-by-file. Files carrying no extractable intent — stub initialisers, empty fixtures, generated lockfiles — are identified and dropped before reaching the inference layer; the invariant that a single empty or unstructured file must never stall the walk is explicitly upheld. Findings produced from the overlap region between adjacent large-file chunks are deduplicated by section and normalised text within each file's pass, preventing double-counting in downstream aggregation.

## Provider Abstraction

All inference calls — structured extraction, free-text generation, and multi-turn chat — are routed through a single provider abstraction layer. This boundary is where observability hooks, retry logic, error normalisation, and backend-switching concerns live; no extraction or aggregation logic needs knowledge of which backend is active. Supported backend shapes include local inference runtimes and hosted services; the local-inference path is the default, with hosted options as addenda, and swapping between them requires no changes outside the provider boundary.

Structured-output calls enforce a schema-validation contract: the model response must be validated against a declared schema before being returned to the caller, ensuring type-safe data flows through every pipeline stage. To maximise determinism, temperature is hard-pinned to zero on all structured-output calls; free-text and conversational paths accept model-default variability in exchange for naturalness.

When a backend exposes a reasoning-depth control, the system runs at the highest available setting, prioritising output quality over walk speed. A configurable depth parameter is translated into the provider's native adaptive-thinking feature, allowing callers to trade latency and cost against quality without branching on provider type in shared pipeline code.

Hosted backends employ prompt-caching strategies — placing the large, repeated system prompt at a fixed position in every request so the service can serve subsequent calls from a cached prefix — making large-scale walks economically viable by paying full input cost only on the first call and a fraction of that cost on subsequent ones.

## Source Traceability and Hallucination Prevention

Full source traceability is a non-negotiable structural invariant: every assertion in every wiki section must be linkable back to the originating file and, where available, the precise line range within it. This is enforced through typed evidence structures (claims and source references) rather than by convention, so the constraint cannot be silently bypassed.

Hallucination prevention operates at two additional levels. First, the inference prompt explicitly instructs the model never to name specific technologies, translating all observations into domain terms — this is a mandatory invariant enforced at the prompt layer. Second, upstream section content that matches known placeholder shapes is filtered out before derivative synthesis, preventing empty or stub sections from being treated as real evidence; these same sentinel strings are used by the quality-report layer to exclude placeholder sections from scoring. Interactive query sessions are similarly grounded: the assistant is instructed to explicitly acknowledge when the wiki does not cover a topic rather than generating unsupported answers.

Content fingerprints serve a triple cross-cutting role: keying both extraction and aggregation caches so stale results are never served, anchoring source-evidence citations so claims can be re-verified against a fresh repository walk, and tracking file identity inside the dependency graph so cross-file context is invalidated when any contributing source changes. Files are always fingerprinted as raw bytes rather than decoded text to ensure the cache layer and the extractor agree on identity regardless of encoding assumptions.

## Authentication and Storage Invariants

Specialised deterministic parsers extract security and data-integrity contracts from high-signal artifacts and surface them as first-class cross-cutting concerns that must be preserved through any migration:

- **Authentication schemes** declared in API contract files are extracted and categorised by type, flagging which security contracts (key-based, delegated authorisation, bearer-token, etc.) the new system must honour.
- **Data integrity constraints** — uniqueness and non-nullability — found in schema definitions are extracted as storage invariants explicitly marked as migration-critical.
- **Query-performance invariants** — index definitions — are recorded with an explicit note that the new system must preserve equivalent access patterns.

All specialised parsers return results in the same structured shape as the general inference extractor, so the aggregation layer needs no knowledge of which extraction path was taken; this uniform interface contract is itself an invariant that must be preserved.

## Data Storage Layout

The pipeline's working state is isolated to a single hidden directory within the repository:

- **Rendered section documents** live at the root of this directory and are intended to be committed to version control.
- **Per-section extraction notes** (JSONL, each record UTC-timestamped) are stored in a notes subdirectory and excluded from version control via a generated ignore file.
- **Extraction and aggregation caches** are stored in a cache subdirectory and similarly excluded.

Deleting the cache subdirectory forces a full re-walk; deleting the entire working directory resets all pipeline state. This layout ensures generated documentation commits remain clean and the boundary between committed outputs and ephemeral working state is unambiguous.

## Sources
1. `wikifi/cli.py:51-60`
2. `wikifi/orchestrator.py:84-148`
3. `wikifi/cli.py:90-97`
4. `wikifi/deriver.py:110-135`
5. `wikifi/report.py:22`
6. `wikifi/extractor.py:228-242`
7. `wikifi/aggregator.py:143-152`
8. `wikifi/deriver.py:96-107`
9. `wikifi/critic.py:158-165`
10. `wikifi/chat.py:120-125`
11. `wikifi/providers/anthropic_provider.py:238-244`
12. `wikifi/providers/openai_provider.py:248-255`
13. `README.md:40-43`
14. `wikifi/fingerprint.py:1-18`
15. `wikifi/aggregator.py:126-155`
16. `TESTING-AND-DEMO.md:67-88`
17. `wikifi/extractor.py:155-175`
18. `wikifi/cache.py:189-193`
19. `wikifi/cache.py:196-222`
20. `wikifi/cache.py:38`
21. `wikifi/orchestrator.py:95-110`
22. `wikifi/cache.py:19-21`
23. `wikifi/config.py:56-59`
24. `wikifi/walker.py:61-79`
25. `wikifi/config.py:38-56`
26. `wikifi/walker.py:220-231`
27. `.env.example:16-29`
28. `wikifi/config.py:33-34`
29. `wikifi/walker.py:133-143`
30. `README.md:44-46`
31. `VISION.md:99-100`
32. `wikifi/extractor.py:253-262`
33. `CLAUDE.md:53-54`
34. `VISION.md:92-96`
35. `wikifi/providers/base.py:36-38`
36. `wikifi/providers/ollama_provider.py:58-68`
37. `VISION.md:97-98`
38. `wikifi/providers/anthropic_provider.py:212-232`
39. `wikifi/providers/anthropic_provider.py:193-210`
40. `wikifi/providers/openai_provider.py:13-17`
41. `wikifi/evidence.py:1-18`
42. `wikifi/aggregator.py:54-67`
43. `wikifi/deriver.py:118-135`
44. `wikifi/report.py:118-123`
45. `wikifi/chat.py:27-31`
46. `wikifi/fingerprint.py:44-50`
47. `wikifi/specialized/openapi.py:110-121`
48. `wikifi/specialized/sql.py:97-98`
49. `wikifi/specialized/sql.py:113-125`
50. `wikifi/specialized/__init__.py:9-13`
51. `TESTING-AND-DEMO.md:249-265`
52. `wikifi/wiki.py:96-121`
