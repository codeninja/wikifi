# FEEDBACK

## Journal Entry

This was a demanding but useful implementation session because the repository started as almost a blank slate while the documentation described a complete product. The docs gave me a strong product direction: wikifi is a CLI library that walks a codebase, extracts technology-agnostic system intent, writes a `.wikifi/` workspace, and must use a local LLM by default through a provider abstraction. That was enough to build a coherent first implementation, but several important operational details had to be discovered or decided while working.

The hardest part was the gap between the high-level product spec and the low-level compatibility contract. `VISION.md` says the wiki layout is at the implementor's discretion, while `.spec/hard_specifications.md` says the directory schema is immutable and structural modifications are prohibited. I resolved that by defining a stable `.wikifi/` layout in code and treating it as the compatibility contract for this implementation, but I had to make that call without a pre-existing schema. If a future agent or maintainer makes a different call, downstream generated artifacts may drift.

Another issue was the LLM contract. The documentation correctly says local Ollama is the default and that reasoning quality is preferred over speed, but it does not describe how thinking-capable Ollama models behave. In practice, `qwen3.6:27b` returned structured JSON in the `thinking` field while leaving `response` empty. My first validation run incorrectly succeeded through deterministic fallback, which exposed that fallback can mask provider integration failures if it is enabled during acceptance validation. The final run only became meaningful after disabling fallback and teaching the provider to read thinking-mode output.

I also had to infer the boundary between "feature extraction" and "implementation details." The docs repeatedly require technology-agnostic output, but the implementation still has to inspect source text, classify files, derive entities, and record evidence. I handled that by preserving source provenance in notes while translating section output into domain-facing language. That balance would benefit from more explicit examples of acceptable and unacceptable generated content.

The testing requirements were clear and helpful: use `uv`, use `ruff`, every feature ships with tests, and coverage must be at least 85%. The initial scaffold did not yet satisfy its own packaging requirements, so the first practical blocker was just making `uv run wikifi` possible. Once packaging was fixed, the Makefile and hook workflow became a useful guardrail.

## Where I Had Issues

- The repository had no implementation modules, no tests, and no package entry point, so the work was closer to greenfield product construction than completing an existing system.
- The specs disagreed on whether `.wikifi/` layout was discretionary or immutable.
- The expected `.wikifi/` directory schema was not provided even though compatibility was treated as mandatory.
- The provider abstraction requirement was clear, but the exact provider API contract, retry behavior, fallback policy, and structured-output parsing rules were unspecified.
- Ollama thinking-mode behavior was not documented, and the first live validation used fallback rather than proving the model path.
- The generated output quality contract was broad: the docs list required sections but do not provide examples, minimum content requirements, or objective acceptance checks for a good wiki.
- The specs require explicit contradiction reporting, but do not define how conflicts should be detected or represented.
- The specs require local LLM by default, but do not state whether validation should fail when the model is missing or whether fallback is acceptable outside developer convenience.

## What I Wish I Knew Up Front

- The exact `.wikifi/` layout expected for compatibility, including which files are required, which are transient, and which should be committed during validation.
- That the benchmark expected generated `.wikifi/` documents to remain in the PR for review.
- That a successful final validation must be a real Ollama-backed run with fallback disabled.
- The specific local model expected for acceptance and any known quirks for that model.
- Whether fallback output is intended only for development resilience or is acceptable as production output when providers are unavailable.
- Whether extraction should call the LLM once per file, once per section, or use a hybrid approach.
- Whether generated derivative sections should be produced by the LLM or can be deterministic synthesis from primary notes.

## Documentation Changes I Would Like

- Add a required `.wikifi/` workspace schema, including paths, file purposes, versioning expectations, and which artifacts are ignored by default.
- Add an acceptance-validation section that explicitly says to run with fallback disabled, a 300-second request timeout, and the required local Ollama model.
- Document Ollama thinking-mode response handling, especially that structured output may be returned in `thinking` rather than `response`.
- Define the provider interface contract with expected request fields, response parsing, errors, retry policy, and fallback semantics.
- Clarify whether fallback output is allowed in normal operation, CI, and final acceptance runs.
- Provide example generated sections that demonstrate the desired level of technology-agnostic translation and evidence provenance.
- Resolve the contradiction between "wiki layout is at implementor's discretion" and "immutable directory schema."
- Define objective quality gates for generated wiki content beyond "non-empty": required headings, required gap declarations, provenance links, Gherkin formatting, diagram syntax, and minimum section coverage.
- Add conflict-detection guidance: what counts as contradictory evidence, how it should be reported, and whether the pipeline should continue.
- State whether generated validation artifacts should be committed to the PR by default.

## Closing Note

The strongest part of the existing documentation is the product vision. It clearly communicates why wikifi exists and what value the generated wiki should provide. The weakest part is the operational contract. The next improvement should turn the high-level vision into a concrete implementation contract: workspace schema, provider semantics, validation commands, and examples of passing output.
