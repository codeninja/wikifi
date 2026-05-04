# Integrations

## Outbound Integrations

### Language-Model Providers

The system maintains a uniform provider abstraction that isolates every pipeline stage from the concrete inference backend. Three selectable backends are supported — a locally-hosted model service, a hosted Anthropic-compatible service, and an OpenAI-compatible service — each implementing the same three-method contract: structured JSON completion, free-text completion, and multi-turn chat. The active backend is chosen by configuration; the orchestrator and all downstream stages call into it without branching on which concrete provider is live.

Every stage that performs inference uses this abstraction:

| Stage | Operation |
|---|---|
| Introspection (Stage 1) | Structured JSON completion to classify repository paths |
| Extraction (Stage 2) | Structured JSON completion against a findings schema, per file |
| Aggregation (Stage 3) | Structured JSON completion against a section-body schema |
| Derivation (Stage 4) | Structured completion for personas, user stories, and diagrams |
| Critic / Reviser | Structured completion for rubric scoring and body revision |
| Chat session | Multi-turn chat grounded in populated wiki content |

### External Tool and Capability Servers

At the development and runtime boundary, the system is configured as a client that fans out to multiple external capability providers via a tool-server protocol. Four integrations are declared: a local AI utility, a local web crawler, a remote documentation context service, and a remote stitching/search service. This makes the system both a producer of wiki content and a consumer of external knowledge services during operation.

### Filesystem and Layout Abstraction

All pipeline stages read and write through a shared filesystem layout abstraction rather than addressing paths directly. Extraction findings are appended to a notes store; aggregated section bodies are written back through the same abstraction; the report and chat components read section markdown from the same on-disk layout. The cache layer uses this abstraction to locate its storage directory, and all cache reads and writes (keyed on file fingerprints and section-content hashes) pass through it.

### Import Graph

The extraction stage integrates with a repository-wide import/reference graph. For each file being analysed, the graph supplies the file's direct neighbors — files it depends on and files that depend on it — which are injected into the extraction prompt to enable cross-file flow descriptions. The graph also drives the specialized-extractor dispatch path by classifying each file's structural kind before routing.

### Per-Project Configuration

Project-specific provider selection, model preferences, caching behavior, and feature flags are read from a TOML configuration file stored inside each managed project's wiki directory. Parse failures fall back gracefully to environment-derived defaults rather than aborting the pipeline.

---

## Inbound Integrations

The primary entry point is the command-line interface, which exposes four subcommands (`init`, `walk`, `chat`, `report`). It constructs the provider instance and passes it directly into the chat and report capabilities. All other pipeline stages are driven by the orchestrator, which sequences introspection → extraction → aggregation → derivation and is itself invoked by the CLI `walk` subcommand.

---

## Integration Surfaces Detected in Analysed Codebases

When the system analyses a target repository, it surfaces the following categories of integration touchpoint:

- **HTTP API endpoints** — each parsed API contract contributes a finding recording the number of endpoints the analysed system exposes to external consumers, forming the inbound integration inventory.
- **RPC service blocks** — each service definition is treated as an integration touchpoint; individual operations are described with their request and response types, including streaming direction where declared.
- **Event-driven subscriptions** — subscription roots in schema definition files are mapped specifically to the integrations section, reflecting that they represent event-driven touchpoints rather than direct request/response capabilities.
- **Relational foreign-key links** — cross-table references are recorded as hard relational links between entities, surfacing constraints that affect how components may be separated or migrated independently.

The specialized extractor dispatch layer acts as the internal routing hub between the upstream file classifier (which tags file kinds) and the downstream extractors responsible for each artifact type. Files that do not match a recognized kind fall through to the general LLM extraction path.

## Supporting claims
- Three selectable LLM backends are supported — a locally-hosted model service, a hosted Anthropic-compatible service, and an OpenAI-compatible service. [1][2][3]
- Each backend implements the same three-method contract: structured JSON completion, free-text completion, and multi-turn chat. [1][2][3]
- The orchestrator and all downstream stages call into the provider without branching on which concrete provider is active. [4][1][2][3]
- The introspection stage uses structured JSON completion to classify repository paths. [5]
- The extraction stage uses structured JSON completion against a findings schema, per file. [6]
- The aggregation stage uses structured JSON completion against a section-body schema. [7]
- The critic/reviser uses structured completions for rubric scoring and body revision. [8]
- The chat session uses multi-turn chat grounded in populated wiki content. [9]
- Four external tool-server integrations are declared: a local AI utility, a local web crawler, a remote documentation context service, and a remote stitching/search service, making the system an MCP client that fans out to multiple capability providers. [10]
- All pipeline stages read and write through a shared filesystem layout abstraction; the cache layer uses this abstraction to locate its storage directory. [11][12][13][14][15][16]
- The extraction stage integrates with a repository-wide import/reference graph; each file's neighbors are injected into the extraction prompt. [17][18]
- The import graph also drives the specialized-extractor dispatch path by classifying each file's structural kind. [18][19]
- Project-specific settings are read from a TOML configuration file inside each managed project's wiki directory; parse failures fall back gracefully to defaults. [20][21]
- The CLI constructs the provider instance and passes it directly into the chat and report capabilities. [4]
- Each parsed API contract contributes a finding recording the number of HTTP endpoints the analysed system exposes to external consumers. [22]
- Each RPC service block in a protocol definition is treated as an integration touchpoint, with operations described including streaming direction. [23]
- Subscription roots are mapped specifically to the integrations section, reflecting event-driven touchpoints. [24]
- Cross-table foreign-key references are recorded as hard relational links between entities, surfacing migration constraints. [25]
- The specialized extractor dispatch layer routes recognized file kinds to dedicated extractors; unrecognized files fall through to the general LLM extraction path. [26][19][27]
- Derivative sections are excluded from the aggregation stage and are instead populated by a separate deriver stage that runs afterwards. [28][14]

## Sources
1. `wikifi/providers/anthropic_provider.py:83-106`
2. `wikifi/providers/ollama_provider.py:44-46`
3. `wikifi/providers/openai_provider.py:1-9`
4. `wikifi/cli.py:176-179`
5. `wikifi/introspection.py:61-70`
6. `wikifi/extractor.py:220-235`
7. `wikifi/aggregator.py:136-141`
8. `wikifi/critic.py:30-32`
9. `wikifi/chat.py:52-55`
10. `.mcp.json:2-36`
11. `wikifi/aggregator.py:109-160`
12. `wikifi/cache.py:30-32`
13. `wikifi/chat.py:63-82`
14. `wikifi/deriver.py:73-107`
15. `wikifi/extractor.py`
16. `wikifi/report.py:78-130`
17. `wikifi/extractor.py:213-215`
18. `wikifi/repograph.py:1-10`
19. `wikifi/specialized/dispatch.py:36-62`
20. `wikifi/cli.py:103-105`
21. `wikifi/config.py:169-200`
22. `wikifi/specialized/openapi.py:96-103`
23. `wikifi/specialized/protobuf.py:64-90`
24. `wikifi/specialized/graphql.py:108-110`
25. `wikifi/specialized/sql.py:88-98`
26. `wikifi/specialized/__init__.py:7-8`
27. `wikifi/specialized/models.py:30-31`
28. `wikifi/aggregator.py:111-116`
