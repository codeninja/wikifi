# External-System Dependencies

The system integrates with up to three language-model inference backends — exactly one active at a time — selected at configuration time. An additional soft dependency covers structured API-contract parsing.

## Inference Backends

### Local Inference Service (default)

By default, all language-model calls are routed to a locally-hosted **Ollama** inference service reached over HTTP at a configurable host address. No API key is required. The service must support three interaction modes: schema-constrained structured output, free-text generation, and multi-turn conversation. Models are identified using a `family:tag` naming convention. A configurable connection timeout (default: 900 seconds) accommodates long reasoning traces on large models.

### Anthropic API — Hosted Inference (opt-in)

Anthropic's hosted inference API is an opt-in alternative. It requires an API key supplied via configuration or the runtime environment. The integration exposes adaptive thinking controls — allowing reasoning depth to be traded against latency on a per-call basis — and supports configurable per-call output token budgets. The system defaults to a specific known-good model when no explicit identifier is provided, preventing routing failures caused by locally-formatted model names being submitted to the hosted endpoint. A configurable network timeout (default: 900 seconds) covers extended-thinking and structured-output calls.

### OpenAI API — Hosted Inference (opt-in)

OpenAI's hosted API is a second opt-in alternative. It exposes two surfaces: a schema-constrained structured-output endpoint returning pre-validated typed responses, and a standard chat-completion endpoint for free text and multi-turn conversation. The API key is sourced from the runtime environment. The integration supports standard hosted endpoints, enterprise cloud deployments (e.g. Azure-hosted variants), and arbitrary proxy deployments via a configurable base URL; deployment identifiers are forwarded unchanged to preserve compatibility. When a locally-formatted model identifier is detected, the system substitutes a known-good hosted model to prevent request failures; explicit deployment identifiers bypass this substitution.

## API-Contract Parsing

When processing structured API-contract files, the system can optionally rely on an external YAML-parsing library. If the library is absent at runtime, a built-in minimal parser handles the relevant document subset, making this a soft dependency — the capability remains functional without the library installed.

## Supporting claims
- A locally-hosted Ollama inference service is the default language-model backend, requiring no API key and no hosted service subscription. [1][2][3]
- The Ollama service is reached over HTTP at a configurable host address. [1][3]
- The Ollama backend must support schema-constrained structured output, free-text generation, and multi-turn conversation. [3]
- Ollama models are identified using a family:tag naming convention. [2]
- The Ollama backend carries a configurable connection timeout defaulting to 900 seconds. [3]
- Anthropic's hosted inference API is an opt-in alternative that requires an API key from configuration or environment. [4][5][6]
- The Anthropic integration supports adaptive thinking modes and configurable per-call output token budgets. [4][6]
- When no explicit model identifier is provided for the Anthropic backend, the system substitutes a specific default model to avoid routing errors from locally-formatted model names. [5][6]
- The Anthropic backend carries a configurable network timeout defaulting to 900 seconds to accommodate extended-thinking and structured-output calls. [6]
- OpenAI's hosted API is a second opt-in inference backend; its API key is sourced from the runtime environment. [7][8][9]
- The OpenAI integration exposes two API surfaces: a schema-constrained structured-output endpoint and a standard chat-completion endpoint for free text and multi-turn conversation. [9]
- The OpenAI integration supports standard hosted endpoints, enterprise cloud deployments, and proxy deployments via a configurable base URL; arbitrary deployment identifiers are forwarded unchanged. [7][8]
- When a locally-formatted model identifier is detected, the OpenAI backend substitutes a known-good hosted model; explicit deployment identifiers are passed through unchanged. [8]
- An external YAML-parsing library is an optional soft dependency for processing API-contract files; a built-in fallback parser handles the required document subset when the library is absent. [10]

## Sources
1. `wikifi/config.py:51-53`
2. `wikifi/orchestrator.py:255-264`
3. `wikifi/providers/ollama_provider.py:48-57`
4. `wikifi/config.py:151-166`
5. `wikifi/orchestrator.py:265-277`
6. `wikifi/providers/anthropic_provider.py:75-100`
7. `wikifi/config.py:170-181`
8. `wikifi/orchestrator.py:278-299`
9. `wikifi/providers/openai_provider.py:111-135`
10. `wikifi/specialized/openapi.py:131-153`
