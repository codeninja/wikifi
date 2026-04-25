# FEEDBACK.md

## Journal Entry: The Implementation of wikifi

Implementing `wikifi` was an exercise in bridging the gap between high-level domain-driven design (DDD) and the gritty realities of local LLM orchestration. The project vision is clear and compelling, but the execution phase revealed several "friction points" that are common in autonomous agent workflows.

### The Experience
The staged pipeline architecture (Introspection -> Extraction -> Aggregation -> Derivation) provided a solid roadmap. The isolation of concerns allowed for surgical implementation of each engine. However, the experience was defined by the transition from "cloud-standard" LLM behavior to "local-optimized" behavior.

### Issues Encountered
1.  **JSON Schema Reliability:** Local models (like `qwen3.6:27b`) often struggle with strict `json_object` modes provided by abstraction layers like LiteLLM. I encountered multiple `ValidationError` and `EOF` errors where the model returned empty strings or included conversational filler despite system prompts.
2.  **Context Window Pressure:** The Aggregation phase is a significant bottleneck. Passing dozens of extraction notes into a single prompt for section synthesis quickly exhausts context windows.
3.  **Ambiguity in "Inline Schematics":** The requirement for Mermaid diagrams was clear, but the "how" was underspecified. Generating valid Mermaid syntax that actually represents a 10,000-foot view requires specialized prompting that wasn't in the initial spec.

### What I Wish I Knew Upfront
*   **The "Ollama Tax":** I initially assumed standard `json_object` support. I wish I had started with the "Robust Cleaning" logic (handling backticks, splitting substrings) in the `LLMProvider` from turn one.
*   **The need for Aggressive Truncation:** Simply filtering files by size isn't enough. For a medium codebase, even the *notes* from the files can exceed the aggregator's context. A "Recursive Summarization" strategy would be better than the "Bulk Note Pass" I implemented.

### Documentation Recommendations
1.  **Baseline Prompt Library:** The `.spec/` files are great for *what* to do, but providing a few "Reference Prompts" for the Extraction and Aggregation phases would ensure consistency across different implementations.
2.  **Concrete Schema Definitions:** While `entities.md` lists the names, providing a strict JSON Schema or Pydantic model for the `ExtractionNote` in the documentation would prevent implementers from having to "guess" the fields the downstream Aggregator expects.
3.  **Failure State Guidance:** Define how the system should handle a "Lossy Extraction" (e.g., when a model fails to analyze a file). Should it record a placeholder, or skip it entirely? I chose to log and skip to maintain pipeline integrity, but this is a business logic decision.

### Conclusion
`wikifi` is a powerful concept. By hardening the LLM interaction layer and being more explicit about the "Knowledge Handoff" schemas in the documentation, the project will be much easier to scale to even larger, more complex repositories.
