# Intent and Problem Space

wikifi exists to produce structured, technology-agnostic documentation of what a software system *does* — its intent, domain entities, capabilities, and contracts — independently of the languages, frameworks, or infrastructure that currently implement it. The central premise is that large codebases, especially long-lived legacy monorepos, accumulate implicit knowledge that is never written down: it lives in the shape of the data model, the pattern of API contracts, the sequencing of schema migrations, and the disagreements between different parts of the codebase. That knowledge is precisely what migration teams and architects need, and precisely what is hardest to recover manually at scale.

### The problem it solves

Manually reading a large codebase to understand its domain intent is prohibitively slow and error-prone. A single-pass review of a repository containing tens of thousands of files cannot produce the structured, citable, auditable record that a re-implementation project requires. The problem has three compounding dimensions:

- **Scale** — the sheer volume of source material makes exhaustive manual analysis impractical.
- **Signal loss** — raw source code mixes domain logic with accidental implementation detail; understanding intent requires mentally stripping one from the other.
- **Hidden disagreement** — tribal knowledge is often encoded not in any single file but in the inconsistencies *between* files: a contract defined one way in a schema and used differently in application logic, for example.

### Who it serves

The system is oriented toward teams facing a migration or re-implementation decision: architects who need to audit what a system actually does, migration leads who need to know whether the documentation is complete enough to act on, and engineers who need authoritative answers about the existing system without reading every file themselves. The report capability is designed explicitly to answer the two questions a migration lead asks before funding a re-implementation: was the entire codebase covered, and is the resulting wiki good enough to act on?

### Design constraints

Several constraints follow directly from the problem:

**Technology-agnostic output.** Because the goal is to capture intent rather than describe implementation, every output artefact must be expressed in domain terms. A reader of the wiki should be able to reason about system behaviour without knowing what programming language or runtime environment was used.

**Full traceability.** Every claim in the generated documentation must be traceable to a specific location in the source codebase. An architect must be able to ask, for any sentence in the wiki, exactly where in the source it came from and receive a verifiable answer. This is a first-class requirement, not an afterthought.

**Explicit contradiction surfacing.** The system must surface disagreements between sources rather than silently merging them. In legacy systems, those disagreements are high-priority signals — they mark the boundaries of undocumented behaviour, accumulated drift, and tribal knowledge that migration teams most need to see.

**Economical operation at scale.** Processing tens of thousands of files with an AI-backed pipeline is inherently expensive. The design constrains this cost through content-addressed caching (skipping unchanged files on re-runs, turning hours-long full walks into minutes-long incremental updates), surgical incremental editing (reusing and patching cached prose when only a subset of a section's evidence has changed), and provider-level prompt-caching (so a shared context is not repriced on every individual file call).

**Grounded, non-speculative output.** At every stage — extraction, synthesis, interactive chat — the system must refuse to invent detail absent from its source evidence. Acknowledging a gap is preferable to producing a plausible-sounding but unsupported assertion. A critic-and-reviser quality loop enforces this before sections are finalised.

**Separation of primary and derivative content.** Some artefacts — personas, user stories, structural diagrams — cannot be reliably derived from any individual source file. The system explicitly defers their production until the full primary documentation pass is complete, preventing sparse per-file findings from producing speculative high-level views.

**Structured treatment of machine-readable contracts.** Schema definitions, interface contracts, API specifications, and migration files already encode domain knowledge in structured form. The system treats these as authoritative artefacts to be parsed precisely rather than interpreted, recognising that prose-model extraction of structured files is both wasteful and lossy.

## Supporting claims
- wikifi exists to produce technology-agnostic documentation of system intent, decoupled from implementation technology. [1][2][3]
- The system is designed to handle large legacy monorepos, described as containing up to tens of thousands of files. [4][2][5]
- The primary audience is migration teams and architects who need auditable, actionable documentation before or during a re-implementation project. [6][7][8][9]
- The report capability is designed to answer whether the codebase was fully covered and whether the wiki is good enough to act on. [7]
- Every claim in the generated documentation must be traceable to a specific file and line range in the source codebase; traceability is a first-class requirement. [10][6]
- The system surfaces contradictions between sources explicitly rather than silently merging them, because disagreements are high-priority signals in legacy systems. [10][6]
- Caching skips AI calls for unchanged files, turning hours-long full runs into minutes-long incremental updates. [4][2]
- A surgical incremental update path reuses and patches cached prose when only a subset of a section's evidence has changed, protecting established prose. [11]
- Provider-level prompt-caching keeps per-file AI call costs economical at scale by reusing the shared context across many calls. [5]
- A critic-and-reviser quality loop enforces that every claim is grounded in upstream evidence before sections are finalised. [12]
- The interactive chat mode requires answers to be grounded in wiki content; the assistant must acknowledge gaps rather than invent unsupported detail. [13]
- Some wiki sections (personas, user stories, diagrams) cannot be derived from any single source file and must be synthesised from the aggregate of primary findings. [14][15]
- Schema definitions, interface contracts, API specifications, and migration files are treated as authoritative structured artefacts to be parsed precisely rather than interpreted via prose analysis. [16][17][18][8][9]
- Noise — VCS plumbing, dependency caches, build artefacts, stub files, binary assets — is filtered before any file is handed to the analysis pipeline, so that models never receive inputs too sparse or irrelevant to produce reliable findings. [19][20]

## Sources
1. `wikifi/cli.py:1-9`
2. `wikifi/extractor.py:1-30`
3. `wikifi/orchestrator.py:1-27`
4. `wikifi/cache.py:1-18`
5. `wikifi/providers/anthropic_provider.py:1-18`
6. `wikifi/evidence.py:1-20`
7. `wikifi/report.py:1-15`
8. `wikifi/specialized/protobuf.py:1-7`
9. `wikifi/specialized/sql.py:1-12`
10. `wikifi/aggregator.py:1-17`
11. `wikifi/surgical.py:1-35`
12. `wikifi/critic.py:1-16`
13. `wikifi/chat.py:1-34`
14. `wikifi/deriver.py:1-18`
15. `wikifi/sections.py:1-20`
16. `wikifi/specialized/__init__.py:1-12`
17. `wikifi/specialized/dispatch.py:1-13`
18. `wikifi/specialized/openapi.py:1-11`
19. `wikifi/introspection.py:1-10`
20. `wikifi/walker.py:1-11`
