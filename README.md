# wikifi

> A Python library that walks a codebase and produces a technology-agnostic wiki describing the system in migration-ready terms.

See [`VISION.md`](./VISION.md) and [`.spec/`](./.spec/) for the spec.

## Usage

```bash
uv sync
uv run wikifi init /path/to/source
uv run wikifi walk /path/to/source
```

`wikifi walk` writes the documentation workspace to the target repository's `.wikifi/` directory:

- `sections/` contains primary capture from direct source evidence.
- `derivatives/` contains personas, user stories, and diagrams synthesized after primary capture.
- `notes/` contains intermediate extraction records and is ignored by the generated workspace `.gitignore`.
- `reports/` contains execution summaries and pipeline health metrics.

The default provider is local Ollama. If the local provider is unavailable and fallback is enabled, the pipeline preserves deterministic source-backed findings and records the provider degradation in the execution summary.
