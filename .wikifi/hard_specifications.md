# Hard Specifications

This section documents requirements that must be preserved verbatim through any reimplementation, migration, or refactor of the wiki-generation pipeline. They are grouped by domain.

### Output Integrity

All synthesized wiki content — including derivative sections — must be technology-agnostic: no names of specific languages, frameworks, or libraries may appear in any generated output. Every observation must be expressed in domain terms.

Contradictions between source notes must never be silently resolved. Any incompatible claims must produce a dedicated contradictions entry identifying each position and the note indices that support it. This rule applies at the aggregation stage and throughout the critic/reviser loop.

All generated section bodies must declare gaps explicitly rather than speculating or inventing claims unsupported by upstream evidence. The reviser is bound by the same constraint: fabricated claims are prohibited even when evidence is sparse.

### Quality Scoring Rubric

The scoring rubric is fixed and must not be altered:

| Score | Meaning |
|---|---|
| 9–10 | Fully grounded, tech-agnostic, narratively coherent; no unsupported claims |
| 6–8 | Minor issues acceptable |
| 3–5 | Substantial gaps or partial coverage |
| 0–2 | Incoherent or off-brief |

The minimum acceptable score for shipping a section without revision is **7**. A revised body is only accepted if its follow-up critique score is **greater than or equal to** the initial score; any revision that causes a score regression must be discarded and the original body retained.

### Evidence and Citation Format

Citations must be rendered as compact footnote-style markers (`[1]`, `[2]`, …) with a Sources footer at the bottom of each section. Line-range references follow the format `path/to/file:start-end`; when start equals end, `path/to/file:line`; when no range is known, `path/to/file` alone.

Detected contradictions must appear verbatim in wiki output under a **'Conflicts in source'** heading, with explicit direction that migration teams must resolve them before re-implementation. They must not be suppressed or merged.

Three exact sentinel strings serve as the canonical markers for unpopulated sections and must not be modified:
- `Not yet populated`
- `No findings were extracted`
- `upstream sections required to derive`

### Content Fingerprint Format

Fingerprints are defined as the first **12 hexadecimal characters** of a SHA-256 digest (48 bits of entropy). This length and format must be preserved across any migration, as fingerprints are recorded in cached artefacts and emitted into wiki evidence references.

### File-Processing Thresholds

The following thresholds are fixed pipeline constants:

| Parameter | Value |
|---|---|
| Maximum file size | 2,000,000 bytes |
| Minimum content (stripped) | 64 bytes |
| Chunk size | 150,000 bytes |
| Chunk overlap | 8,000 bytes |
| Manifest truncation limit | 20,000 bytes |

Chunk overlap must satisfy `0 ≤ overlap < chunk_size`; chunk size must be positive. These invariants must hold for the recursive splitter to terminate correctly on all inputs, including whitespace-free monolithic files.

### Cache Integrity

The aggregation cache hash must span: file reference, summary, finding text, and the full structured sources list (file path, line range, and per-source fingerprint). Omitting any of these fields allows stale citation metadata to be replayed without re-aggregation.

Cache persistence must use an atomic write pattern — write to a sibling temporary file, then rename — to guarantee that a crash during saving never produces a corrupt cache file.

### On-Disk Directory Layout

The directory layout (`.wikifi/`, `config.toml`, `.gitignore`, one markdown file per section, `.notes/`, `.cache/`) is the versioned contract with target projects and must not change in ways that break existing wikis. The `.notes/` and `.cache/` directories must always be excluded from version control; only section markdown files are committed. New required gitignore entries introduced in future versions must be backfilled automatically on the next initialization run.

### Command-Line Interface Contract

The tool's entry point name and its four subcommands (`init`, `walk`, `chat`, `report`) are contractual interfaces for users and tooling. They must not be renamed or removed.

### Pipeline Stage Boundaries

- **Stage 1** must operate without reading any source files; it sees only directory-level summaries and manifest contents. Source reading is exclusively Stage 2's responsibility.
- **Stage 2** targets only primary wiki sections during per-file extraction. Derivative sections (personas, user stories, diagrams) are explicitly excluded from this stage and are produced later from aggregated primary findings.
- Include and exclude patterns produced by Stage 1 must be in gitignore-style format relative to the repository root.[23]

### Section Taxonomy Invariant

Every derivative section must reference only known section IDs, and every upstream dependency must appear earlier in the canonical section ordering. This ordering invariant is validated at module load time; violations raise an error.

### Note Index Invariant

Note indices presented to the synthesis stage are **1-based**. The resolution logic subtracts 1 before indexing into the notes list. This off-by-one invariant must be preserved if the prompting scheme changes.

### Derivative Section Output Formats

Gherkin-style outputs must use proper `Given/When/Then` syntax inside fenced `gherkin` code blocks. Diagram outputs must be valid and inside fenced `mermaid` code blocks, with `graph`, `classDiagram`, `erDiagram`, and `sequenceDiagram` as the preferred diagram types.

### Provider API Contract

