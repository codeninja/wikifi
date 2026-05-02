# Intent and Problem Space

wikifi exists because the intent embedded in a legacy system is typically invisible — locked inside years of implementation choices, technology-specific conventions, and accumulated structure that makes it difficult to separate *what the system does and why* from *how it currently does it*. Migration teams tasked with replacing or re-implementing such a system need the former without the latter.

### The Core Problem

When a team inherits a large legacy codebase and must produce a new implementation, they face a knowledge-extraction problem. The source describes a particular way of solving a set of problems, but rarely describes the problems themselves at a level that is portable to a new context. Reading the source directly tends to reproduce the same structure and constraints in the new system — recreating legacy decisions rather than the underlying intent.

wikifi addresses this by walking a repository and producing a structured, technology-agnostic wiki that surfaces:

- **Domain entities and capabilities** — what the system models and what it can do
- **API contracts and integration touchpoints** — what it exposes and to whom
- **Cross-cutting concerns** — considerations that span the system as a whole
- **Personas, user stories, and diagrams** — who uses the system, what they need, and how flows connect

The goal is to make legacy intent explicit, complete, and portable so a fresh implementation can retain full functional value without inheriting structural decisions.

### Primary Audience

The immediate audience is migration teams — architects and developers who need to understand a system's domain well enough to re-implement it rather than maintain it. A secondary audience includes anyone who must understand what a system does without reading its source directly, including those who need to interrogate the resulting wiki conversationally.

### What the System Is Not

wikifi is explicitly a feature-extraction tool, not a transposition tool. It surfaces what a legacy system does and leaves all decisions about target architecture, structure, and approach entirely to the migration team. The output prescribes nothing about how the new system should be built.

### Shaping Constraints

Several constraints are built into the design from the outset:

| Constraint | Rationale |
|---|---|
| **Technology agnosticism** | Output must be expressed in domain terms, never in terms of the implementation technology found in the source, so the wiki does not embed the very assumptions it is meant to dissolve. |
| **Quality over speed** | Accuracy and completeness of the generated wiki are prioritised over processing throughput. |
| **Arbitrary scale** | The system must handle repositories of any size — including legacy monorepos with tens of thousands of files — through caching and chunking strategies that make repeated and interrupted runs cheap. |
| **Full traceability** | Every assertion in the generated wiki must trace back to specific source files and locations so architects can verify any claim against the original codebase. |
| **Honest disagreement** | Where source files contain conflicting signals, the system surfaces those contradictions explicitly rather than silently resolving them, preserving the full picture for the migration team. |

## Sources
1. `VISION.md:3-9`
2. `CLAUDE.md:73-75`
3. `README.md:3`
4. `wikifi/cli.py:1-8`
5. `.env.example:1-2`
6. `TESTING-AND-DEMO.md:1-6`
7. `wikifi/config.py:1-8`
8. `wikifi/specialized/__init__.py:1-13`
9. `wikifi/specialized/openapi.py:1-11`
10. `wikifi/specialized/protobuf.py:1-8`
11. `wikifi/deriver.py:1-18`
12. `wikifi/sections.py:1-19`
13. `VISION.md:86-89`
14. `wikifi/critic.py:1-15`
15. `wikifi/chat.py:1-32`
16. `wikifi/cache.py:1-21`
17. `wikifi/extractor.py:1-37`
18. `wikifi/aggregator.py:1-15`
19. `wikifi/evidence.py:1-18`
