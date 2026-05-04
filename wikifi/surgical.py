"""Surgical aggregation — edit a cached section body around a small finding delta.

Plan A's aggregation cache is whole-section: any change to any contributing
file invalidates the section's body and triggers a from-scratch re-synthesis.
That works, but on a partially changed repo it (a) wastes tokens
re-narrating identical claims and (b) risks losing established prose that
the prior walk got right because the model has no anchor to it.

Plan B inserts a third path between "cache hit" and "full rewrite":

- **unchanged** — every cached finding id is present in the live notes and
  vice versa. Hand the cached body back; just refresh the cache key (the
  ``notes_hash`` may have shifted due to a source line move that didn't
  touch the finding text itself).
- **surgical** — the symmetric difference between cached and live finding
  ids is below ``surgical_edit_threshold``. Send the cached body plus a
  delta of *added* and *removed* findings to the LLM and ask it to edit
  in place, preserving every paragraph that doesn't depend on the delta.
- **rewrite** — too much churn. Fall back to Plan A's whole-section
  re-aggregation path; surgical edits beyond the threshold tend to hide
  latent inconsistencies the model would otherwise resolve cleanly.

The surgical path is the one that protects the user's stated concern —
"potentially omitting or changing key details" — by making the cached
body the explicit anchor the LLM has to edit around rather than
re-derive from scratch.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

from wikifi.cache import CachedSection
from wikifi.evidence import Claim, Contradiction, EvidenceBundle, SourceRef, coalesce_refs
from wikifi.providers.base import LLMProvider
from wikifi.sections import Section

log = logging.getLogger("wikifi.surgical")


SURGICAL_SYSTEM_PROMPT = """\
You are wikifi's section editor. You receive an existing markdown body for one \
section of a technology-agnostic wiki, plus a small set of *added* findings \
(new evidence) and *removed* findings (evidence no longer supported by the \
source). Edit the body to integrate the added findings and revise around the \
removed ones.

Rules:
- PRESERVE unchanged paragraphs verbatim. Every sentence that does not \
  depend on a removed finding or directly contradict an added one MUST \
  appear in the output exactly as it was in the input. The reader should \
  be able to diff your output against the input and see only the localized \
  edit.
- When integrating an added finding, add it as a single sentence or bullet \
  within the most topically relevant existing paragraph. Only create a new \
  paragraph if no existing one is on-topic.
- When a removed finding underpinned a sentence, revise or delete that \
  sentence. Do not leave a claim in the body that no longer has source \
  support.
- Tech-agnostic. Never name languages, frameworks, or libraries — \
  translate every observation into domain terms.
- Use `new_claims` to declare each claim newly introduced in the edited \
  body. Index its `source_indices` against the *added findings* list \
  (1-based; the user prompt tags them [A1], [A2], …).
- Use `removed_claim_indices` (1-based against the *cached claims* list \
  the user prompt shows as [C1], [C2], …) to identify any cached claim \
  whose supporting evidence is gone. Those entries will be dropped from \
  the rendered citation footer.
- Use `contradictions` for the FULL post-edit set (not a delta). It \
  replaces the cached contradictions verbatim, so include any contradictions \
  that survived the edit too.
- Output the body only (no top-level heading); the writer adds the title.
"""


class SurgicalClaim(BaseModel):
    """One claim added by the surgical edit, indexed against the *added* notes."""

    text: str = Field(description="One assertion newly introduced in the edited body.")
    source_indices: list[int] = Field(
        default_factory=list,
        description=(
            "1-based indices into the ADDED findings list (the [A1], [A2] tags). "
            "Do not reference cached claims here — use removed_claim_indices for those."
        ),
    )


class SurgicalContradiction(BaseModel):
    summary: str = Field(description="One-sentence description of the disagreement.")
    positions: list[SurgicalClaim] = Field(
        default_factory=list,
        description="Each disagreeing position, with its own added-findings indices.",
    )


class SurgicalEdit(BaseModel):
    """The model's structured output for one surgical aggregation pass."""

    body: str = Field(description="Edited markdown body. Preserves unchanged paragraphs verbatim.")
    new_claims: list[SurgicalClaim] = Field(
        default_factory=list,
        description="Claims newly introduced by the edit; indexed against added findings.",
    )
    removed_claim_indices: list[int] = Field(
        default_factory=list,
        description=(
            "1-based indices into the cached claims list ([C1], [C2] in the prompt) for "
            "claims whose supporting evidence is gone — drop them from the citation footer."
        ),
    )
    contradictions: list[SurgicalContradiction] = Field(
        default_factory=list,
        description="Full post-edit contradictions list; replaces the cached entries.",
    )


