# Capabilities

wikifi turns any codebase into a structured, evidence-backed wiki and keeps that wiki current as the codebase evolves — without requiring the development team to write documentation by hand.

### Automated Repository Discovery

The system autonomously examines a repository using only its directory structure and manifest file contents, classifying paths into those that contain meaningful production source and those that should be skipped. From this metadata alone it derives a one-paragraph summary of the system's apparent purpose, a list of primary languages in use, and a set of include/exclude patterns for the analysis that follows.

### Structured Documentation Generation

A multi-stage pipeline walks every in-scope file, extracts domain-level findings, and synthesizes those findings into a canonical set of wiki sections.[4][5][6] Documentation is organized into two tiers:

| Tier | Sections | Grounding |
|---|---|---|
| Primary | Domains, Intent, Capabilities, External Dependencies, Integrations, Cross-Cutting Concerns, Entities, Hard Specifications | Direct per-file evidence |
| Derivative | User Personas, User Stories, Diagrams | Cross-file synthesis from aggregated primaries |

Structured artifacts — API contracts, schema definitions, interface definition files, and database migration scripts — are processed through deterministic, type-aware extractors for higher reliability and speed. All other source files are analyzed through a general-purpose understanding pass. The cross-file reference graph is consulted per file so that findings can describe flows between modules rather than treating each file in isolation.

### Citation Traceability and Contradiction Surfacing

Every claim in the generated wiki is anchored to the specific source file and line range from which it was derived, rendered as inline citation markers linked to a numbered source footer. Where two or more source locations assert incompatible things about the same topic, the system surfaces an explicit "Conflicts in source" block rather than silently reconciling the disagreement — giving downstream readers an honest view of ambiguity.

### Incremental Re-Analysis

A content-addressed record of prior analysis results is maintained at multiple independent granularities: per file, per section, and per repository scope. On a subsequent run, only files whose content has changed are re-processed; sections whose evidence base is entirely unchanged are served from cache without additional analysis work. When only a small subset of findings in a section changes, the system performs targeted in-place edits to preserve established prose rather than rewriting from scratch, retaining citation numbering and unaffected paragraphs verbatim. A re-run in which nothing has changed is a complete no-op.

### Quality Review

An optional critic-and-reviser cycle can be applied to any wiki section: the body is scored against a structured rubric, weaknesses are identified, a revised body is produced, and the better version is kept. This loop is considered the highest-leverage quality lever for derivative outputs such as personas and user stories. A separate coverage and quality report summarizes, per section, how many files contributed findings and how complete the analysis was; when the critic is enabled, per-section quality scores and unsupported-claim flags are included alongside an overall mean score.

### Interactive Exploration

Once a wiki has been generated, users can open an interactive conversational session grounded in the wiki content. Questions can span multiple turns, conversation history can be reset while retaining the wiki context, and currently loaded sections can be listed at any time. Only fully populated sections are included in the assistant's context, preventing placeholder content from diluting answers.

### Resilience and Graceful Degradation

If synthesis of a section fails at runtime, the raw extracted notes are preserved in the output so the wiki always contains some content rather than a blank section. Files that cannot be parsed — for example, malformed API contract files — are flagged for manual review rather than causing processing to halt entirely. Cache state is persisted after each file so that a crash at any stage resumes from exactly the last completed file rather than restarting from scratch.

