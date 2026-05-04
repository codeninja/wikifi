# Integrations

## Outbound: AI Backend Interface

Every AI-driven operation in the pipeline flows through a single abstract provider contract that every backend must satisfy. This contract exposes exactly three interaction modes — structured JSON completion, free-text completion, and multi-turn conversation — and is consumed by at least seven internal modules: the introspection stage, the extractor, the aggregator, the deriver, the critic/reviser, the chat REPL, and the orchestrator. Because all modules program to this abstraction, backends are fully interchangeable.

Three concrete backends are wired in:

| Backend | Selection mechanism | Notes |
|---|---|---|
| Hosted provider A (Claude) | default or explicit config | Adds prompt-caching optimisation for large walks |
| Hosted provider B (OpenAI) | `WIKIFI_PROVIDER=openai` env var | Upstream API errors normalised before propagation |
| Local model service (Ollama) | config selection | Runs entirely on-premises; same three interaction modes |

The orchestrator selects among them without branching on provider-specific details, and each concrete backend normalises errors into a uniform shape before returning to callers.

## Outbound: Repository and Filesystem Layer

The pipeline reads the target repository through a filesystem enumeration layer that applies ignore-file semantics. The introspection stage calls this layer to obtain a compressed structural view (tree summary and manifest files); the orchestrator calls it again to drive the per-file extraction pass. The enumeration layer itself has no knowledge of AI providers or downstream stages.

The extractor additionally consults a repo-wide import graph to obtain each file's cross-file neighborhood (up to eight neighbors), enriching every AI extraction prompt with context that spans module boundaries.

## Internal Integration Bus

The on-disk wiki layout acts as a shared artifact bus between all four pipeline stages:

- **Stage 1 → Stage 2**: introspection writes the list of paths to analyse; the extractor reads it.
- **Stage 2 → Stage 3**: the extractor appends structured per-section notes (JSONL) via `append_note`; the aggregator reads them via `read_notes`.
- **Stage 3 → Stage 4**: the aggregator writes finalised section markdown via `write_section`; the deriver and report modules read those bodies.

A walk cache provides a second shared data channel: the extractor records fingerprint-keyed results; the deriver and report stages read the cache to determine total file coverage and avoid redundant work.

The orchestrator is the central wiring point for all of these internal calls, threading settings, cache handles, layout references, and the chosen provider through each stage in sequence.

## Outbound: Quality-Review Services

The critic and reviser are called as a service by the deriver (optionally, after synthesis) and by the report module (to produce context-aware quality scores). Both delegate to the shared AI provider, passing typed schemas to obtain structured critique and revision outputs. Section metadata — title, identifier, and brief — is sourced from the canonical sections registry and used to build evaluation prompts.

## Inbound: Surfaces Discovered in the Target Codebase

When the pipeline analyses the target repository, specialised extractors classify inbound integration touchpoints found in contract and schema files:

- **HTTP API surface**: endpoints described in OpenAPI/Swagger contract files are surfaced as inbound-facing integration points, with endpoint count and identity captured for migration consumers.
- **Remote procedure call services**: each service block in a protocol interface-definition file is recorded as an integration touchpoint, with each operation's name, request type, response type, and streaming direction (client, server, or bidirectional) preserved.
- **Real-time event subscriptions**: subscription root declarations in schema definition files are classified as inbound integration touchpoints — external consumers subscribe to these rather than invoking them imperatively.
- **Relational foreign-key links**: foreign key constraints are surfaced as directed coupling between entities (`source.column → target.column`), representing integration contracts at the storage layer.

File routing to these specialised extractors is handled by a dispatcher that consumes a file-kind classification from the import graph layer, falling back to the general AI extraction path for unrecognised kinds.

## Inbound: Command-Line Entry Point

The command-line interface is the outermost entry point for human-initiated operations. It exposes four commands (initialise, walk, chat, report) and delegates each to the appropriate internal subsystem: the orchestrator for pipeline execution, the cache module for cache management, the chat REPL for interactive conversation, the config module for settings resolution, and the report module for quality reporting.

## Supporting claims
- Every AI-driven operation flows through a single abstract provider contract consumed by at least seven internal modules. [1]
- The contract exposes exactly three interaction modes: structured JSON completion, free-text completion, and multi-turn conversation. [1][2]
- Three concrete backends exist: a hosted provider (Claude), a hosted provider (OpenAI), and a local model service (Ollama). [3][2][4]
- The orchestrator selects among backends without branching on provider-specific details. [3][4]
- Upstream API errors from the OpenAI backend are normalised into a uniform error shape before propagating to the orchestrator. [4]
- The filesystem enumeration layer is called by the introspection stage (for tree summary and manifest files) and by the orchestrator (for per-file iteration), but has no knowledge of AI providers or downstream stages. [5]
- The extractor consults a repo-wide import graph to obtain up to eight cross-file neighbors per file, enriching extraction prompts with multi-module context. [6][7]
- The on-disk wiki layout acts as a shared artifact bus: the extractor appends notes, the aggregator reads and writes section markdown, and the deriver and report modules consume those bodies. [8][9]
- A walk cache provides a second shared data channel used by the extractor for fingerprint-based storage and by the report module for file-coverage counts. [10][11][12]
- The orchestrator is the central integration hub, wiring settings, cache, layout, and provider through introspection, extraction, aggregation, and derivation stages. [13]
- The critic and reviser are called as a service by the deriver and the report module, both delegating to the shared AI provider with structured output schemas. [14][15][16]
- Section metadata (title, identifier, brief) is sourced from the canonical sections registry and used to build critic and reviser prompts. [17]
- OpenAPI/Swagger contract files are analysed to surface the inbound HTTP endpoint surface as integration findings. [18]
- Each service block in a protocol interface-definition file is recorded as an integration touchpoint, with each RPC's operation name, request/response types, and streaming direction captured. [19]
- GraphQL subscription root declarations are classified as inbound integration touchpoints representing real-time event streams for external consumers. [20]
- Foreign key constraints are surfaced as directed coupling between storage entities, representing integration contracts at the storage layer. [21]
- File routing to specialised extractors is handled by a dispatcher that consumes a file-kind classification from the import graph layer. [7]
- The command-line interface is the outermost entry point, delegating to the orchestrator, cache, chat REPL, config, and report subsystems. [22]

## Sources
1. `wikifi/providers/base.py:40-56`
2. `wikifi/providers/ollama_provider.py:46-90`
3. `wikifi/providers/anthropic_provider.py:76-78`
4. `wikifi/providers/openai_provider.py:1-10`
5. `wikifi/walker.py:1-11`
6. `wikifi/extractor.py:252-256`
7. `wikifi/specialized/dispatch.py:46-65`
8. `wikifi/aggregator.py:46-47`
9. `wikifi/extractor.py:289-295`
10. `wikifi/extractor.py:186-200`
11. `wikifi/report.py:131-143`
12. `wikifi/surgical.py:40-46`
13. `wikifi/orchestrator.py:89-226`
14. `wikifi/critic.py:111-120`
15. `wikifi/deriver.py:70-90`
16. `wikifi/report.py:121-126`
17. `wikifi/critic.py:150-165`
18. `wikifi/specialized/openapi.py:88-95`
19. `wikifi/specialized/protobuf.py:66-90`
20. `wikifi/specialized/graphql.py:103-104`
21. `wikifi/specialized/sql.py:96-107`
22. `wikifi/cli.py:22-27`