@dataclass(frozen=True)
class SectionChange:
    """Per-section diff between cached and live finding sets."""

    decision: Literal["unchanged", "surgical", "rewrite"]
    added_indices: list[int]
    """1-based positions in the live notes whose finding_id is not in the cache."""
    removed_ids: list[str]
    """Cached finding ids no longer present in the live notes."""
    unchanged_count: int
    total_live: int

    @property
    def churn_ratio(self) -> float:
        # Mirror :func:`classify_section_change`'s guard: when the live
        # finding set is empty but the cache had findings (i.e.
        # ``removed_ids`` is non-empty), every cached finding is gone —
        # the maximum possible churn. Returning 0.0 there would be
        # misleading and could let downstream callers treat a
        # remove-everything diff as "no change."
        if self.total_live == 0:
            return 1.0 if self.removed_ids else 0.0
        return (len(self.added_indices) + len(self.removed_ids)) / self.total_live


def classify_section_change(
    *,
    cached: CachedSection | None,
    live_finding_ids: list[str],
    surgical_threshold: float,
) -> SectionChange:
    """Choose between cache-hit-rerender, surgical edit, and full rewrite.

    - No cached entry, or a cached entry with no ``finding_ids`` (legacy
      v2 caches), routes to ``rewrite`` — without a prior finding-set
      we can't compute a meaningful delta.
    - Symmetric difference empty → ``unchanged`` (the caller refreshes
      the notes_hash and re-renders the cached body, no LLM call).
    - Otherwise compute churn ratio. ≤ threshold → ``surgical``;
      > threshold → ``rewrite``.
    """
    if cached is None or not cached.finding_ids:
        return SectionChange(
            decision="rewrite",
            added_indices=list(range(1, len(live_finding_ids) + 1)),
            removed_ids=[],
            unchanged_count=0,
            total_live=len(live_finding_ids),
        )

    # Empty-string ids surface from malformed or legacy notes (see
    # :func:`wikifi.cache.note_finding_ids`). They have no meaningful
    # identity, so any section that contains one — cached or live —
    # forces a full rewrite rather than risking a "two empties look
    # unchanged" set collision in the comparisons below.
    if "" in cached.finding_ids or "" in live_finding_ids:
        return SectionChange(
            decision="rewrite",
            added_indices=list(range(1, len(live_finding_ids) + 1)),
            removed_ids=list(cached.finding_ids),
            unchanged_count=0,
            total_live=len(live_finding_ids),
        )

    cached_set = set(cached.finding_ids)
    live_set = set(live_finding_ids)
    added_indices = [i + 1 for i, fid in enumerate(live_finding_ids) if fid not in cached_set]
    removed_ids = [fid for fid in cached.finding_ids if fid not in live_set]
    unchanged_count = len(cached_set & live_set)
    total_live = len(live_finding_ids)

    if not added_indices and not removed_ids:
        return SectionChange(
            decision="unchanged",
            added_indices=[],
            removed_ids=[],
            unchanged_count=unchanged_count,
            total_live=total_live,
        )

    # ``max(total_live, 1)`` guards the "removed everything" edge case
    # where total_live is 0 — the entire cached set is gone, which is a
    # rewrite by any reasonable threshold.
    churn = (len(added_indices) + len(removed_ids)) / max(total_live, 1)
    decision: Literal["unchanged", "surgical", "rewrite"] = "surgical" if churn <= surgical_threshold else "rewrite"
    return SectionChange(
        decision=decision,
        added_indices=added_indices,
        removed_ids=removed_ids,
        unchanged_count=unchanged_count,
        total_live=total_live,
    )


def surgical_aggregate(
    *,
    section: Section,
    cached: CachedSection,
    live_notes: list[dict],
    change: SectionChange,
    provider: LLMProvider,
) -> EvidenceBundle:
    """Send the cached body + finding delta to the LLM and merge the edit.

    Returns the bundle the renderer takes (body + claims + contradictions).
    Citation re-anchoring is done here:
    - Cached claims survive verbatim, except those listed in
      ``removed_claim_indices`` are dropped.
    - ``new_claims`` indices are resolved against the *added notes only*
      and converted to :class:`SourceRef`.
    - Contradictions are fully replaced from the model output.
    """
    added_notes = [live_notes[i - 1] for i in change.added_indices if 1 <= i <= len(live_notes)]
    removed_notes = _removed_finding_descriptors(change.removed_ids)
    user_prompt = _render_surgical_user_prompt(
        section=section,
        cached_body=cached.body,
        added_notes=added_notes,
        removed_notes=removed_notes,
        cached_claims=cached.claims,
    )
    edit = provider.complete_json(
        system=SURGICAL_SYSTEM_PROMPT,
        user=user_prompt,
        schema=SurgicalEdit,
    )
    return _merge_edit_with_cached(
        edit=edit,
        cached=cached,
        added_notes=added_notes,
    )


