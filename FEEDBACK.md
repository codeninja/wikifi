# Feedback for the Wikifi Developer

## Experience Summary
Building `wikifi` was a rewarding experience. The project architecture, particularly the orchestrator-provider-walker pattern, is clean and well-structured, making it easy to reason about the pipeline. The integration of `pydantic`, `typer`, and `loguru` aligns perfectly with the defined project conventions.

## Challenges Encountered
1. **Ollama JSON Mode:** Relying on `format: "json"` in the Ollama API call proved fragile, especially with powerful models (27B+) that insist on including "thinking" processes or markdown formatting in their output. This caused initial Pydantic validation failures.
2. **Schema Sensitivity:** The `ExtractionNote` model was strictly expecting strings for `role_summary` and `finding`. When the LLM returned these as lists (e.g., bulleted points), the entire pipeline stalled.
3. **Unexpected CLI Argument Handling:** Typer's argument parsing behavior was slightly different from common expectations when `target` had a default value, leading to a minor hiccup during CLI testing.

## Lessons Learned (Wish I Knew Up Front)
- **Aggressive Input Sanitization:** I should have assumed the LLM would return structured data in suboptimal formats from the start and built defensive parsing into the `Extractor` before the first run.
- **Model Behavior:** I now know that forcing `format: json` on large models often conflicts with their reasoning ("thinking") output. It is better to prompt for raw JSON and use regex/parsing logic on the response.

## Recommended Documentation Changes
1. **Schema Flexibility:** Update the `ExtractionNote` documentation/specification to explicitly allow (and suggest) defensive parsing for `role_summary` and `finding` fields, as LLMs frequently vary their structure.
2. **Provider Troubleshooting:** Add a section to `CLAUDE.md` or the internal docs regarding common LLM provider pitfalls (specifically the "thinking" output issue with JSON-mode).
3. **CLI Usage:** Add explicit examples of how to invoke the CLI commands with arguments in the `README.md` to avoid argument parsing confusion.

Overall, the project is solid. The pipeline is logically sound and very extensible. Thank you for the clean architectural foundation.
