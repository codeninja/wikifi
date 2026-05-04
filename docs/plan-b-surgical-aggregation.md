# Plan B — Surgical aggregation for partial-change walks

**Status:** drafting (depends on Plan A landing first)
**Goal:** when a re-walk produces a *delta* of findings (some files changed, most didn't) the section bodies are *edited* in place around the delta — preserving stable prose, citation numbering, and any organizing structure — instead of being regenerated from scratch.

## Why this matters

Today, when even one file changes inside a section's contributing set, the whole section is re-aggregated by the LLM from the full notes payload. Two problems with that:

1. **Detail loss.** A from-scratch synthesis on a slightly different note set can drop or rephrase observations that were in the prior body — there's no anchor to "the body that already worked." The user's exact concern: *"potentially omitting or changing key details."*
2. **Wasted tokens.** The model re-derives identical paragraphs every time. For a section with 50 notes where 1 changed, it re-narrates 49 unchanged claims.

Surgical aggregation reframes the prompt: "here's the section as it stands; here's what's new/changed/gone in the underlying findings; integrate the delta and return the revised body."

## Non-goals

- Citation rewriting at character precision. Surgical edits will refresh the citation footer and re-number, but inline `[N]` markers in the prose are part of the body and re-flow with the edit.
- Streaming partial edits. The model returns one revised body per section, atomically.
- Sub-paragraph diffs. Granularity is "edit the section body" — the *prompt* is finer-grained, but the *output* is still a whole body.

## Design

### Finding identity

Each finding needs a stable id that survives across walks so we can detect added / removed / modified between cached and live sets.

Composition:

```
finding_id = sha256(file_path + "::" + section_id + "::" + finding_text)[:16]
```

Deterministic from content. Two walks producing the same `finding_text` for the same `(file, section)` get the same id. A reword of the finding gets a new id (counts as removed-and-added — equivalent to "modified" semantically).

Stored on each cached extraction finding so the aggregator doesn't have to recompute on replay.

### Cache shape (v3 bump)

```
CachedSection {
    notes_hash: str           # whole-payload hash, kept for the "no change at all" fast path
    body: str
    claims: list[dict]
    contradictions: list[dict]
    finding_ids: list[str]    # NEW — the set of finding ids that this body was synthesized from
}
```

### Diff classification per section

```
prior_ids = set(cache.finding_ids)
live_ids  = {finding_id(n) for n in live_notes}

added    = live_ids - prior_ids
removed  = prior_ids - live_ids
unchanged = live_ids & prior_ids

if not (added or removed):
    # Plan A handles this — full cache hit
    reuse cached body

elif (len(added) + len(removed)) > REWRITE_THRESHOLD * len(live_ids):
    # Too much churn — surgical edit risks degrading quality. Full re-aggregation.
    fall back to current aggregate_all path

else:
    # Surgical edit path
    surgical_edit(section, cached.body, added_notes, removed_finding_ids, unchanged_count)
```

`REWRITE_THRESHOLD` proposed default: `0.3` (30%). Configurable via `Settings.surgical_edit_threshold`.

### Surgical edit prompt

Inputs to the LLM:

1. The section brief (same as today).
2. **The current section body**, fenced.
3. **Added findings**: list of new notes with their `file`, `summary`, `finding`, `sources`. Indexed `[A1, A2, …]`.
4. **Removed findings** (id + the cached `finding_text`): "these claims are no longer supported by the source — revise or drop any prose that depended on them." Indexed `[R1, R2, …]`.
5. The set of unchanged findings is *not* sent in full — only a count and the existing body, which is the model's evidence that they're already represented. (This is the token saving.)

Schema returned:

```python
class SurgicalEdit(BaseModel):
    body: str
    new_claims: list[AggregatedClaim]      # claims that were added or re-anchored to added findings
    removed_claim_indices: list[int]       # 1-based indices into the cached `claims` list, deleted
    contradictions: list[AggregatedContradiction]  # full new set; replaces cached
```

Citations for unchanged claims survive by id (we re-resolve the cached `claims` list against the new `notes` payload and drop any that referenced removed sources). Citations for new claims come in via `new_claims`.

### Citation re-anchoring

After surgical edit:

```
final_claims = (cached.claims minus removed_claim_indices) + new_claims
```

Each claim's `source_indices` was 1-based against the *original* note list. `new_claims` indices are against the *added* sub-list (`A1`, `A2`, …). Translate both into the live notes list before resolving to `SourceRef`s, then renumber footnotes consistently in the rendered body.

The renderer (`evidence.render_section_body`) gets refactored to accept the merged claim list and re-do its existing footnote pass — no new rendering primitives.

### Stability test

A surgical edit must:

- Preserve every paragraph that doesn't reference an added or removed finding, **byte-for-byte** (modulo footnote renumbering).
- Drop or revise paragraphs that reference removed findings.
- Integrate added findings somewhere, not as an unstructured appendix.

The test is mechanical: run a surgical edit with `added=[X]`, `removed=[]`, then string-diff the input body against the output — only paragraphs touching X should differ.

This is the assertion that protects against the "model rewrites everything anyway" failure mode. It will fail until the prompt is tight enough — that's the signal to keep iterating on the prompt.

## Subtasks (ordered)

1. **Plan A merged** (prerequisite — surgical edits build on a working cache).
2. **Add stable `finding_id`** to extractor outputs and cache.
3. **Bump cache to v3.** Add `finding_ids` to `CachedSection`. Persist + load.
4. **Diff helper.** `classify_section_change(cached, live) -> ("unchanged" | "surgical" | "rewrite")`.
5. **Surgical aggregation prompt + schema.** New `SurgicalEdit` Pydantic model, new system prompt focused on minimal edits.
6. **Aggregator dispatch.** Decision tree that routes each section to one of three paths.
7. **Citation re-anchor.** Merge cached claims with `new_claims`, renumber, re-render.
8. **Stability tests.**
   - Single added finding → only paragraphs touching that finding differ.
   - Single removed finding → only paragraphs that cited it are revised.
   - Mixed delta within threshold → surgical path taken.
   - Delta > threshold → falls back to rewrite path.
   - Citations resolve correctly after edit.
9. **Configuration.** `Settings.surgical_edit_threshold` (default 0.3). `--no-surgical` CLI flag for opt-out.
10. **Walk report surface.** Show counts: `sections_unchanged / sections_edited / sections_rewritten`.
11. **Update VISION.md**: surgical edits are now part of how wikifi handles re-walks. Document the contract in one paragraph.

## Risks and open questions

- **The model may not actually preserve unchanged paragraphs.** This is the core risk. Mitigations:
  - Tight prompt that quotes the cached body inside fenced markdown and instructs *"return the body verbatim except for the smallest change that integrates the delta."*
  - Stability test gates merges. If the test flakes on real data, we lower the threshold (less surgical, more rewrite).
  - A post-edit critic: diff the edited body against the cached body, and if the diff is larger than a heuristic ratio of the delta size, fall back to a full rewrite.
- **Citation numbering churn.** Footnotes will renumber when claims are added or removed. That's expected — they're auto-generated. Inline `[N]` markers in the prose will need to be updated by the model as part of the edit.
- **Diagrams and Gherkin.** Surgical edits to Mermaid blocks and Gherkin scenarios are higher-risk than prose edits. Initial approach: derivative sections (personas, user_stories, diagrams) stay on full-rewrite path until we have evidence that surgical edits are safe for structured outputs. Plan B applies to primary sections only.
- **Threshold tuning.** 0.3 is a guess. Real-world: monitor the ratio in production walks and tune. Worth logging the chosen path and delta size so we can analyze later.
- **Backwards compatibility.** v3 cache bump invalidates v1 and v2 caches. First walk after upgrade is a full re-aggregation. Acceptable — same as any cache bump.

## Success criteria

- A walk where one source file changed, contributing to 3 sections, produces section bodies where unchanged paragraphs are byte-identical to the prior walk's output (modulo footnote renumbering).
- Token cost per re-walk on a partially-changed repo drops materially (target: 50%+ reduction vs full re-aggregation, measured on the wikifi self-walk).
- The user's stated concern — "potentially omitting or changing key details" — is verifiably absent: the stability test fails on any drift in unchanged regions.
- Test coverage ≥ 85%.
- No regression on Plan A's success criteria (full-cache-hit walk still does zero work).

## Sequencing relative to Plan A

Plan A and Plan B share the cache layer. Plan A introduces incremental persistence and the derivation cache; Plan B builds finding-id tracking and the surgical edit path on top. Building B without A's incremental persistence would be unsafe — a partial walk could persist a surgically-edited body without the matching `finding_ids`, producing cache state that doesn't round-trip.

Order: A → merge → B starts from main with A's foundation in place.
