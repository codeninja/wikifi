# Capabilities

wikifi turns any codebase into a structured, technology-agnostic wiki by walking source files, extracting structured knowledge, and synthesizing readable documentation with a full evidence trail that links every assertion back to specific source locations.

## Documentation Pipeline

Documentation is produced through four ordered stages:

**1. Repository Triage**
The system examines the directory layout and manifest files to determine which paths contain production source worth deeper analysis and which should be skipped (vendored dependencies, build artifacts, generated files, CI configuration). Files outside configurable size bounds are excluded before any analysis begins.[7][8]

**2. Per-file Extraction**
Each in-scope file is analyzed to produce structured findings describing its contribution to each wiki section.[9] Files whose format is well-structured — relational schemas, API contracts, interface definitions, and migration scripts — are routed to dedicated deterministic extractors that bypass AI inference entirely, improving accuracy and reducing cost for these artifact types. General-purpose source files are analyzed via AI inference, with large files split into overlapping chunks so no content is lost at boundaries. Findings are deduplicated across chunk boundaries to avoid double-counting, and each finding carries a citation (path and line range) for downstream traceability.

Optionally, the system builds a cross-file import and reference graph before extraction begins. Each file's extraction is then enriched with its neighborhood in that graph — which files it depends on and which depend on it — enabling findings to describe cross-file flows rather than treating files in isolation.

**3. Section Synthesis**
Per-file findings are aggregated into coherent, readable markdown bodies for each primary wiki section. Every assertion in the output is backed by numbered citations traceable to the specific source files and line ranges from which it was inferred.

**4. Derivative Section Generation**
Higher-level artifacts — user personas, scenario-based user stories, and architectural diagrams — are synthesized from the finalized primary sections. If upstream content is absent, the system writes a placeholder declaring the gap rather than fabricating content.

## Wiki Structure

The generated wiki covers **eight primary sections**: business domains, system intent, capabilities, external dependencies, integrations, cross-cutting concerns, core entities, and hard specifications. Three derivative sections (personas, user stories, architectural diagrams) are generated only after all relevant primary sections are finalized.

The system can scaffold a complete wiki directory structure in a target project in an idempotent manner — re-running initialization leaves existing content untouched while creating any missing pieces.

## Conflict Detection and Evidence Traceability

When source files make incompatible assertions about the same domain topic, the conflict is surfaced explicitly under a dedicated heading rather than silently resolved. This is a deliberate design choice for legacy codebases, where tribal knowledge often hides in inconsistencies; teams are directed to resolve conflicts before re-implementation. Claims that appear in the supporting evidence but cannot be matched to the synthesized narrative body are collected into a separate supporting-claims list, ensuring nothing is silently dropped.

## Quality Assurance

An optional critic-and-reviser loop evaluates each synthesized section against a structured rubric (scored 0–10), identifies unsupported claims and coverage gaps, and triggers a revision pass when the score falls below a configurable threshold. A revised body is accepted only if it improves or matches the prior score, preventing regressions. The loop is off by default to keep generation time predictable, but is most beneficial for derivative sections where single-shot synthesis is most likely to stray from evidence. If synthesis fails entirely for a section, the system falls back to emitting the raw notes directly, preserving information at the cost of polish.

## Coverage and Readiness Reporting

A dedicated report command produces a markdown table listing each section with its file count, finding count, body size, quality score, and the most prominent gap or unsupported claim — giving teams a one-page readiness summary. The coverage portion requires no AI provider and is safe for automated pipelines.

## Incremental and Crash-Resumable Operation

Two independently keyed caches — one per file (keyed by content fingerprint) and one per section (keyed by a hash of its full notes payload) — allow re-walks to skip unchanged material entirely. The cache is written after each file completes, making the pipeline crash-resumable.[34] Stale entries for files removed from the repository can be pruned. A monotonically incremented version number embedded in every cache file causes a clean rebuild on version mismatch, preventing stale data from surviving format upgrades. Cache files are written atomically so a crash during persistence never corrupts the stored state. A force-reanalysis mode is also available to drop the cache entirely and perform a clean walk.

## Interactive Query Interface

Once a wiki is generated, users can open a conversational session grounded in the populated wiki sections. Only sections with meaningful content are loaded as context. The session supports multi-turn questioning, conversation history reset while retaining the wiki context, and inspection of which sections are currently loaded.

