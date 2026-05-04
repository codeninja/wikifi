# Hard Specifications

## Output Integrity

These rules govern what the system is permitted to emit and are enforced at multiple stages of the pipeline.

- **Tech-agnostic language.** All synthesised wiki content — both primary sections and derivative sections such as personas, user stories, and diagrams — must be free of specific language, framework, or library names. Every such observation must be translated into domain terms. This constraint applies equally to the aggregator, the reviser, and the deriver.
- **No silent contradiction resolution.** Whenever two source notes make incompatible claims about the same topic, the output must include a `contradictions[]` entry naming each position and the note indices that support it. Suppressing or merging conflicting claims is forbidden.
- **No invented facts.** When evidence is absent, the system must declare the gap explicitly rather than speculating.[2][6] This applies to both primary aggregation and derivative synthesis.
- **Derivative sections grounded in upstream content only.** Derivative sections must draw exclusively on the aggregated bodies of the primary sections that precede them in the canonical section ordering; they may not introduce claims not present in those upstream bodies.

## Evidence and Citation Format

The citation scheme is a contractual output format.

- Claims must be rendered with compact footnote-style markers (`[1]`, `[2]`, …) and a **Sources** footer at the bottom of each section.
- Line ranges are formatted as `path/to/file:start-end`; a single-line reference as `path/to/file:line`; an unknown range as `path/to/file` alone.
- Detected contradictions must appear verbatim under a **Conflicts in source** heading with an explicit instruction that migration teams must resolve them before re-implementation. They must not be suppressed.
- Note indices presented to the synthesis stage are 1-based; the internal resolution step subtracts 1 before indexing into the underlying list. This off-by-one invariant must be preserved if the prompting scheme is ever changed.

## File Processing Thresholds

| Parameter | Value | Rule |
|---|---|---|
| Maximum file size | 2,000,000 bytes | Files at or above this limit are unconditionally skipped and never read |
| Minimum content size | 64 bytes (stripped) | Files below this threshold are skipped entirely |
| Chunk window | 150,000 bytes | Fixed sliding-window size for splitting large files |
| Chunk overlap | 8,000 bytes | Overlap between adjacent chunks to preserve cross-boundary context |
| Manifest truncation | 20,000 bytes | Manifest files are truncated to this length before inclusion in any prompt |

Additionally, chunk overlap must satisfy `0 ≤ overlap < chunk_size`, and chunk size must be positive. These inequalities are hard invariants; violating them causes the recursive splitter to fail on edge-case inputs such as whitespace-free monolithic files.

## Caching Constraints

- **Aggregation cache key completeness.** The hash used to key an aggregation result must span the file reference, summary, finding text, and the full structured sources list (file path, line range, and fingerprint per source). Omitting any field allows stale citation metadata to be replayed without re-aggregation.
- **Atomic write pattern.** Cache persistence must write to a sibling `.tmp` file and then rename it atomically. A crash during saving must never produce a corrupt cache file.
- **Fingerprint format.** Content fingerprints are defined as the first 12 hexadecimal characters of a SHA-256 digest. This format must be preserved across any migration because it is recorded in cached artefacts and emitted into wiki evidence references.

## Quality Assurance Rules

The scoring rubric is fixed and non-negotiable:

| Score range | Meaning |
|---|---|
| 9–10 | Fully grounded, tech-agnostic, narratively coherent; no unsupported claims |
| 6–8 | Minor issues only |
| 3–5 | Substantial gaps or partial coverage |
| 0–2 | Incoherent or off-brief |

- The **minimum acceptable score** for publishing a section without revision is **7**.
- A revised body is accepted only if its follow-up critique score is **greater than or equal to** the initial score. Any revision that produces a score regression is discarded and the original body is retained. This invariant must be preserved in any reimplementation.

## Provider and API Constraints

### Shared
- The default per-call request timeout is **900 seconds**, chosen to absorb the observed latency of high-effort reasoning on large local models. Reducing this value risks aborting in-progress reasoning traces.
- Three abstract interaction modes — structured completion, text completion, and chat — constitute the **complete and exclusive** contract between the pipeline and any backend. No other methods are ever invoked; any conforming implementation must satisfy all three signatures exactly.