def _merge_edit_with_cached(
    *,
    edit: SurgicalEdit,
    cached: CachedSection,
    added_notes: list[dict],
) -> EvidenceBundle:
    """Re-anchor citations: keep cached claims minus removed, add new claims."""
    survivors = _drop_removed_claims(cached.claims, edit.removed_claim_indices)
    surviving_claims = [
        Claim(
            text=c.get("text", ""),
            sources=[SourceRef.model_validate(s) for s in c.get("sources", [])],
        )
        for c in survivors
    ]

    added_refs = _refs_per_added_note(added_notes)
    new_claims = [
        Claim(
            text=nc.text,
            sources=_resolve_added_indices(nc.source_indices, added_refs),
        )
        for nc in edit.new_claims
    ]

    contradictions = [
        Contradiction(
            summary=c.summary,
            positions=[
                Claim(text=p.text, sources=_resolve_added_indices(p.source_indices, added_refs)) for p in c.positions
            ],
        )
        for c in edit.contradictions
    ]

    return EvidenceBundle(
        body=edit.body,
        claims=surviving_claims + new_claims,
        contradictions=contradictions,
    )


def _drop_removed_claims(cached_claims: list[dict], removed_indices: list[int]) -> list[dict]:
    """Return the cached claims whose 1-based index is NOT in ``removed_indices``."""
    drop = {i for i in removed_indices if 1 <= i <= len(cached_claims)}
    return [c for i, c in enumerate(cached_claims, start=1) if i not in drop]


def _refs_per_added_note(added_notes: list[dict]) -> list[list[SourceRef]]:
    """Map each added note to its source refs (mirrors ``aggregator._refs_per_note``)."""
    out: list[list[SourceRef]] = []
    for note in added_notes:
        sources = note.get("sources")
        if isinstance(sources, list) and sources:
            try:
                out.append([SourceRef.model_validate(s) for s in sources])
                continue
            except Exception:  # malformed sources — fall back to file
                pass
        file = note.get("file")
        if file:
            out.append([SourceRef(file=str(file))])
        else:
            out.append([])
    return out


def _resolve_added_indices(indices: list[int], added_refs: list[list[SourceRef]]) -> list[SourceRef]:
    refs: list[SourceRef] = []
    for idx in indices:
        real = idx - 1
        if 0 <= real < len(added_refs):
            refs.extend(added_refs[real])
    return coalesce_refs(refs)


def _removed_finding_descriptors(removed_ids: list[str]) -> list[dict]:
    """Build the ``removed_notes`` payload the surgical prompt expects.

    The cache stores stable ``finding_ids`` aligned with the prior
    walk's notes order, but it does *not* persist the original note
    bodies (file path or finding text). All we can give the model for
    a removed finding is the opaque id; the prompt then asks the model
    to find any sentence in the cached body that cites this id-shaped
    handle and revise around it.

    Restoring richer context (file path, finding text) would require
    persisting the underlying notes alongside ``finding_ids`` in the
    cache schema — a separate change, not addressed here.
    """
    return [{"finding_id": fid} for fid in removed_ids]


def _render_surgical_user_prompt(
    *,
    section: Section,
    cached_body: str,
    added_notes: list[dict],
    removed_notes: list[dict],
    cached_claims: list[dict],
) -> str:
    lines: list[str] = []
    lines.append(f"## Section: {section.title} (id: {section.id})")
    lines.append("")
    lines.append("### Brief")
    lines.append(section.description)
    lines.append("")
    lines.append("### Current section body (preserve unchanged paragraphs verbatim)")
    lines.append("```markdown")
    lines.append(cached_body.strip())
    lines.append("```")
    lines.append("")

    lines.append(f"### Added findings ({len(added_notes)}) — index against new_claims.source_indices")
    if not added_notes:
        lines.append("_(none)_")
    for idx, note in enumerate(added_notes, start=1):
        file_ref = note.get("file", "?")
        finding = note.get("finding", "")
        summary = note.get("summary", "")
        role = f" (file role: {summary})" if summary else ""
        lines.append(f"[A{idx}] {file_ref}{role}: {finding}")
    lines.append("")

    lines.append(
        f"### Removed findings ({len(removed_notes)}) — these no longer have source support; "
        "revise or drop the prose that depended on them"
    )
    if not removed_notes:
        lines.append("_(none)_")
    for idx, note in enumerate(removed_notes, start=1):
        file_ref = note.get("file", note.get("finding_id", "?"))
        finding = note.get("finding", "")
        if finding:
            lines.append(f"[R{idx}] {file_ref}: {finding}")
        else:
            lines.append(f"[R{idx}] (cached finding id {file_ref})")
    lines.append("")

    lines.append(
        f"### Cached claims ({len(cached_claims)}) — index into removed_claim_indices "
        "to drop any whose evidence is gone"
    )
    if not cached_claims:
        lines.append("_(none)_")
    for idx, claim in enumerate(cached_claims, start=1):
        text = claim.get("text", "")
        lines.append(f"[C{idx}] {text}")
    lines.append("")

    lines.append(
        "Edit the body to integrate the added findings and revise around the removed ones. "
        "Preserve unchanged paragraphs verbatim. Return SurgicalEdit per the schema."
    )
    return "\n".join(lines)


__all__ = [
    "SURGICAL_SYSTEM_PROMPT",
    "SectionChange",
    "SurgicalClaim",
    "SurgicalContradiction",
    "SurgicalEdit",
    "classify_section_change",
    "surgical_aggregate",
]