## Supporting claims
- wikifi produces a technology-agnostic wiki from any codebase, linking every assertion back to specific source locations. [1][2][3]
- Stage 1 examines the directory layout and manifest files to classify paths as worth walking or skippable (vendored dependencies, build output, generated files, CI configuration). [4][5][6]
- Files with well-structured formats (relational schemas, API contracts, interface definitions, migration scripts) are routed to dedicated deterministic extractors that bypass AI inference entirely. [10][11][12][13][14][15]
- Large files are split into overlapping chunks so no content is lost at boundaries, with separators tried from coarsest to finest. [16]
- Findings are deduplicated across chunk boundaries to avoid double-counting, and each finding carries a citation (path and line range). [9]
- The system optionally builds a cross-file import and reference graph, injecting each file's neighborhood into its extraction pass to enable cross-file flow descriptions. [17][18][19]
- Per-file findings are aggregated into coherent, readable markdown bodies for each primary wiki section, with every assertion backed by numbered citations. [1][3]
- Derivative sections — user personas, scenario-based user stories, and architectural diagrams — are synthesized from finalized primary sections; absent upstream content produces a placeholder rather than fabricated content. [20][21]
- The wiki covers eight primary sections and three derivative sections; derivative sections are generated only after their upstream primaries are finalized. [21]
- The system scaffolds a complete wiki directory structure idempotently, leaving existing content untouched while creating missing pieces. [22]
- Incompatible assertions across source files are surfaced explicitly under a dedicated heading rather than silently resolved — a deliberate feature for legacy codebases where tribal knowledge hides in inconsistencies. [23][24]
- Claims that appear in the supporting evidence but cannot be matched to the narrative body are collected into a separate supporting-claims list rather than silently dropped. [3]
- An optional critic-and-reviser loop evaluates each synthesized section on a 0–10 rubric, identifies unsupported claims and gaps, and triggers revision when the score falls below a configurable threshold, accepting the revision only if it improves or matches the prior score. [25][26]
- The critic-reviser loop is off by default to keep generation time predictable, and is most beneficial for derivative sections where single-shot synthesis is most likely to fabricate. [25][27]
- If synthesis fails entirely, the system falls back to emitting raw notes directly in the section body, preserving information at the cost of polish. [28]
- A report command produces a per-section markdown table with file counts, finding counts, body size, quality score, and the most prominent gap or unsupported claim. [29][30][31]
- The coverage portion of the report requires no AI provider and is safe for automated pipelines. [29]
- Two independently keyed caches — per-file (content fingerprint) and per-section (notes-payload hash) — allow re-walks to skip unchanged material entirely. [32][33][34]
- Stale cache entries for removed files can be pruned in bulk. [35][18]
- A monotonically incremented version number in every cache file triggers a clean rebuild on version mismatch, preventing stale data from surviving upgrades. [36]
- Cache files are written atomically so a crash during persistence never leaves a corrupted cache. [37]
- A force-reanalysis mode drops the on-disk cache entirely to perform a clean walk. [38]
- Users can open a conversational session grounded in populated wiki sections, supporting multi-turn questioning, history reset, and inspection of loaded sections. [39][2]
- Only sections with meaningful content are loaded as context for the conversational session; placeholder sections are filtered out. [40]

## Sources
1. `wikifi/aggregator.py:1-15`
2. `wikifi/cli.py:63-210`
3. `wikifi/evidence.py:85-120`
4. `wikifi/introspection.py:28-44`
5. `wikifi/introspection.py:61-70`
6. `wikifi/walker.py:92-186`
7. `.env.example:20-29`
8. `wikifi/walker.py:100-130`
9. `wikifi/extractor.py`
10. `wikifi/config.py:97-102`
11. `wikifi/extractor.py:183-218`
12. `wikifi/repograph.py:1-15`
13. `wikifi/specialized/__init__.py:8-11`
14. `wikifi/specialized/dispatch.py:44-62`
15. `wikifi/specialized/models.py:4-6`
16. `wikifi/extractor.py:298-360`
17. `wikifi/config.py:60-93`
18. `wikifi/orchestrator.py:55-145`
19. `wikifi/repograph.py:162-215`
20. `wikifi/deriver.py:73-107`
21. `wikifi/sections.py:44-142`
22. `wikifi/wiki.py:72-101`
23. `wikifi/aggregator.py:9-14`
24. `wikifi/evidence.py:121-133`
25. `wikifi/config.py:103-113`
26. `wikifi/critic.py:100-153`
27. `wikifi/deriver.py:90-103`
28. `wikifi/aggregator.py:272-285`
29. `wikifi/report.py:82-85`
30. `wikifi/report.py:106-114`
31. `wikifi/report.py:46-74`
32. `wikifi/cache.py:5-15`
33. `wikifi/config.py:88-96`
34. `wikifi/extractor.py:166-182`
35. `wikifi/cache.py:113-118`
36. `wikifi/cache.py:37`
37. `wikifi/cache.py:205-209`
38. `wikifi/cli.py:90-122`
39. `wikifi/chat.py:88-130`
40. `wikifi/chat.py:63-82`
