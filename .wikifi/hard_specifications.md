# Hard Specifications

The following specifications are immutable constraints that govern pipeline behavior, data formats, interface contracts, and operational boundaries. They are not defaults or preferences; violating any one of them produces incorrect output, cache corruption, silent data loss, or runtime errors.

---

## Output Behavioral Rules

**Tech-agnosticism is unconditional.** Every pipeline stage that produces wiki prose — initial synthesis, surgical editing, critic revision, and derivative generation — must translate all observations into domain-level terms. Language names, framework names, and library names must never appear in any generated section body. This rule applies identically to the primary aggregator, the surgical editor, and the reviser.

**Contradictions must be surfaced, never resolved silently.** When two notes assert incompatible things about the same domain topic, a `contradictions[]` entry must be emitted naming each position and its supporting note indices. Merged or invented resolutions are prohibited.

**All claims must be grounded.** Synthesized content may only assert what the upstream evidence supports. When evidence is absent, the gap must be declared explicitly rather than filled with speculation. This rule applies to initial synthesis, revision passes, and derivative generation alike.

**The interactive assistant must ground every response in wiki content.** The system prompt governing the chat interface requires the assistant to cite section names when relevant and state plainly when the wiki does not cover a topic, rather than inventing detail. This behavioral constraint must be preserved in any provider migration.

---

## Quality Thresholds

The critic evaluates each section body on a 0–10 scale with four fixed bands:

| Band | Score range | Meaning |
|------|-------------|----------|
| Excellent | 9–10 | Tech-agnostic, fully grounded, no unsupported claims |
| Acceptable | 6–8 | Minor issues only |
| Deficient | 3–5 | Substantial gaps or partial coverage |
| Failing | 0–2 | Incoherent or off-brief |

The **minimum acceptable score is 7 out of 10**. Any section scoring below this threshold with unsupported claims or coverage gaps is automatically submitted for a one-shot revision. A revision that does not improve the score is discarded to prevent regressions.

---

## Cache Integrity Invariants

**Finding IDs are keyed on content, not position.** Each finding's identifier is derived from the SHA-256 digest (truncated to 12 hexadecimal characters) of the concatenation of source file path, section identifier, and finding text. A single-character change to any of these three components produces a new ID, semantically equivalent to a delete-plus-insert, and intentionally invalidates any cached prose written around the old wording.

**The notes hash must not be refreshed on metadata-only drift.** The cache key computed from a finding set must not change when only line ranges or file summaries shift without a corresponding change in finding IDs.[9] Refreshing the key under those conditions would allow freshness checks to pass while citations reference stale source positions, causing silent citation drift across pipeline runs.

**Aggregation cache keys cover source provenance in full.** The key includes the complete source list — file path, line range, and content fingerprint per referenced file. Any shift in a referenced file's content or line positions causes a cache miss and forces re-aggregation against fresh evidence.

**The asymmetric review policy is mandatory.** A cached section body produced without the critic-and-reviser loop must be rejected when the current run explicitly requests review. The inverse is permitted: a reviewed body may be reused on a non-review run because it is considered strictly higher quality.

**Content fingerprints are 12 hexadecimal characters and must remain stable.** This prefix length is a fixed constant. Existing cached results, persisted evidence citations, and dependency graph records are all keyed or cited by these 12-character strings; changing the length or algorithm breaks all previously persisted data.

---

## Citation and Attribution Format

Citations must be rendered as compact footnote-style markers (`[1]`, `[2]`, …) with an explicit "Sources" footer at the bottom of each section. When line ranges are known, they must be included in the format `path/to/file:42-87`. This rendering contract is defined at the evidence model layer and must not be altered by rendering stages.

Per-chunk line ranges reported during extraction are relative to the chunk; they must be translated to absolute file line numbers before citations are written, by computing the line offset of each chunk's start position within the full file.

---

## On-Disk Layout Contract

The `.wikifi/` directory layout is a **versioned contract** between the tool and any target project. It must remain stable across upgrades so that existing wikis remain readable without migration. The cache directory constant is defined in the layout module (not the cache module) to enforce a strict unidirectional import dependency and guarantee a single source of truth for the directory structure. These architectural constraints are documented in inline comments and must be preserved.

---

## File Ingestion Limits

| Condition | Disposition |
|-----------|-------------|
| File size > 2 000 000 bytes | Unconditionally skipped |
| Stripped text content < 64 bytes | Unconditionally skipped |
| Path matches fixed exclusion list | Always excluded, regardless of project gitignore |

The fixed exclusion list (version control directories, virtual environments, package caches, compiled artefacts, lockfiles, minified assets) is applied unconditionally. It is described as conservative and is not overridable by project-level ignore files; only an explicit include flag may recover a path from it.

**Chunking invariant:** chunk overlap must satisfy `0 ≤ overlap < chunk_size`. Violating either bound raises an immediate error. The recursive splitter must consume every byte of every file regardless of content, including minified or whitespace-free files.

---

## Pipeline Structural Invariants