The provider contract consists of exactly three interaction modes — structured completion, text completion, and chat. No other methods are ever invoked; any conforming implementation must satisfy all three signatures exactly.

Additional provider-specific invariants that must be carried forward:

- Sampling parameters (temperature, top_p, top_k) must **not** be sent to certain hosted reasoning models; doing so causes a 400 validation error. They must be omitted entirely, not conditionally included.
- Reasoning-capable model families (identified by specific name prefixes) must receive `max_completion_tokens` instead of `max_tokens`, and may optionally receive a `reasoning_effort` value of `low`, `medium`, or `high`. Non-reasoning models must not receive `reasoning_effort`.
- Disabling the reasoning trace on certain locally-hosted model families causes them to ignore schema constraints and emit free text. Reasoning must default to **high** and must never be disabled for these models in the structured-output path.
- The default request timeout for locally-hosted model backends is **900 seconds**, chosen to absorb 1–3 minute per-file latencies at high thinking levels. Reducing this timeout risks aborting in-progress reasoning traces.
- The default output token cap for the hosted cloud provider is **32,000** tokens per call; for the OpenAI-compatible provider it is **16,000** tokens per call.
- When the structured-output parse path returns no parsed object (due to refusal or truncation), the implementation must fall back to validating raw JSON text against the schema, not return null. The provider protocol's contract is to raise on failure, never to silently return nothing.

### Model Identifier Heuristics

When the hosted-Claude backend is configured but no matching model identifier is detected, the system falls back to `claude-opus-4-7`. The Ollama model identifier heuristic is: a string containing `:` that does not begin with the prefix `ft:` (case-insensitive). This exact rule must be carried forward without modification to avoid misclassifying fine-tuned model identifiers or Azure deployment IDs.

### Specialized Extractor Rules

- Only migration files with `.sql` or `.ddl` suffixes are routed to the SQL migration extractor; all other migration files fall through to the general extraction path. Routing is determined by file suffix, not file-kind classification.
- When an API contract file is present but cannot be parsed, an explicit warning finding must be emitted directing migration teams to review the file manually. The file must not be silently dropped.
- Service-to-RPC attribution in protocol definition files must be computed by tracking brace depth (counting nested blocks), not by line proximity, to correctly handle multi-service files.
- Index definitions must be emitted as explicit findings recording that they encode query-time performance invariants which must be preserved through migration.

## Supporting claims
- All synthesized wiki content must be technology-agnostic: no names of specific languages, frameworks, or libraries may appear in any generated output, and every observation must be expressed in domain terms. [1][2][3]
- Contradictions between source notes must never be silently resolved; any incompatible claims must produce a dedicated contradictions entry identifying each position and the supporting note indices. [4]
- All generated section bodies must declare gaps explicitly rather than speculating or inventing claims unsupported by upstream evidence; this constraint applies to the reviser as well. [2][5]
- The scoring rubric is fixed: 9–10 fully grounded and coherent; 6–8 minor issues; 3–5 substantial gaps; 0–2 incoherent or off-brief. [6]
- The minimum acceptable score for shipping a section without revision is 7. [6]
- A revised body is only accepted if its follow-up critique score is greater than or equal to the initial score; any revision that causes a score regression must be discarded and the original body retained. [7]
- Citations must be rendered as compact footnote-style markers with a Sources footer; line ranges formatted as path:start-end, path:line for single lines, and path alone when unknown. [8]
- Detected contradictions must appear verbatim in wiki output under a 'Conflicts in source' heading and must not be suppressed or merged. [9]
- Three exact sentinel strings mark unpopulated sections and must not be modified: 'Not yet populated', 'No findings were extracted', and 'upstream sections required to derive'. [10]
- Fingerprints are defined as the first 12 hexadecimal characters of a SHA-256 digest and this format must be preserved across any migration. [11]
- The maximum file size threshold is 2,000,000 bytes; the minimum content threshold is 64 bytes of stripped text; chunk size is 150,000 bytes with 8,000 bytes of overlap; manifest files are truncated to 20,000 bytes. [12][13][14]
- Chunk overlap must satisfy 0 ≤ overlap < chunk_size and chunk size must be positive; these invariants must hold for the recursive splitter to terminate correctly. [15]
- The aggregation cache hash must span file reference, summary, finding text, and the full structured sources list; omitting any field allows stale citation metadata to be replayed. [16]
- Cache persistence must use an atomic write pattern (write to a sibling temp file, then rename) to guarantee a crash never produces a corrupt cache file. [17]
- The on-disk directory layout is the versioned contract with target projects and must not change in ways that break existing wikis. [18]
- .notes/ and .cache/ directories must always be excluded from version control; only section markdown files are committed. New gitignore entries must be backfilled automatically on next init. [19]
- The tool's entry point name and its four subcommands (init, walk, chat, report) are contractual interfaces and must not be renamed or removed. [20]
- Stage 1 must operate without reading any source files; it sees only directory-level summaries and manifest contents. [21]
- Stage 2 targets only primary wiki sections; derivative sections are excluded and produced later from aggregated primary findings. [22]
- Every derivative section must reference only known section IDs and every upstream dependency must appear earlier in the canonical section ordering; violations raise an error at load time. [24]
- Note indices presented to the synthesis stage are 1-based and the resolution logic subtracts 1 before indexing; this off-by-one invariant must be preserved if the prompting scheme changes. [25]
- Gherkin-style outputs must use Given/When/Then syntax inside fenced gherkin code blocks; diagrams must be valid and inside fenced mermaid code blocks. [26]
- The provider contract consists of exactly three interaction modes — structured completion, text completion, and chat — and any conforming implementation must satisfy all three signatures exactly. [27]
- Sampling parameters must not be sent to certain hosted reasoning models; doing so causes a 400 error and they must be omitted entirely. [28]
- Reasoning-capable model families must receive max_completion_tokens instead of max_tokens and may receive reasoning_effort; non-reasoning models must not receive reasoning_effort. [29]
- Reasoning must default to high and must never be disabled for certain locally-hosted model families in the structured-output path, as disabling it causes schema constraints to be ignored. [30]
- The default request timeout for locally-hosted model backends is 900 seconds, chosen to absorb 1–3 minute per-file latencies; reducing it risks aborting in-progress reasoning traces. [31]
- The default output token cap for the hosted cloud provider is 32,000 tokens per call; for the OpenAI-compatible provider it is 16,000 tokens per call. [32][33][34]
- When the structured-output parse path returns no parsed object, the implementation must fall back to validating raw JSON text against the schema rather than returning null. [35][36]
- When the hosted-Claude backend is configured but no matching model identifier is detected, the system falls back to claude-opus-4-7. [37]
- The Ollama model identifier heuristic is: a string containing ':' that does not begin with the prefix 'ft:' (case-insensitive); this rule must be preserved exactly. [38]
- Only migration files with .sql or .ddl suffixes are routed to the SQL migration extractor; routing is determined by file suffix, not file-kind classification. [39]
- When an API contract file cannot be parsed, an explicit warning finding must be emitted; the file must not be silently dropped. [40]
- Service-to-RPC attribution in protocol definition files must be computed by tracking brace depth, not by line proximity. [41]
- Index definitions must be emitted as explicit findings recording that they encode query-time performance invariants that must be preserved through migration. [42]

