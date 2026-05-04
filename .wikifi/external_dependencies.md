# External-System Dependencies

The system depends on three mutually-exclusive inference backends and one optional data-parsing service. The active backend is selected at configuration time; the remaining two are inactive.

## Inference Backends

### Local Self-Hosted Inference (default)

By default, all language-model calls are routed to a locally-hosted inference service. The service is addressed over HTTP at a configurable host endpoint and a configurable model identifier. No API key is required. The local backend handles schema-constrained structured output, free-text completion, multi-turn dialogue, and an optional reasoning-trace mode.[3] A per-call timeout is configurable.

### Anthropic Hosted API (opt-in)

An Anthropic-hosted inference service is available as an opt-in backend. It requires an API key supplied via an environment variable. When the configured model identifier is not recognized as a valid Anthropic model name, the system automatically substitutes a known-good default (claude-opus-4-7) to prevent request failures. The backend supports adaptive reasoning, with a thinking-effort level (low / medium / high / max) mapped onto the provider's native feature. A per-call output-token cap is configurable.

### OpenAI-Compatible Hosted API (opt-in)

An OpenAI-compatible hosted inference service is a second opt-in backend. It requires an API key from the environment and accepts an optional base-URL override, which allows the system to target Azure OpenAI endpoints, proxy deployments, or other compatible services. When a model identifier uses a local-service naming convention (family:tag), it is automatically replaced with a provider-appropriate default; all other identifiers — including Azure deployment names — pass through unchanged. The backend supports all three interaction modes: schema-constrained structured output, free-text completion, and multi-turn dialogue.

## Inference Backend Comparison

| Attribute | Local (default) | Anthropic | OpenAI-compatible |
|---|---|---|---|
| Requires API key | No | Yes (env var) | Yes (env var) |
| Custom endpoint | Yes (host URL) | No | Yes (base URL override) |
| Adaptive reasoning | Yes (optional) | Yes (effort levels) | — |
| Per-call token cap | — | Yes | Yes |
| Azure / proxy support | — | — | Yes |

## Optional Data-Parsing Service

When processing OpenAPI/Swagger contract files, the system can delegate YAML parsing to an external library if one is present in the runtime environment. If that library is absent, a built-in minimal parser handles the specific structural subset required. This means the capability degrades gracefully rather than failing; no external service endpoint or credential is involved.

## Supporting claims
- By default, all language-model calls are routed to a locally-hosted inference service addressed over HTTP at a configurable host endpoint and model identifier. [1][2][3]
- The local backend requires no API key. [2][3]
- A per-call timeout is configurable for the local backend. [3]
- The Anthropic-hosted inference service requires an API key supplied via an environment variable. [4][5]
- When the configured model identifier is not recognized as a valid Anthropic model name, the system substitutes a known-good default (claude-opus-4-7). [6][5]
- The Anthropic backend maps a thinking-effort level (low/medium/high/max) to the provider's adaptive thinking feature. [4]
- A per-call output-token cap is configurable for the Anthropic backend. [4]
- The OpenAI-compatible backend requires an API key from the environment and accepts an optional base-URL override for Azure, proxy, or other compatible deployments. [7][8][9]
- When a model identifier uses a local-service naming convention, it is automatically replaced with a provider-appropriate default; all other identifiers pass through unchanged. [8]
- The OpenAI-compatible backend supports schema-constrained structured output, free-text completion, and multi-turn dialogue. [9]
- When processing OpenAPI/Swagger contract files, the system uses an external YAML-parsing library if present, falling back to a built-in minimal parser that covers the required structural subset. [10]

## Sources
1. `wikifi/config.py:55-58`
2. `wikifi/orchestrator.py:243-251`
3. `wikifi/providers/ollama_provider.py:54-57`
4. `wikifi/config.py:155-178`
5. `wikifi/providers/anthropic_provider.py:97-115`
6. `wikifi/orchestrator.py:252-264`
7. `wikifi/config.py:180-197`
8. `wikifi/orchestrator.py:265-285`
9. `wikifi/providers/openai_provider.py:1-10`
10. `wikifi/specialized/openapi.py:148-167`
