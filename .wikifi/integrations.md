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