### Hosted-Claude Backend
- Default maximum output is **32,000 tokens** per call. Callers using the highest reasoning effort levels are expected to raise this limit and enable streaming; too low a value causes the model to exhaust the budget on reasoning before producing structured output.
- Sampling parameters (temperature, top-p, top-k) **must not** be sent to the `claude-opus-4-7` model variant; doing so causes a validation error. The provider omits them unconditionally.
- Structured output is obtained via schema-constrained decoding; if the primary parsed result is absent, the implementation falls back to parsing the raw text block as JSON before raising an error.

### Local-Model Backend
- Disabling the reasoning trace on Qwen3-family models causes them to ignore the JSON schema constraint and emit free text, breaking validation. Reasoning must never be disabled for Qwen3-style models on the structured-output path. The configuration documentation explicitly marks fully-disabled thinking as unsafe for this reason.
- Default per-call timeout is 900 seconds (same rationale as above).

### OpenAI-Compatible Backend
- Default output cap is **16,000 tokens** per call; default per-call timeout is 900 seconds.
- Reasoning-capable model families (identified by the prefixes `o<digit>` or `gpt-5`) must receive `max_completion_tokens` instead of `max_tokens`, and may receive a `reasoning_effort` value of `low`, `medium`, or `high`. Non-reasoning models must **not** receive `reasoning_effort` to avoid API validation errors.
- When the structured-output parse path returns no parsed object (due to a refusal or truncation), the implementation must fall back to validating raw JSON text against the schema, not return a null silently.

### Model Identifier Routing
- **Ollama heuristic:** a model identifier is classified as an Ollama-style identifier if it contains `:` and does not begin with the prefix `ft:` (case-insensitive). This rule must be carried forward exactly to avoid misclassifying fine-tuned models or Azure deployment IDs.
- When the hosted-Claude backend is selected but no Claude-prefixed model identifier is configured, the system falls back to a specific default model rather than forwarding the potentially invalid identifier.
- Azure/proxy deployments with non-standard deployment IDs are preserved unchanged.

## Pipeline Stage Boundaries

- **Stage 1** must operate without reading any source files; it sees only directory-level summaries and manifest contents. Source reading is exclusively Stage 2's responsibility.
- **Stage 1** must produce include and exclude path patterns in gitignore-style format relative to the repository root.
- **Stage 2 (extraction)** targets only primary wiki sections. Derivative sections are explicitly excluded and are produced in Stage 4 from the aggregate of primary findings. This boundary must be preserved through any migration.
- **Derivative section ordering.** Every derivative section must reference only known section IDs, and every upstream dependency must appear earlier in the canonical section ordering. This ordering invariant is validated at module load time; any violation raises an error.

## Interface and Directory Contracts

- The CLI entry point and its four subcommands (`init`, `walk`, `chat`, `report`) are declared as a named script in the package manifest; the command name and subcommand surface are **contractual interfaces** for users and tooling.
- The on-disk directory layout (`.wikifi/`, `config.toml`, `.gitignore`, one markdown file per section, `.notes/`, `.cache/`) is the **explicit versioned contract** with target projects and must not change in ways that break existing wikis.
- The `.notes/` and `.cache/` directories must always be excluded from version control; only section markdown files are committed. Any new required gitignore entries introduced in future versions must be backfilled into older wikis automatically on the next `init` run.
- Three exact sentinel strings mark unpopulated sections and must not be altered: `Not yet populated`, `No findings were extracted`, and `upstream sections required to derive`. The report module depends on these exact strings for gap analysis and scoring exclusion.

## Specialized Extractor Rules

