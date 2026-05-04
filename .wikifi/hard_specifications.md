# Hard Specifications

## Technology-Agnostic Output Mandate

All generated content at every stage of the pipeline must be expressed in technology-agnostic domain language. No specific languages, frameworks, or library names may appear in findings, synthesized bodies, derivative sections, or introspection outputs. This requirement applies to per-file extraction, aggregation, derivation, and chat responses alike.

## File Intake Thresholds

Two size-based hard cutoffs govern which files may enter the analysis pipeline:

| Condition | Threshold | Action |
|---|---|---|
| File size exceeds | 2,000,000 bytes | Unconditionally skipped (treated as vendored or generated noise) |
| Stripped text content shorter than | 64 bytes | Unconditionally skipped (prevents speculative AI reasoning on near-empty stubs) |

These thresholds are applied both by the filesystem walker and independently in configuration, making them doubly enforced.

## Chunking Parameters

The content chunking window is fixed at **150,000 bytes** with an **8,000-byte overlap** between adjacent chunks. The overlap is required to preserve cross-boundary context and must be maintained whenever chunking logic is modified. The invariant `0 ≤ overlap < chunk_size` is enforced as a hard error; any violation raises immediately. The recursive splitting strategy must guarantee full coverage of any input — no content may be silently dropped regardless of format.

## Identity and Cache Rules

**Finding identity** is defined as the SHA-256 digest of the concatenation `file::section_id::finding`, truncated to 16 hexadecimal characters. A single-character change to any of the three components produces a different identity, treated as a delete-plus-insert rather than an edit, invalidating any cached prose referencing the prior wording.

**Content fingerprints** must be exactly 12 hexadecimal characters derived from the leading 12 characters of a SHA-256 digest computed over raw bytes (not decoded text), ensuring encoding-independence across all subsystems.

**Aggregation cache keys** must include the full sources list — file reference, line range, and content fingerprint per citation — not merely the finding text. When a cited file's line numbers shift or its content changes, the cache must miss and aggregation must rerun against fresh evidence.

**Review-mode cache asymmetry**: an entry produced under the critic-review mode must not be silently served to a walk running without review. The reverse is permitted — a reviewed body is considered strictly higher quality and may be reused by a non-review walk. For derivative sections, both a matching upstream-content hash and a matching review-mode flag are required for cache reuse.

## Directory Layout and Storage Formats

The wiki artefact directory must be named `.wikifi/` and must reside inside the target project root. The chat and report commands treat the existence of this directory as a hard pre-condition and refuse to proceed without it. The `.wikifi/` layout is declared a stable forward-compatible contract; any new required scaffolding entries must be backfilled into existing wikis on the next initialisation run.

**Notes storage format**: notes are stored as JSONL (one JSON object per line). Each record must include a `timestamp` field in ISO-8601 UTC format. This format is consumed by the aggregation stage and must remain stable across versions.

**Citation format**: citations must be rendered as compact footnote-style markers (`[1]`, `[2]`, …) with an explicit numbered "Sources" footer at the bottom of each section. Line-precise references must be formatted as `path/to/file:start-end` or `path/to/file:line` when line information is available. Inline annotation must use a conservative verbatim substring match — a claim is only inlined next to a matching sentence when the claim's exact text appears in the body; paraphrased bodies must place claims in a separate "Supporting claims" list to prevent mis-attribution.

**Report sentinel values**: section bodies containing the strings `Not yet populated`, `No findings were extracted`, or `upstream sections required to derive` are contractually treated as empty and excluded from quality scoring. These values form a stable interface between the writer and the reporter.

## Section Taxonomy and Pipeline Stages

The analysis pipeline is divided into exactly four named stages in fixed order: Stage 1 Introspection, Stage 2 Extraction, Stage 3 Aggregation, and Stage 4 Derivation.[21] This four-stage contract is surfaced to users in walk report output.

The canonical set of section identifiers is fixed:

`domains`, `intent`, `capabilities`, `external_dependencies`, `integrations`, `cross_cutting`, `entities`, `hard_specifications`, `personas`, `user_stories`, `diagrams`