**Section dependency ordering is checked at startup.** Every upstream section that a derivative declares must exist in the taxonomy and appear earlier in the ordered section list. Violations raise an error at startup, making this ordering an immutable structural invariant.

**The short-circuit predicate requires all conditions to hold simultaneously.** An empty repository (zero files observed) is explicitly excluded from short-circuiting. A first walk on a fresh wiki always executes all pipeline stages because no prior scope hash exists.

**Surgical edits must be locally bounded.** Every sentence that does not depend on a removed finding or contradict an added one must appear in the output exactly as it appeared in the cached input. The diff between input and output is required to be localized to only the changed evidence.

**Empty finding set implies maximum churn.** When the live finding set is empty and the cache contained findings, the churn ratio is defined as 1.0 (maximum), never 0.0, to prevent a remove-all-findings scenario from being misclassified as no change.

**Finding deduplication is keyed on the exact pair of (section identifier, finding text).** Identical text from chunk overlap regions is dropped on the second occurrence so that a concept straddling a chunk boundary is recorded exactly once.

---

## Provider Interface Contract

Every backend must implement exactly three interaction modes: structured-JSON completion, free-text completion, and multi-turn chat. These three methods are the full and exclusive contract; the pipeline never calls anything else on a provider. A backend that does not implement all three fails at construction time.

**Per-call timeouts must not be reduced.** The default per-call HTTP timeout across provider backends is **900 seconds**. This value is set to absorb the wall-time of high-reasoning-effort inference on large local models and must be preserved or increased, never reduced, when deploying against capable models.

**Reasoning-capable model families require separate parameter routing.** Models identified as reasoning-capable must receive their output token budget via a dedicated completion-token parameter rather than the standard token cap parameter; mixing these causes a rejected request. The `reasoning_effort` parameter must be forwarded only to reasoning-capable models when an explicit effort level is specified; for all other models it must be unconditionally stripped to prevent future validation failures.

**Sampling parameters must be omitted for specific hosted model families.** For at least one hosted model family, sending sampling parameters (temperature, top-probability, top-k) returns a 400 error. The provider must unconditionally omit these parameters for affected families.

**Local inference models with extended reasoning must not disable the reasoning trace.** For model families where disabling the reasoning trace causes the model to ignore schema constraints and emit free text, the pipeline defaults to a high-effort reasoning setting. The minimum safe setting is documented as low-effort; disabling reasoning entirely breaks downstream validation and is prohibited.

---

## Configuration Precedence and Accepted Fields

The per-project configuration file takes highest precedence over environment variables and built-in defaults. This ordering is encoded as a printed contract in every generated configuration file. Only the fields explicitly written by the initialization command are accepted from the project configuration file; unrecognized or extra fields are silently ignored to prevent a stale configuration from altering behavior the operator did not intend.

---

## Specialized Extraction Rules

**Migration file routing is suffix-gated.** Only files with specific structured-query-language suffixes that are classified as migrations are routed to the dedicated migration extractor; all other migration-tagged files must fall through to the general extraction path regardless of classification. This rule prevents silent misrouting of code-based migration logic.

**Schema definition files must never silently drop objects.** An unresolvable schema definition file must produce a finding directing reviewers to consult the file directly, so no defined entity or endpoint is lost from the migration inventory.

**Migration files must not report zero affected tables when ALTER statements are present.** The touched-table count must include tables targeted by structural modification statements even when no creation statement appears in the file, to avoid misleading migration reviewers.

**Introspection classification policy is hard-coded.** The list of path categories to skip (vendored dependencies, build output, generated files, lockfiles, test code, repository configuration, development tooling, CI/CD pipelines, and infrastructure-as-code unless encoding domain rules) and the list to include (application source implementing features, business logic, domain models, integrations, data persistence, and external touchpoints) are baked into the system prompt and not configurable at runtime.

---

## Command Identity

The tool's user-facing command name is **`wikifi`**, declared in the project's script table. This is the required invocation name for all user-facing commands and must not change across releases.