- Only migration files with `.sql` or `.ddl` suffixes are routed to the SQL migration extractor; all other migration files must fall through to the general extraction path. Routing is determined by file suffix inspection, not by file-kind classification alone.
- When an API contract file is present but cannot be parsed, the system must emit an explicit warning finding directing migration teams to review the file manually. Unparseable specs are flagged, not silently skipped.
- Service-to-RPC attribution in protocol definition files must be computed by tracking brace depth (counting nested blocks), not by line proximity, to ensure correct attribution in multi-service files.
- Index definitions in schema files encode query-time performance invariants that must be preserved through migration; the extractor emits this requirement explicitly in every index finding.
- The import/reference graph must be constructed without any binary or compiled dependencies; only pattern matching and path resolution are permitted. This is a stated architectural constraint.
- Migration files are detected by matching a hardcoded list of well-known migration directory path tokens. A SQL file located in such a directory is classified as a migration rather than generic schema, preserving the distinction between forward-only schema changes and current schema state.

## Supporting claims
- All synthesised wiki content must be free of specific language, framework, or library names and must be translated into domain terms. [1][2][3]
- Whenever two source notes make incompatible claims, the output must include a contradictions entry naming each position and the note indices that support it; suppressing or merging conflicting claims is forbidden. [4][5]
- Derivative sections must draw exclusively on the aggregated bodies of the primary sections that precede them. [6][7]
- Claims must be rendered with compact footnote-style markers and a Sources footer; detected contradictions must appear under a Conflicts in source heading. [8][5]
- Note indices are 1-based and the internal resolution step subtracts 1 before indexing; this off-by-one invariant must be preserved. [9]
- Files at or above 2,000,000 bytes are unconditionally skipped and never read. [10][11]
- Files below 64 bytes of stripped content are skipped entirely. [12][11]
- Chunk window is 150,000 bytes with 8,000 bytes of overlap; chunk overlap must satisfy 0 ≤ overlap < chunk_size and chunk size must be positive. [12][13]
- Manifest files are truncated to 20,000 bytes maximum before inclusion in any prompt. [11]
- The aggregation cache key must span the file reference, summary, finding text, and the full structured sources list; omitting any field allows stale metadata to be replayed. [14]
- Cache persistence must use an atomic write pattern (write to a sibling .tmp file, then rename) to guarantee a crash never produces a corrupt cache file. [15]
- Content fingerprints are defined as the first 12 hexadecimal characters of a SHA-256 digest and this format must be preserved across any migration. [16]
- The minimum acceptable quality score for publishing a section without revision is 7; the fixed rubric maps 9–10 to fully grounded, 6–8 to minor issues, 3–5 to substantial gaps, and 0–2 to incoherent. [17]
- A revised body is accepted only if its follow-up critique score is greater than or equal to the initial score; any regression causes the original body to be retained. [18]
- The default per-call request timeout is 900 seconds. [19][20][21]
- Three abstract interaction modes — structured completion, text completion, and chat — constitute the complete and exclusive provider contract. [22]
- The hosted-Claude backend defaults to a 32,000 token output cap; sampling parameters must not be sent to the claude-opus-4-7 model variant. [23][24][25]
- Disabling the reasoning trace on Qwen3-family models causes them to ignore the JSON schema constraint and emit free text; reasoning must never be disabled for these models on the structured-output path. [19][26]
- Reasoning-capable model families must receive max_completion_tokens instead of max_tokens and may receive a reasoning_effort value; non-reasoning models must not receive reasoning_effort. [27]
- When the structured-output parse path returns no parsed object, the implementation must fall back to validating raw JSON text against the schema rather than returning null. [28][29]
- An Ollama-style model identifier is defined as a string containing ':' that does not begin with the prefix 'ft:' (case-insensitive); this rule must be carried forward exactly. [30]
- Stage 1 must operate without reading any source files and must produce include/exclude patterns in gitignore-style format relative to the repository root. [31][32]
- Stage 2 extraction targets only primary sections; derivative sections are excluded and produced in Stage 4. [33]
- Every derivative section must reference only known section IDs, and every upstream dependency must appear earlier in the canonical section ordering; violations raise an error at module load time. [7]
- The CLI entry point and its four subcommands (init, walk, chat, report) are contractual interfaces for users and tooling. [34]
- The on-disk directory layout is the explicit versioned contract with target projects and must not change in ways that break existing wikis. [35]
- .notes/ and .cache/ directories must always be excluded from version control; new required gitignore entries must be backfilled automatically on the next init run. [36]
- Three exact sentinel strings — 'Not yet populated', 'No findings were extracted', and 'upstream sections required to derive' — must be preserved as canonical markers for unpopulated sections. [37]
- Only migration files with .sql or .ddl suffixes are routed to the SQL migration extractor; all others fall through to the general extraction path. [38]
- When an API contract file cannot be parsed, the system must emit an explicit warning finding rather than silently dropping it. [39]
- Service-to-RPC attribution must be computed by tracking brace depth, not line proximity. [40]
- Index definitions encode query-time performance invariants that must be preserved through migration; the extractor emits this requirement explicitly in every index finding. [41]
- The import/reference graph must be constructed without any binary or compiled dependencies. [42]
- Gherkin outputs must use Given/When/Then syntax inside fenced gherkin code blocks; Mermaid diagrams must be valid and inside fenced mermaid code blocks. [43]