Derivative sections must declare their upstream dependencies; those upstreams must exist in the taxonomy and appear earlier in the ordered sequence. This ordering constraint is validated at startup and failure raises an error. Per-file extraction is restricted to primary section IDs only; derivative sections are produced exclusively in Stage 4.[23]

## Quality Scoring Rubric

The quality rubric is fixed:

| Score range | Meaning |
|---|---|
| 9–10 | Technology-agnostic, fully evidence-grounded, no unsupported claims |
| 6–8 | Largely sound with minor issues |
| 3–5 | Substantial gaps or partial coverage |
| 0–2 | Incoherent or off-brief |

The score field is constrained to integers 0–10 inclusive. The default acceptance threshold (below which revision is triggered) is **7**. A revised body is only accepted when its score is greater than or equal to the score it replaces, preventing quality regressions.

## Surgical Edit Constraints

When incremental updates are applied surgically:

- Unchanged paragraphs **must** appear in the output exactly as they appeared in the input. This is a hard preservation rule, not a soft preference.
- Claim and finding indices are 1-based throughout: added findings are tagged `[A1]`, `[A2]`, …; cached claims are tagged `[C1]`, `[C2]`, …; removed findings are tagged `[R1]`, `[R2]`, …. Any deviation breaks citation re-anchoring.
- The contradictions field in surgical edit output is a **full replacement** of the cached contradictions list, not a delta; the model must include contradictions that survived the edit as well as any new ones.

## Configuration Precedence

Configuration resolution precedence is contractual: the wiki's own config file overrides environment variables when present.[29] This contract is printed at the top of every generated config file and must be preserved.

## Inference Provider Constraints

**Structured output** is obtained via the inference provider SDK's schema-constrained decoding path, not via manually constructed tool-use blocks. This path is load-bearing for extraction correctness.

**Output token limits**: the default output token ceiling for the extended-reasoning hosted path is 32,000 tokens — headroom required because reasoning traces consume output tokens before producing the structured result. The default ceiling for the direct API path is 16,000 tokens. Reasoning-capable model families must receive the output token limit under a distinct request parameter name from plain chat models; sending the wrong parameter name causes a 400 error.

**Temperature**: on any schema-constrained completion call via the local inference path, temperature must be 0 to preserve reproducibility of structured output. Thinking mode must not be disabled for certain local model families that rely on it for schema adherence, as disabling it causes the model to ignore the output schema and produce unparseable free text.

**Sampling parameters**: for certain hosted model variants, sampling parameters (temperature, top_p, top_k) must not be sent at all — the API returns a 400 error if they are present.

**Request timeout**: the default request timeout is 900 seconds and must not be reduced when high-reasoning mode is active.

**System prompt position**: the system prompt must always be sent at message position 0 to ensure prefix caching eligibility.

**Model identifier routing**: a model name containing a colon separator (family:tag) is treated as a local inference identifier and swapped for a provider-appropriate default when a hosted provider is selected, except when the name begins with `ft:` (a fine-tuned model prefix), which is left unchanged.

## File Classification Rules

**OpenAPI/Swagger detection** is performed against only the first 4,096 bytes of candidate files. Parse failures on API contract files must never crash the documentation walk; exactly one advisory finding must be emitted directing users to inspect the file manually.

**Migration directory detection** uses a fixed enumeration of path tokens: `/migrations/`, `/alembic/`, `/db/migrate/`, `/database/migrations/`, `/prisma/migrations/`, `/flyway/`, `/liquibase/`. Files matching these tokens are classified as migrations rather than generic source.

**SQL extractor routing**: only migration files with the exact extension `.sql` or `.ddl` are routed to the SQL migration extractor. Migration files in any other form must fall through to prose LLM extraction. This rule must be preserved under any refactor.

**Schema index preservation**: every index discovered in a schema is recorded with the explicit requirement that it encodes a query-time performance invariant the new system must preserve, treating index existence as a non-negotiable carry-forward obligation rather than an implementation detail.

## Hallucination Avoidance Contracts

Two system-level prompts encode explicit anti-hallucination contracts:

