# External-System Dependencies

The system draws on external services in three areas: language-model inference, development-time tooling integrations, and an optional document-parsing aid.

## Language-Model Inference Services

All AI inference is routed through exactly one of three backends, selected at configuration time.

| Backend | Hosting model | Authentication | Notes |
|---|---|---|---|
| Self-hosted model server | Local process, user-managed | None required | Default path; connects via a configurable HTTP endpoint |
| Anthropic hosted API | Cloud, vendor-managed | API key (environment variable) | Opt-in; supports adaptive reasoning depth; configurable per-call token cap (default 32 000) and HTTP timeout (default 900 s) to handle long inference runs |
| OpenAI-compatible hosted API | Cloud, vendor-managed (or proxy) | API key | Opt-in; base URL is overridable, enabling compatible third-party or private deployments |

The self-hosted model server is the zero-configuration default: new users can run it locally without obtaining any credentials. The two cloud options are opt-in and require API keys supplied via environment variables. Both cloud providers support configurable timeouts, token limits, and extended reasoning modes; the cloud inference path also performs structured-output decoding (schema-constrained responses returning validated domain objects), free-text completion, and multi-turn conversational exchange.

## Development-Time Tool Integrations

A separate layer of integrations, declared in the project's tool-server configuration, augments the system during development or at runtime with auxiliary capabilities:

- **Google's generative AI service** — consumed via a shared API key; powers at least two registered tool integrations, including one described as an orchestration or data-assembly capability.
- **External documentation and context lookup** — an HTTP-based service queried with its own API key to retrieve up-to-date reference material, likely used to enrich prompts with current library or API documentation.
- **Self-hosted web-crawling service** — a locally-running crawler reachable at a fixed port, requiring no API key, used to fetch and process web content on demand.

## Optional Parsing Support

When processing contract specification files in YAML format, the system can delegate parsing to a third-party YAML library if one is present in the environment. If the library is absent the system falls back to a built-in minimal parser that covers the subset of YAML constructs it needs. This makes the external library a soft, non-blocking dependency rather than a hard requirement.

## Supporting claims
- The self-hosted model server is the default inference backend, requires no API key, and is reachable at a configurable HTTP endpoint. [1][2][3]
- Anthropic's hosted inference API is an opt-in backend authenticated via an environment-variable API key, supporting adaptive reasoning modes, a configurable per-call token cap (default 32 000), and an HTTP timeout defaulting to 900 seconds. [4][2][5]
- The OpenAI-compatible hosted API is an opt-in backend authenticated via API key with a configurable base URL, enabling use of compatible third-party or private proxy deployments. [6][2][7]
- The cloud inference path supports structured-output (schema-constrained) decoding, free-text completion, and multi-turn conversational chat. [7]
- Google's generative AI service is consumed via a shared API key and powers at least two registered tool integrations, including one orchestration or data-assembly capability. [8][9]
- An HTTP-based external documentation and context lookup service is queried with its own dedicated API key, likely to enrich prompts with up-to-date reference material. [10]
- A self-hosted web-crawling service runs locally at a fixed port, requires no API key, and is used to fetch and process web content. [11]
- A third-party YAML parsing library is a soft dependency for processing YAML-format specification files; the system falls back to a built-in minimal parser when the library is absent. [12]

## Sources
1. `wikifi/config.py:53-55`
2. `wikifi/orchestrator.py:148-200`
3. `wikifi/providers/ollama_provider.py:52`
4. `wikifi/config.py:116-134`
5. `wikifi/providers/anthropic_provider.py:83-100`
6. `wikifi/config.py:136-151`
7. `wikifi/providers/openai_provider.py:113-175`
8. `.mcp.json:4-8`
9. `.mcp.json:29-35`
10. `.mcp.json:22-28`
11. `.mcp.json:14-20`
12. `wikifi/specialized/openapi.py:154-162`