## Conflicts in source
_The walker found disagreements across files. Migration teams should resolve these before re-implementation._

- **The example environment configuration states that only the local-model provider is supported in v1, but multiple other sources document the hosted-Claude and OpenAI providers as fully implemented first-class backends with detailed API constraints.**
  - Only the local-model (Ollama) provider is supported in v1. (`.env.example:7-44`)
  - The hosted-Claude and OpenAI backends are fully implemented with detailed token caps, sampling-parameter rules, model-routing logic, and fallback behaviour. (`wikifi/config.py:122-134`, `wikifi/orchestrator.py:160-200`, `wikifi/providers/anthropic_provider.py:14-17`, `wikifi/providers/anthropic_provider.py:70-79`, `wikifi/providers/openai_provider.py:215-235`, `wikifi/providers/openai_provider.py:59-66`, `wikifi/providers/openai_provider.py:136-144`)

## Sources
1. `wikifi/aggregator.py:57-59`
2. `wikifi/critic.py:53-61`
3. `wikifi/deriver.py:37-39`
4. `wikifi/aggregator.py:61-63`
5. `wikifi/evidence.py:121-131`
6. `wikifi/deriver.py:34-50`
7. `wikifi/sections.py:148-158`
8. `wikifi/evidence.py:43-52`
9. `wikifi/aggregator.py:167-173`
10. `wikifi/config.py:59-65`
11. `wikifi/walker.py:61-79`
12. `wikifi/config.py:66-81`
13. `wikifi/extractor.py:302-308`
14. `wikifi/cache.py:243-255`
15. `wikifi/cache.py:205-209`
16. `wikifi/fingerprint.py:23-27`
17. `wikifi/critic.py:31-48`
18. `wikifi/critic.py:137-147`
19. `.env.example:7-44`
20. `wikifi/providers/ollama_provider.py:50-54`
21. `wikifi/providers/openai_provider.py:59-66`
22. `wikifi/providers/base.py:42-52`
23. `wikifi/config.py:122-134`
24. `wikifi/providers/anthropic_provider.py:14-17`
25. `wikifi/providers/anthropic_provider.py:70-79`
26. `wikifi/providers/ollama_provider.py:9-27`
27. `wikifi/providers/openai_provider.py:215-235`
28. `wikifi/providers/anthropic_provider.py:107-145`
29. `wikifi/providers/openai_provider.py:136-144`
30. `wikifi/orchestrator.py:205-215`
31. `wikifi/introspection.py:5-9`
32. `wikifi/introspection.py:50-58`
33. `wikifi/extractor.py:51-56`
34. `wikifi/cli.py:1-7`
35. `wikifi/wiki.py:1-8`
36. `wikifi/wiki.py:36-47`
37. `wikifi/report.py:103-108`
38. `wikifi/specialized/dispatch.py:28-62`
39. `wikifi/specialized/openapi.py:24-37`
40. `wikifi/specialized/protobuf.py:62-67`
41. `wikifi/specialized/sql.py:115-121`
42. `wikifi/repograph.py:22-30`
43. `wikifi/deriver.py:40-45`
44. `wikifi/orchestrator.py:160-200`
