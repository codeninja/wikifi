# External-System Dependencies

The system draws on several categories of external service: language-model inference backends, development-time tooling integrations, and a continuous-integration platform.

## Language-Model Inference

All substantive text generation and structured extraction is delegated to an external (or locally hosted) language-model service. Three backends are supported through a common provider abstraction:

| Backend | Hosting | Authentication | Role |
|---|---|---|---|
| Local inference server (default) | Self-hosted, no network egress | None required | Default backend for all extraction and synthesis calls; configurable host address and 15-minute per-call timeout |
| Hosted AI service A (Anthropic) | Cloud API | API key (`ANTHROPIC_API_KEY`) | Opt-in backend; uses an ephemeral prompt-cache marker on the system prompt so that large extraction prompts are billed at roughly 10 % of normal input-token cost across repeated per-file calls |
| Hosted AI service B (OpenAI-compatible) | Cloud API (or compatible proxy/Azure endpoint) | API key + optional custom base URL | Opt-in backend; relies on automatic prefix caching (prefixes ≥ 1 024 tokens cached for ~5–10 minutes); exposes a reasoning-intensity knob mapped to the backend's reasoning-effort parameter on capable model variants |

The local inference server is the default and requires no credentials or external network access. The two hosted backends are opt-in and each require a provisioned API key. All three backends are configured with a model name, timeout, and per-call output-token cap drawn from the application's runtime settings.

### Caching Strategy
Because the extraction prompt is large and is reused across every file in a repository, minimising repeated billing for identical prompt prefixes is a first-class concern. The hosted-AI-service-A integration achieves this by tagging the system-prompt block with an ephemeral cache-control marker. The hosted-AI-service-B integration relies on the provider's automatic prefix-caching mechanism without requiring explicit markers.

## Development-Time Tool Integrations

The MCP server configuration reveals several additional integrations that appear to be used during development or agent-assisted workflows rather than in the core production pipeline:

- **Google AI generative API** — consumed by at least two registered tool integrations; authenticated via a shared API key.
- **Self-hosted web-crawling service** — running locally on a fixed port with no API key, providing crawling capability on demand.
- **External documentation/context lookup service** — called over HTTP with a dedicated API key; likely used to retrieve up-to-date reference documentation for prompt enrichment.
- **Google-hosted orchestration service (