## Conflicts in source
_The walker found disagreements across files. Migration teams should resolve these before re-implementation._

- **Notes disagree on whether a file of exactly 2,000,000 bytes is skipped: one states files 'larger than' that threshold are skipped (exclusive boundary), while another states files 'at or above' that limit are skipped (inclusive boundary).**
  - Files larger than 2,000,000 bytes are unconditionally skipped — implying a file of exactly 2,000,000 bytes would not be skipped. (`wikifi/config.py:59-65`)
  - Files at or above 2,000,000 bytes are unconditionally skipped — implying a file of exactly 2,000,000 bytes would be skipped. (`wikifi/walker.py:61-79`)

## Sources
1. `wikifi/aggregator.py:57-59`
2. `wikifi/critic.py:53-61`
3. `wikifi/deriver.py:37-39`
4. `wikifi/aggregator.py:61-63`
5. `wikifi/deriver.py:34-50`
6. `wikifi/critic.py:31-48`
7. `wikifi/critic.py:137-147`
8. `wikifi/evidence.py:43-52`
9. `wikifi/evidence.py:121-131`
10. `wikifi/report.py:103-108`
11. `wikifi/fingerprint.py:23-27`
12. `wikifi/config.py:59-65`
13. `wikifi/config.py:66-81`
14. `wikifi/walker.py:61-79`
15. `wikifi/extractor.py:302-308`
16. `wikifi/cache.py:243-255`
17. `wikifi/cache.py:205-209`
18. `wikifi/wiki.py:1-8`
19. `wikifi/wiki.py:36-47`
20. `wikifi/cli.py:1-7`
21. `wikifi/introspection.py:5-9`
22. `wikifi/extractor.py:51-56`
23. `wikifi/introspection.py:50-58`
24. `wikifi/sections.py:148-158`
25. `wikifi/aggregator.py:167-173`
26. `wikifi/deriver.py:40-45`
27. `wikifi/providers/base.py:42-52`
28. `wikifi/providers/anthropic_provider.py:14-17`
29. `wikifi/providers/openai_provider.py:215-235`
30. `wikifi/providers/ollama_provider.py:9-27`
31. `wikifi/providers/ollama_provider.py:50-54`
32. `wikifi/config.py:122-134`
33. `wikifi/providers/anthropic_provider.py:70-79`
34. `wikifi/providers/openai_provider.py:59-66`
35. `wikifi/providers/anthropic_provider.py:107-145`
36. `wikifi/providers/openai_provider.py:136-144`
37. `wikifi/orchestrator.py:160-200`
38. `wikifi/orchestrator.py:205-215`
39. `wikifi/specialized/dispatch.py:28-62`
40. `wikifi/specialized/openapi.py:24-37`
41. `wikifi/specialized/protobuf.py:62-67`
42. `wikifi/specialized/sql.py:115-121`