- The chat interface requires the assistant to ground every answer in the wiki material and to explicitly acknowledge when something is not covered, rather than fabricating detail.
- Derivative synthesis output must be grounded exclusively in the upstream sections provided; the model must declare a gap rather than invent any fact not supported by upstream evidence.

## Fixed Exclusion Patterns

A fixed set of directory and file patterns is unconditionally excluded from the analysis pipeline regardless of user configuration or ignore-file contents, including: version control metadata directories, common dependency caches, build output directories, the tool's own working directory, and compiled binary file extensions (including lock files and minified assets).

## Supporting claims
- All generated content at every stage of the pipeline must be expressed in technology-agnostic domain language with no specific language, framework, or library names. [1][2][3][4]
- Files exceeding 2,000,000 bytes are unconditionally skipped and treated as vendored or generated noise. [5][6]
- Files whose stripped text content is shorter than 64 bytes are unconditionally skipped to prevent speculative AI reasoning on stubs. [5][7]
- The content chunking window is fixed at 150,000 bytes with an 8,000-byte overlap between adjacent chunks. [8][9]
- The invariant 0 ≤ overlap < chunk_size is enforced as a hard error on any change to chunking logic. [9]
- Finding identity is SHA-256(file::section_id::finding) truncated to 16 hex characters; a single-character change to any component is treated as a delete-plus-insert invalidating cached prose. [10]
- Content fingerprints must be exactly 12 hexadecimal characters derived from the leading 12 characters of a SHA-256 digest computed over raw bytes. [11]
- Aggregation cache keys must include the full sources list (file reference, line range, and content fingerprint per citation), not merely the finding text. [12]
- A cache entry produced under critic-review mode must not be silently served to a non-review walk; the reverse is permitted. [13]
- Derivative section cache reuse requires both a matching upstream-content hash and a matching review-mode flag. [14]
- The wiki artefact directory must be named .wikifi/ inside the target project root; its absence is a hard pre-condition that blocks chat and report commands. [15][16]
- The .wikifi/ directory layout is a stable forward-compatible contract; new scaffolding must be backfilled into existing wikis on the next initialisation run. [16]
- Notes are stored as JSONL with one JSON object per line; each record must include a timestamp field in ISO-8601 UTC format, and this format must remain stable across versions. [17]
- Citations must be rendered as compact footnote-style markers ([1], [2], …) with an explicit numbered Sources footer; line-precise references must use path/to/file:start-end or path/to/file:line format. [18]
- Inline annotation uses a conservative verbatim substring match; paraphrased bodies must place claims in a separate Supporting claims list to prevent mis-attribution. [19]
- Section bodies containing the strings 'Not yet populated', 'No findings were extracted', or 'upstream sections required to derive' are contractually treated as empty and excluded from quality scoring. [20]
- The canonical set of section identifiers is fixed and must be preserved; derivative sections must declare upstreams that exist in the taxonomy and appear earlier in the ordered sequence, validated at startup. [22]
- The quality rubric is fixed on a 0–10 integer scale with defined bands: 9–10 fully grounded, 6–8 largely sound, 3–5 substantial gaps, 0–2 incoherent. [24]
- The default acceptance threshold below which revision is triggered is a score of 7; a revised body is only accepted when its score is greater than or equal to the score it replaces. [24][25]
- Unchanged paragraphs in surgical edits must appear in the output exactly as they appeared in the input — a hard preservation rule. [26]
- Claim and finding indices in surgical edit prompts are 1-based: added findings tagged [A1]/[A2]/…, cached claims tagged [C1]/[C2]/…, removed findings tagged [R1]/[R2]/…. [27]
- The contradictions field in surgical edit output is a full replacement of the cached list, not a delta. [28]
- Structured output is obtained via the SDK's schema-constrained decoding path, not via manually constructed tool-use blocks; this path is load-bearing for extraction correctness. [30]
- The default output token ceiling for the extended-reasoning hosted path is 32,000 tokens; too low a limit causes the reasoning trace to exhaust the budget and return an empty structured response. [31]
- The default output token ceiling for the direct API path is 16,000 tokens and the default request timeout is 900 seconds. [32]
- Reasoning-capable model families must receive the output token limit under a distinct parameter name from plain chat models; sending the wrong name causes a 400 error. [33]
- On schema-constrained completion calls via the local inference path, temperature must be 0 to preserve reproducibility of structured output. [34]
- Thinking mode must not be disabled for certain local model families, as disabling it causes the model to ignore the output schema and produce unparseable free text. [34]
- For certain hosted model variants, sampling parameters (temperature, top_p, top_k) must not be sent at all; the API returns a 400 error if they are present. [35]
- The default request timeout is 900 seconds and must not be reduced when high-reasoning mode is active. [34][32]
- The system prompt must always be sent at message position 0 to ensure prefix caching eligibility. [32]
- A model name with a colon separator is treated as a local inference identifier and swapped for a provider default when a hosted provider is selected, except names beginning with ft: which are left unchanged. [36]
- OpenAPI/Swagger detection is performed against only the first 4,096 bytes of candidate files; parse failures must never crash the walk and must emit exactly one advisory finding. [37][38]
- Migration directory detection uses a fixed enumeration of path tokens: /migrations/, /alembic/, /db/migrate/, /database/migrations/, /prisma/migrations/, /flyway/, /liquibase/. [39]
- Only migration files with the exact extension .sql or .ddl are routed to the SQL migration extractor; all other forms must fall through to prose LLM extraction. [40]
- Every index discovered in a schema encodes a query-time performance invariant the new system must preserve — a non-negotiable carry-forward obligation. [41]
- The chat interface requires the assistant to ground every answer in the wiki material and explicitly acknowledge gaps rather than fabricating detail. [42]
- Derivative synthesis output must be grounded exclusively in the upstream sections provided; the model must declare a gap rather than invent unsupported facts. [43]
- A fixed set of directory and file patterns is unconditionally excluded from the analysis pipeline regardless of user configuration or ignore-file contents. [44]
- Contradictions must never be silently resolved; the aggregator must emit a structured contradictions[] entry naming each incompatible position and its supporting note indices. [1]

