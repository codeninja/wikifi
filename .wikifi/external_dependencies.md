# External-System Dependencies

The system depends on external services in two areas: the **language-model inference layer** that drives all AI analysis, and a set of **tooling integrations** used for development support and runtime enrichment.

### Language-Model Inference

Three mutually exclusive inference backends are supported; exactly one is active per deployment.

| Backend | Role | Authentication | Key Configuration |
|---|---|---|---|
| Self-hosted local inference service | Default LLM backend; serves models over HTTP on the local network | None required | Configurable host address and request timeout |
| Anthropic's hosted inference API | Opt-in cloud backend for high-capability extraction | API key (environment variable) | Configurable output-token cap and HTTP timeout to manage long-running calls; supports adaptive reasoning depth |
| OpenAI-compatible hosted inference API | Opt-in cloud backend for structured decoding, completion, and chat | API key | Configurable base URL, enabling compatible proxy or alternate deployment targets |

The self-hosted local service is the default and the zero-friction starting point for new users — it requires no credentials and no cloud account. The two hosted cloud services are opt-in alternatives that require API keys and expose additional parameters for latency and cost control.

The local backend supports reasoning-capable model variants that trade increased latency for greater analytical depth; this extended-reasoning mode is also available on the hosted cloud backends.

The Anthropic-backed path operates in a single structured-extraction mode. The OpenAI-compatible path supports three distinct usage modes: schema-constrained structured decoding (returning validated domain objects), free-text completion, and multi-turn conversational chat.

### Development and Runtime Tooling Integrations

Several additional services are configured in the tooling layer:

- **Self-hosted web-crawling service** — runs locally on a fixed port with no external credentials required. Provides on-demand web-crawling capability, used to gather source material.
- **Google's hosted AI/generative API** — authenticated via a dedicated API key; consumed by at least two registered tool integrations.
- **External documentation context service** — called over HTTP using a dedicated API key; enriches prompts or retrieves up-to-date reference documentation at runtime.
- **Google-hosted orchestration service** — an HTTP service authenticated via the same Google API key; its exact role is not fully specified in available sources but is likely related to data composition or workflow orchestration.

### Soft Dependency: Structured-Data Parsing

When processing structured API contract files, the system can optionally leverage an external YAML parsing library for full format support. If that library is absent, an internal minimal parser serves as a fallback, covering the specific fields the system requires. This is a soft rather than hard dependency — the system remains functional without it.

## Supporting claims
- Three mutually exclusive LLM inference backends are supported: a self-hosted local service, Anthropic's hosted API, and an OpenAI-compatible hosted API. [1][2][3][4][5]
- The self-hosted local inference service is the default backend, requires no API key, and connects over a configurable HTTP endpoint. [1][2][5][6]
- The self-hosted local service supports reasoning-capable model variants that trade latency for greater analytical depth. [1][6]
- Anthropic's hosted inference API is an opt-in backend authenticated via an environment-variable API key, with a configurable output-token cap and HTTP timeout to manage long-running inference calls. [3][5][7]
- Anthropic's hosted backend supports an adaptive reasoning depth mode. [3][7]
- The OpenAI-compatible hosted API is an opt-in backend authenticated via API key, with a configurable base URL enabling use of compatible proxy deployments. [4][5][8]
- The OpenAI-compatible backend supports three usage modes: schema-constrained structured decoding, free-text completion, and multi-turn conversational chat. [8]
- A self-hosted web-crawling service runs locally on a fixed port and requires no external credentials. [9]
- Google's hosted AI/generative API is consumed by at least two tool integrations, authenticated via a dedicated API key. [10][11]
- An external documentation context service is called over HTTP with a dedicated API key, used to enrich prompts or retrieve reference documentation at runtime. [12]
- A Google-hosted orchestration service is consumed over HTTP, authenticated via the same Google API key; its exact role is not fully specified in available sources. [11]
- An external YAML parsing library is a soft dependency for structured API contract processing; the system falls back to an internal minimal parser when the library is absent. [13]

## Sources
1. `.env.example:7-14`
2. `wikifi/config.py:53-55`
3. `wikifi/config.py:116-134`
4. `wikifi/config.py:136-151`
5. `wikifi/orchestrator.py:148-200`
6. `wikifi/providers/ollama_provider.py:52`
7. `wikifi/providers/anthropic_provider.py:83-100`
8. `wikifi/providers/openai_provider.py:113-175`
9. `.mcp.json:14-20`
10. `.mcp.json:4-8`
11. `.mcp.json:29-35`
12. `.mcp.json:22-28`
13. `wikifi/specialized/openapi.py:154-162`
