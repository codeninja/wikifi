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