## Sources
1. `wikifi/aggregator.py:55-72`
2. `wikifi/deriver.py:39-41`
3. `wikifi/extractor.py:65-69`
4. `wikifi/introspection.py:15-40`
5. `wikifi/config.py:64-82`
6. `wikifi/walker.py:70-73`
7. `wikifi/walker.py:74-76`
8. `wikifi/config.py:73-80`
9. `wikifi/extractor.py:317-321`
10. `wikifi/cache.py:389-408`
11. `wikifi/fingerprint.py:22-52`
12. `wikifi/cache.py:353-373`
13. `wikifi/cache.py:234-248`
14. `wikifi/deriver.py:148-160`
15. `wikifi/cli.py:205-240`
16. `wikifi/wiki.py:1-10`
17. `wikifi/wiki.py:135-142`
18. `wikifi/evidence.py:1-18`
19. `wikifi/evidence.py:168-185`
20. `wikifi/report.py:117-122`
21. `wikifi/cli.py:151-200`
22. `wikifi/sections.py:41-156`
23. `wikifi/extractor.py:45-50`
24. `wikifi/critic.py:33-52`
25. `wikifi/critic.py:63-65`
26. `wikifi/surgical.py:47-50`
27. `wikifi/surgical.py:60-67`
28. `wikifi/surgical.py:63-66`
29. `wikifi/config.py:9-21`
30. `wikifi/providers/anthropic_provider.py:19-24`
31. `wikifi/providers/anthropic_provider.py:60-69`
32. `wikifi/providers/openai_provider.py:55-61`
33. `wikifi/providers/openai_provider.py:224-228`
34. `wikifi/providers/ollama_provider.py:1-40`
35. `wikifi/providers/anthropic_provider.py:20-27`
36. `wikifi/orchestrator.py:307-316`
37. `wikifi/repograph.py:111-120`
38. `wikifi/specialized/openapi.py:7-11`
39. `wikifi/repograph.py:94-108`
40. `wikifi/specialized/dispatch.py:28-56`
41. `wikifi/specialized/sql.py:112-121`
42. `wikifi/chat.py:25-31`
43. `wikifi/deriver.py:36-52`
44. `wikifi/walker.py:22-52`
