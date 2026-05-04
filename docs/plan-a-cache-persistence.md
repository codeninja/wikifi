# Plan A — Cache persistence + full-cache-hit short-circuit

**Status:** drafting → in progress
**Goal:** running `wikifi walk` twice with no source changes does effectively zero work — no LLM calls, no full-section rewrites, and any progress made by a partial walk survives an interruption.

## Problem

Two distinct bugs interact:

1. **Aggregation cache updates are not persisted incrementally.** [orchestrator.py](../wikifi/orchestrator.py) only persists the cache (a) per-file via `_persist` during stage 2 and (b) once at the end of `run_walk` after stage 4. If anything between stages 3 and the final save raises (Ctrl-C, OOM, deriver LLM failure that escapes the per-section catch, etc.) every aggregation cache entry computed in stage 3 is lost. Next walk reads stale `notes_hash` values, misses on every section, re-aggregates from scratch.
2. **Stage 4 has no cache layer at all.** Derivation runs unconditionally on every walk regardless of whether upstream sections changed. Even when stage 3 cache-hits 100%, derivation still calls the LLM once per derivative section.

Empirical confirmation (current repo, after the user's last walk):
- Notes JSONL mtime: `2026-05-04 11:03:33`
- Cache JSON mtime: `2026-05-04 11:03:33`
- Section .md mtimes: `11:04:59 → 11:09:35`

The .md files were written 1–6 minutes after the cache was last touched. Stage 3 ran, wrote the .md files, but the cache file stopped at end-of-stage-2.

5 of 8 sections had cached `notes_hash` ≠ live `hash_section_notes(notes)` after that walk. 3 sections matched (the cache-hit cases that didn't need an in-memory write).

## Non-goals

- Changing the granularity of aggregation. Section is still rewritten as a whole when the section's note set changes. Sub-section surgical edits are Plan B.
- Changing the introspection schema or the chunking strategy.
- Cache schema migrations beyond a version bump (existing v1 caches will be invalidated by a v2 bump if needed).

## Design

### 1. Stage 3 incremental persistence

`aggregate_all` already accepts `cache: WalkCache | None`. Add a `persist_cache: Callable[[], None] | None = None` parameter mirroring `extract_repo`'s signature. Call it after each successful `cache.record_aggregation(...)`. The orchestrator wires the same `_persist` closure that's already in scope.

Same for `derive_all` once it has a cache.

### 2. Derivation cache layer

Add `cache.derivation: dict[str, CachedDerivation]` parallel to `cache.aggregation`. Key on `section_id`. Hash the `_collect_upstream(...)` output (concatenated bodies in deterministic order) — call it `upstream_hash`. Cache stores `{upstream_hash, body, revised: bool}`.

Lookup: if upstream_hash matches, replay cached body, skip the LLM call and the critic loop. Stats: `sections_cached` parallel to aggregation's.

The critic-revised body is what gets cached — running the critic again on identical input would reproduce the same outcome at high token cost.

### 3. Cache schema bump

Bump `CACHE_VERSION` to `2`. Existing v1 caches load to empty (already the behavior in `_load_extraction` / `_load_aggregation`). Document the bump in a one-line cache-invalidation note in `wikifi/cache.py`'s docstring.

### 4. Walk early-out

After stage 2 completes, the orchestrator decides whether to skip stages 3 and 4. The check has to be strong enough to survive *partial* prior walks — a walk that crashed mid-stage-3 leaves a fully-populated extraction cache alongside stale section bodies on disk. A naive predicate ("extraction was 100% cached + scope matches") would freeze that staleness in place forever; the next walk would short-circuit with the wrong content still in section .md files.

Five conditions must all hold:

1. Caching is on.
2. We saw at least one file (an empty repo never short-circuits).
3. Every file processed in stage 2 hit either the per-file cache or a deterministic specialized extractor — no LLM call produced new findings.
4. The introspection scope hash matches the prior walk's. Scope is only `(include, exclude)` — `primary_languages` and `rationale` are descriptive and would otherwise cause spurious scope-change detections from one-token model variations.
5. Every primary section's aggregation cache and every derivative section's derivation cache is *fresh* against the live notes / upstream bodies. Helpers `aggregation_fully_cached(layout, cache)` and `derivation_fully_cached(layout, cache, *, review)` encapsulate this — they iterate sections and assert each cache entry exists with a matching hash.

When `fully_cached` is true:
- Skip stages 3 and 4 entirely.
- Section markdown on disk is from the prior walk; it's the cached content — leave it alone.
- Walk report shows "no changes detected — wiki already current" and reports the cache hit count.

When false (any new/changed/removed files, scope shift, or any cache gap from a prior interrupted walk): run stages 3 and 4 normally, but now they persist incrementally so the next walk can short-circuit cleanly.

### 5. Report surface

Extend `WalkReport` and the CLI table with:
- `aggregation.sections_cached` (already exists) — count of cache hits in stage 3
- `derivation.sections_cached` (new) — count of cache hits in stage 4
- A short-circuit line: when `fully_cached`, the table collapses to a one-line "cache full hit" summary.

## Subtasks (ordered for execution)

1. **Wire `persist_cache` through stage 3.** `aggregate_all(...persist_cache=...)`. Call it after each `record_aggregation`. Add a test that simulates mid-stage-3 interruption and asserts cache content survives.
2. **Add `derivation` to `WalkCache`.** New `CachedDerivation` dataclass. New `lookup_derivation` / `record_derivation` methods. Persistence in `save` / `_load_derivation`.
3. **Wire derivation cache through `derive_all`.** Compute `upstream_hash` per section. Hit → replay. Miss → run LLM, optional critic, then `record_derivation`. Add `sections_cached` to `DerivationStats`.
4. **Cache the introspection result.** Extend `WalkCache` with `introspection: IntrospectionResult | None`. Persist alongside the other caches. Compare on next walk.
5. **Bump `CACHE_VERSION` to 2.** Update docstring. Verify load-path returns empty on v1 files (it does).
6. **Implement early-out in `run_walk`.** Tri-state check after stage 2 returns. Skip 3 & 4 when fully cached. Update `WalkReport` shape (probably an optional `skipped: bool` per stage or just `None` for skipped stages).
7. **Update CLI table.** Show "skipped — cache full hit" when applicable.
8. **Tests.** Coverage targets:
   - Stage 3 cache persists after each section (test simulates `record_aggregation` raising on the third section; first two sections still on disk after the failure)
   - Derivation cache hit path: same upstreams → no LLM call
   - Full-cache-hit early-out: 2nd walk on identical content invokes 0 LLM calls
   - Introspection scope change defeats early-out: changing `introspection.exclude` triggers stages 3 & 4 even when extraction is 100% hit
   - Cache version bump invalidates v1 entries
9. **Update VISION.md / README.md** if cache contract is documented there (verify; don't add new doc surface speculatively).

## Risks

- **Introspection cache key drift.** Introspection itself is LLM-driven and may produce slightly different `(include, exclude)` between runs even on identical input (model nondeterminism). If we treat any difference as scope change, we never short-circuit. Mitigation: normalize the compared tuples (sorted, deduplicated, lowercase paths) before hashing. If still flaky, add an introspection cache keyed on `summarize_tree` output so introspection itself is a cache hit when the directory shape is identical.
- **Section .md drift from manual edits.** If a user hand-edited a section .md between walks, full-cache-hit will leave the hand-edit in place. That's actually correct behavior (we didn't have signal to overwrite), but worth documenting.
- **Persist-after-each-section perf.** Cache JSON is ~150KB. Atomic write per section across 8 sections = ~1.2MB written per walk. Negligible vs the LLM calls we're avoiding.

## Success criteria

- `make walk` twice, no changes between → second walk reports "fully cached" and runs no LLM calls.
- `make walk` twice, change one source file → second walk re-extracts only that file, re-aggregates only sections that file contributed to, leaves the rest cached. (Scope-of-aggregation is still whole-section; sub-section surgery is Plan B.)
- Kill `make walk` mid-stage-3 → next walk picks up from where it left off and only re-aggregates the sections that didn't complete.
- Test coverage ≥ 85% maintained.
