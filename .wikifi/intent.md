# Intent and Problem Space

Large software repositories — especially long-lived, legacy monorepos — accumulate operational knowledge that is scattered across files, embedded in implementation choices, and never captured as coherent documentation. Developers asked to understand or migrate such a system face two intertwined challenges: the sheer volume of source material makes manual review impractical, and the documentation that does exist describes *how* the system is built rather than *what it does for its users*.

The system exists to automatically generate a technology-agnostic wiki from a target repository — a structured body of documentation that describes what a system accomplishes for its users, deliberately decoupled from the languages, frameworks, and libraries used to build it. Because the wiki captures intent rather than implementation, it remains legible and actionable even when the underlying technology stack is replaced entirely.

## Who It Is For

The primary audience is:

- **Developers** who need to understand a codebase they did not write
- **Migration leads and architects** who need to scope or fund a re-implementation
- **Teams maintaining legacy systems** where tribal knowledge hides in inconsistencies scattered across files

Before committing resources to a re-implementation, migration leads typically ask two questions: did the analysis walk cover the full system, and is the resulting wiki trustworthy enough to act on? The system is designed to answer both, and to do so without modifying any wiki content during the reporting pass, making it safe to run in automated pipelines.

## Constraints That Shape the Design

Several explicit constraints govern the system's design decisions end to end:

| Constraint | What it means in practice |
|---|---|
| **Technology agnosticism** | Every extracted observation must describe what the code accomplishes for users; implementation-specific terms are excluded at the extraction stage |
| **Traceability** | Every assertion in the wiki is linked to the precise source location that supports it, so an architect can verify any claim without trusting unsourced documentation |
| **Contradiction surfacing** | When source files contain conflicting observations, the system surfaces those conflicts explicitly rather than silently resolving or discarding them |
| **Quality over wall-time** | Configuration explicitly prioritises documentation quality over processing speed |
| **Incremental efficiency** | Repeated analysis of large codebases must be practical; unchanged work is skipped so that re-runs take minutes rather than hours |
| **Backend independence** | The AI inference backend can be swapped without affecting any pipeline stage, preventing vendor lock-in at the infrastructure level |
| **Economic viability** | Calling a hosted AI service for hundreds of per-file extraction passes without cost controls would be prohibitive; prompt-cache reuse makes the hosted path economically competitive |

These constraints are not incidental implementation choices — they are the stated rationale behind the system's four-stage pipeline, its caching architecture, its structured evidence model, and its provider abstraction layer.

## Supporting claims
- The system exists to automatically generate a technology-agnostic wiki from a target repository, decoupling what the system does from the technologies used to build it. [1][2][3]
- The primary audience is developers who need to understand or migrate a codebase, and migration leads or architects who need to scope a re-implementation. [1][4][5]
- Legacy systems accumulate tribal knowledge that hides in inconsistencies scattered across files. [6]
- Every extracted observation must describe what the code accomplishes for users, never naming specific technologies, so the wiki survives a technology migration. [1][7]
- Every assertion in the wiki is linked to the precise source location that supports it, so any architect can ask 'where in the source did this come from?' and receive a verifiable answer. [4]
- When source files contain conflicting or inconsistent observations, the system surfaces those contradictions explicitly rather than silently merging or discarding them. [6]
- Configuration explicitly prioritises wiki quality over processing wall-time. [8]
- Repeated analysis of large codebases (including 50,000-file legacy monorepos) must be efficient; unchanged work is skipped so re-runs take minutes rather than hours. [9][2]
- The AI inference backend can be swapped by implementing a single abstract contract, keeping all pipeline stages decoupled from any specific vendor. [10]
- Without deliberate cost controls, calling a hosted AI service for hundreds of per-file extraction passes would be cost-prohibitive; prompt-cache reuse makes hosted inference economically viable. [11]
- Before funding a re-implementation, migration leads ask two questions: did the analysis walk cover the full system, and is the resulting wiki trustworthy enough to act on? [5]

## Sources
1. `wikifi/cli.py:1-11`
2. `wikifi/orchestrator.py:1-27`
3. `wikifi/sections.py:1-18`
4. `wikifi/evidence.py:1-18`
5. `wikifi/report.py:1-15`
6. `wikifi/aggregator.py:1-16`
7. `wikifi/extractor.py:1-20`
8. `wikifi/config.py:1-26`
9. `wikifi/cache.py:1-35`
10. `wikifi/providers/base.py:1-19`
11. `wikifi/providers/anthropic_provider.py:1-18`