## Supporting claims
- Every pipeline stage that produces wiki prose must translate all observations into domain-level terms; language, framework, and library names must never appear in any generated section body. [1][2][3][4]
- When two notes assert incompatible things about the same domain topic, a contradictions entry must be emitted; merged or invented resolutions are prohibited. [1]
- All synthesized content may only assert what upstream evidence supports; gaps must be declared explicitly rather than filled with speculation. [2][3]
- The interactive assistant must ground every response in wiki content and state plainly when the wiki does not cover a topic, rather than inventing detail. [5]
- The critic evaluates sections on a 0–10 scale with four fixed bands: 9–10 (excellent), 6–8 (acceptable), 3–5 (deficient), 0–2 (failing). [6]
- The minimum acceptable quality score is 7 out of 10; sections below this threshold are automatically submitted for revision, and regressions are discarded. [7]
- Finding IDs are derived from the SHA-256 digest (truncated to 12 hexadecimal characters) of the source file path, section identifier, and finding text; a single-character change produces a new ID. [8]
- Aggregation cache keys include the full source list — file path, line range, and content fingerprint — so any shift in a referenced file forces re-aggregation. [10]
- A cached section body produced without the critic-and-reviser loop must be rejected when the current run explicitly requests review; the inverse is permitted. [11]
- Content fingerprints are fixed at 12 hexadecimal characters of a SHA-256 digest; this length must remain stable as existing caches, citations, and graph records are keyed by these strings. [12]
- Citations must use compact footnote-style markers with a Sources footer, and line ranges must be included in the format path/to/file:42-87 when known. [13]
- Per-chunk line ranges must be translated to absolute file line numbers before citations are written. [14]
- The on-disk directory layout is a versioned contract that must remain stable across upgrades; the cache directory constant is defined in the layout module to enforce a single source of truth and unidirectional import dependency. [15][16]
- Files exceeding 2,000,000 bytes are unconditionally skipped; files whose stripped text is under 64 bytes are unconditionally skipped. [17]
- A fixed set of path patterns is always excluded regardless of the project's own ignore file; it is not overridable by project-level configuration. [18]
- Chunk overlap must satisfy 0 ≤ overlap < chunk_size; violation raises an immediate error, and the splitter must consume every byte of every file. [19]
- Section dependency ordering is checked at startup; any violation raises an error, making the ordering an immutable structural invariant. [20]
- The short-circuit predicate requires all conditions to hold simultaneously; an empty repository is excluded from short-circuiting and a first walk always runs all stages. [21]
- Every sentence in a surgically edited section that does not depend on changed evidence must appear in the output exactly as it appeared in the cached input. [4]
- When the live finding set is empty and the cache had findings, the churn ratio is 1.0, never 0.0. [22]
- Finding deduplication is keyed on the exact pair of (section identifier, finding text); identical text from overlap regions is dropped on the second occurrence. [23]
- Every provider backend must implement exactly three interaction modes — structured-JSON completion, free-text completion, and multi-turn chat — or construction fails. [24]
- The default per-call HTTP timeout across provider backends is 900 seconds and must be preserved or increased, never reduced. [25][26][27]
- Reasoning-capable model families must receive their output token budget via a dedicated completion-token parameter; mixing parameters causes a rejected request. [28]
- The reasoning_effort parameter must be forwarded only to reasoning-capable models with an explicit effort level; for all other models it must be unconditionally stripped. [29]
- Sampling parameters must be unconditionally omitted for specific hosted model families where sending them returns a 400 error. [27]
- For local inference model families where disabling the reasoning trace causes schema constraint violations, the pipeline defaults to high-effort reasoning; disabling it entirely is prohibited. [30]
- The per-project configuration file takes highest precedence; only fields explicitly written by the initialization command are accepted; unrecognized fields are silently ignored. [31]
- Only files with structured-query-language suffixes classified as migrations are routed to the dedicated migration extractor; all other migration-tagged files fall through to the general extraction path. [32]
- An unresolvable schema definition file must produce a finding directing reviewers to consult the file directly so no entity or endpoint is silently lost. [33]
- The touched-table count in migration files must include tables targeted by structural modification statements even when no creation statement is present. [34]
- The introspection classification policy — defining which path categories to skip and which to include — is baked into the system prompt and is not configurable at runtime. [35]
- The tool's user-facing command name is 'wikifi', declared in the project's script table, and must not change across releases. [36]

## Sources
1. `wikifi/aggregator.py:56-70`
2. `wikifi/critic.py:51-58`
3. `wikifi/deriver.py:36-52`
4. `wikifi/surgical.py:46-72`
5. `wikifi/chat.py:26-34`
6. `wikifi/critic.py:32-47`
7. `wikifi/critic.py:103-136`
8. `wikifi/cache.py:418-439`
9. `wikifi/aggregator.py:161-180`
10. `wikifi/cache.py:393-410`
11. `wikifi/cache.py:197-214`
12. `wikifi/fingerprint.py:22-27`
13. `wikifi/evidence.py:16-20`
14. `wikifi/extractor.py:290-298`
15. `wikifi/wiki.py:1-8`
16. `wikifi/wiki.py:33-37`
17. `wikifi/walker.py:67-73`
18. `wikifi/walker.py:22-53`
19. `wikifi/extractor.py:380-395`
20. `wikifi/sections.py:155-166`
21. `wikifi/orchestrator.py:197-232`
22. `wikifi/surgical.py:110-121`
23. `wikifi/extractor.py:280-288`
24. `wikifi/providers/base.py:40-56`
25. `wikifi/providers/ollama_provider.py:50-57`
26. `wikifi/providers/openai_provider.py:57-62`
27. `wikifi/providers/anthropic_provider.py:97-115`
28. `wikifi/providers/openai_provider.py:218-223`
29. `wikifi/providers/openai_provider.py:196-212`
30. `wikifi/providers/ollama_provider.py:10-30`
31. `wikifi/config.py:210-228`
32. `wikifi/specialized/dispatch.py:27-31`
33. `wikifi/specialized/openapi.py:26-40`
34. `wikifi/specialized/sql.py:143-152`
35. `wikifi/introspection.py:18-40`
36. `wikifi/cli.py:3`
