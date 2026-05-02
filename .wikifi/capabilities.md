# Capabilities

wikifi analyzes any target codebase and produces a structured, technology-agnostic wiki that captures domain knowledge, system intent, capabilities, external dependencies, integrations, cross-cutting concerns, core entities, and hard specifications — expressed entirely in domain terms rather than in the language of a specific technology stack.

## Workspace Initialization

Before analysis begins, the system bootstraps a wiki workspace inside the target project in an idempotent manner, creating the required directory structure, a configuration file, version-control ignore rules, and one placeholder document per defined section. Repeat invocations leave already-existing artifacts untouched.

## Codebase Analysis Pipeline

The core pipeline runs in four ordered stages:

1. **Repository introspection** — The system compresses the repository's directory layout and reads key manifest files, then uses this compact view to classify every path as either worth walking (production source, business logic, integrations, domain models) or worth skipping (vendored dependencies, build output, tests, CI/CD). The classification is returned as a structured, diffable result.

2. **Per-file extraction** — Every in-scope file is routed through one of three extraction paths:
   - *Cache replay* — if a file's content is unchanged since the last run, previously stored findings are reused without any further processing.
   - *Deterministic schema parsing* — files recognised as structured schema artifacts (SQL DDL, database migrations, API contract specs, interface definition files, and graph schema files) are processed by purpose-built parsers that produce findings about entities, relationships, operations, and constraints without invoking an AI model.
   - *AI-assisted extraction* — all remaining files pass through an AI extraction pass; large files are recursively split into overlapping chunks so no content is missed regardless of size.

   Every finding carries a source citation — the originating file path, an inclusive line range, and a content fingerprint — enabling full traceability back to the codebase.

3. **Cross-file context enrichment** — In parallel with extraction, the system builds an import and reference graph across the entire in-scope file set. Each file's neighborhood (the files it depends on and the files that depend on it) is injected into its extraction prompt, enabling findings to describe inter-file flows rather than treating each file in isolation.

4. **Section aggregation** — Per-file findings are grouped by their target wiki section and synthesised into readable markdown bodies. Every asserted claim is backed by numbered citations pointing to the originating files and line ranges. Where two or more files make incompatible assertions about the same topic, the system surfaces the conflict explicitly in a dedicated *Conflicts in source* block rather than silently resolving it — a deliberate feature for legacy codebases where disagreements encode high-priority migration signals.

## Wiki Structure

The generated wiki is organised into **eleven sections**: eight primary sections populated directly from per-file evidence, and three derivative sections synthesised from the completed primaries:

| Section type | Sections |
|---|---|
| Primary (8) | Business domains, system intent, capabilities, external dependencies, integrations, cross-cutting concerns, core entities, hard specifications |
| Derivative (3) | User personas, Gherkin-style user stories, Mermaid architectural diagrams |

Derivative sections are only generated after the primaries they depend on are finalised. If upstream primary sections are empty or missing, the system writes a placeholder that declares the gap rather than fabricating content.

## Quality Assurance

An optional critic-and-reviser pass evaluates any synthesised section against its brief and the upstream evidence it drew from, producing a structured quality score (0–10) with itemised unsupported claims, gaps, and suggested edits. When a section scores below a configurable threshold, a revision is automatically invoked; the revision is accepted only if it matches or improves the original score, preventing regressions. This loop is particularly valuable for derivative sections — personas and user stories — where single-shot synthesis is most prone to introducing unsupported assertions.

## Incremental and Resumable Walks

The pipeline uses a two-scope content-addressed cache: per-file extraction results are keyed to a combination of file path and content fingerprint, and per-section aggregation results are keyed to a digest of the contributing notes payload. Only changed files and affected sections are reprocessed on incremental runs. Because results are persisted after every completed file, an interrupted walk resumes from the last unprocessed file rather than restarting from scratch. The cache can also be fully invalidated to force a clean re-walk.

## Coverage and Quality Reporting

A report command produces a human-readable markdown table summarising every wiki section by contributing file count, finding count, body size, optional critic-derived quality score, and the highest-priority content gap identified by the critic. Coverage statistics also surface *dead zones* — files that were processed but produced no findings — so teams can identify blind spots in the analysis.

## Interactive Knowledge Querying

Once a wiki has been generated, users can open an interactive conversational session grounded in all populated sections. The session supports multi-turn exchanges, conversation history reset, and introspection of which sections are currently loaded as context. Only meaningfully populated sections are included, ensuring the assistant is not grounded in placeholder content.

## Graceful Degradation

When AI synthesis fails for a section, the system falls back to emitting the raw collected notes directly in the section body, preserving information at the cost of polish and surfacing the error inline. Similarly, unparseable schema files produce an advisory finding directing reviewers to inspect the file manually rather than silently failing.

## Sources
1. `VISION.md:6-8`
2. `wikifi/sections.py:44-142`
3. `README.md:14-24`
4. `wikifi/orchestrator.py:62-76`
5. `wikifi/wiki.py:64-86`
6. `wikifi/introspection.py:28-44`
7. `wikifi/introspection.py:61-70`
8. `wikifi/walker.py:92-186`
9. `wikifi/extractor.py:140-200`
10. `wikifi/cache.py:5-8`
11. `README.md:34-36`
12. `TESTING-AND-DEMO.md:116-149`
13. `wikifi/config.py:75-81`
14. `wikifi/repograph.py:41-52`
15. `wikifi/specialized/__init__.py:46-57`
16. `wikifi/specialized/sql.py:56-62`
17. `wikifi/extractor.py:251-270`
18. `TESTING-AND-DEMO.md:40-66`
19. `wikifi/aggregator.py:1-15`
20. `TESTING-AND-DEMO.md:90-114`
21. `wikifi/config.py:69-74`
22. `wikifi/extractor.py:241-246`
23. `wikifi/repograph.py:155-210`
24. `wikifi/evidence.py:88-121`
25. `wikifi/aggregator.py:9-14`
26. `wikifi/evidence.py:13-17`
27. `VISION.md:53-63`
28. `wikifi/deriver.py:73-107`
29. `TESTING-AND-DEMO.md:151-164`
30. `wikifi/config.py:83-94`
31. `wikifi/critic.py:100-153`
32. `wikifi/deriver.py:90-103`
33. `TESTING-AND-DEMO.md:67-88`
34. `wikifi/cache.py:9-12`
35. `wikifi/config.py:63-68`
36. `wikifi/cache.py:14-18`
37. `wikifi/cache.py:105-113`
38. `README.md:16-20`
39. `wikifi/cli.py:88-112`
40. `README.md:21-23`
41. `TESTING-AND-DEMO.md:166-186`
42. `wikifi/critic.py:155-180`
43. `wikifi/report.py:44-77`
44. `wikifi/report.py:103-107`
45. `README.md:24-25`
46. `wikifi/chat.py:88-130`
47. `wikifi/chat.py:63-82`
48. `wikifi/cli.py:60-220`
49. `wikifi/aggregator.py:272-285`
50. `wikifi/specialized/openapi.py:23-50`