## Supporting claims
- The system autonomously classifies a repository's directory tree into paths worth analysing and paths to skip, using only directory metadata and manifest file contents. [1][2][3]
- From directory metadata alone the system derives a one-paragraph summary of the system's apparent purpose and identifies primary languages in use. [1]
- Documentation is organized into eight primary sections grounded in direct per-file evidence and three derivative sections synthesized from the aggregated primaries. [6]
- Primary sections cover: domains, intent, capabilities, external dependencies, integrations, cross-cutting concerns, entities, and hard specifications. [6]
- Derivative sections cover user personas, user stories, and diagrams, and require cross-file synthesis to avoid speculation. [6][7]
- Structured artifacts such as API contracts, schema definitions, interface definition files, and database migration scripts are processed through deterministic, type-aware extractors rather than the general understanding pass. [8][5][9][10][11][12][13]
- The cross-file reference graph is consulted per file so findings can describe flows between modules rather than treating each file in isolation. [14][15][16]
- Every claim in the generated wiki is anchored to the originating source file and line range, rendered as inline citation markers linked to a numbered source footer. [17][18]
- Where two or more sources assert incompatible things about the same topic, the system surfaces an explicit 'Conflicts in source' block rather than silently reconciling the disagreement. [19][17]
- A content-addressed record of prior analysis results is maintained at multiple independent granularities — per file, per section, and per repository scope — enabling incremental re-runs. [20][21]
- On a subsequent run, only files whose content has changed are re-processed; unchanged sections are served from cache without additional analysis work. [21][22]
- When only a small subset of findings in a section changes, the system performs targeted in-place edits to preserve established prose rather than rewriting from scratch. [23][24][25][26][27]
- A re-run in which nothing has changed is a complete no-op — stages 3 and 4 are skipped entirely. [28][22]
- An optional critic-and-reviser cycle scores any section body against a structured rubric, produces a revised body, and keeps the better version. [29]
- The critic-and-reviser loop is considered the highest-leverage quality lever for derivative outputs such as personas and user stories. [30]
- A coverage and quality report summarizes, per section, how many files contributed findings; when the critic is enabled it also includes per-section quality scores and unsupported-claim flags. [31][32][33][34]
- Users can open an interactive conversational session grounded in the generated wiki content, spanning multiple turns, with the ability to reset conversation history while retaining wiki context. [35][36]
- Only fully populated wiki sections are included in the conversational assistant's context, preventing placeholder content from diluting answers. [37]
- If synthesis of a section fails, the raw extracted notes are preserved in the output so the wiki always contains some content. [38]
- Files that cannot be parsed are flagged for manual review rather than halting processing entirely. [39]
- Cache state is persisted after each file so that a crash at any stage resumes from the last completed file rather than restarting from scratch. [20][21]

## Conflicts in source
_The walker found disagreements across files. Migration teams should resolve these before re-implementation._

- **The number of distinct routing paths for section re-synthesis is described inconsistently across notes: one describes four paths (full cache hit, finding-set unchanged but metadata shifted, surgical edit, full rewrite) while another describes three paths (full cache hit, surgical edit, full rewrite).**
  - Four prioritized paths govern section production: full cache hit, finding-set unchanged but notes metadata shifted (refresh cache key, no LLM call), surgical edit for low-churn deltas, and full rewrite for high churn or no prior body. (`wikifi/aggregator.py:130-175`)
  - Three routing paths exist: full cache hit (no work), surgical edit (append or remove specific claims), and full rewrite (when changes are too broad). (`wikifi/cache.py:100-116`)

## Sources
1. `wikifi/introspection.py:55-70`
2. `wikifi/introspection.py:86-117`
3. `wikifi/walker.py:89-115`
4. `wikifi/orchestrator.py:57-100`
5. `wikifi/extractor.py:1-20`
6. `wikifi/sections.py:41-136`
7. `wikifi/deriver.py:80-135`
8. `wikifi/config.py:114-119`
9. `wikifi/specialized/__init__.py:1-12`
10. `wikifi/specialized/dispatch.py:43-60`
11. `wikifi/specialized/models.py:1-9`
12. `wikifi/specialized/sql.py:63-70`
13. `wikifi/specialized/sql.py:56-62`
14. `wikifi/config.py:107-113`
15. `wikifi/extractor.py:242-244`
16. `wikifi/repograph.py:163-230`
17. `wikifi/evidence.py:95-145`
18. `wikifi/extractor.py:254-268`
19. `wikifi/aggregator.py:1-16`
20. `wikifi/cache.py:5-35`
21. `wikifi/extractor.py:193-215`
22. `wikifi/orchestrator.py:175-205`
23. `wikifi/aggregator.py:130-175`
24. `wikifi/config.py:131-148`
25. `wikifi/surgical.py:148-193`
26. `wikifi/surgical.py:196-234`
27. `wikifi/surgical.py:237-284`
28. `wikifi/cache.py:22-30`
29. `wikifi/critic.py:4-10`
30. `wikifi/deriver.py:115-130`
31. `wikifi/report.py:4-8`
32. `wikifi/report.py:8-11`
33. `wikifi/report.py:43-70`
34. `wikifi/critic.py:213-232`
35. `wikifi/chat.py:95-134`
36. `wikifi/cli.py:63-240`
37. `wikifi/chat.py:68-83`
38. `wikifi/aggregator.py:290-302`
39. `wikifi/specialized/openapi.py:27-41`
40. `wikifi/cache.py:100-116`
