"""Evidence model: source references, claims, and contradictions.

A premium migration wiki must let an architect ask, for any sentence in the
wiki, *"where in the source did this come from?"* — and get a precise,
verifiable answer. This module defines the small structured types that
carry that answer end-to-end:

- :class:`SourceRef` — a single ``(file, lines, fingerprint)`` pointer back
  to the codebase. Lines are optional because not every claim has a line
  range (e.g. cross-cutting findings that span a whole module).
- :class:`Claim` — one assertion in a section's narrative, with the source
  refs that justify it. The aggregator emits one or more claims per
  section; the renderer converts them into citation-bearing markdown.
- :class:`Contradiction` — two or more claims that disagree, surfaced
  rather than silently merged. Migration teams treat contradictions as
  high-priority signals: legacy systems hide tribal knowledge in them.

Citations are rendered as compact footnote-style markers (``[1]``, ``[2]``,
…) with an explicit "Sources" footer at the bottom of each section. Lines
are included when known (``path/to/file.py:42-87``).
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field


class SourceRef(BaseModel):
    """A pointer back to a single span of source code."""

    file: str = Field(description="Repo-relative path of the source file.")
    lines: tuple[int, int] | None = Field(
        default=None,
        description="Optional inclusive (start, end) line range within the file.",
    )
    fingerprint: str = Field(
        default="",
        description="Short content hash captured at extraction time. Empty when unknown.",
    )

    def render(self) -> str:
        """Render as ``path:start-end`` (or just ``path`` when lines unknown)."""
        if self.lines is None:
            return self.file
        start, end = self.lines
        if start == end:
            return f"{self.file}:{start}"
        return f"{self.file}:{start}-{end}"


class Claim(BaseModel):
    """A single assertion the aggregator places in a section, with sources."""

    text: str = Field(description="Markdown sentence(s) asserting one fact.")
    sources: list[SourceRef] = Field(
        default_factory=list,
        description="Files/lines that support this claim. Empty means unsupported.",
    )

    def supported(self) -> bool:
        return bool(self.sources)


class Contradiction(BaseModel):
    """Two or more conflicting claims about the same topic."""

    summary: str = Field(description="One-sentence description of the conflict.")
    positions: list[Claim] = Field(
        default_factory=list,
        description="Each disagreeing position, with its own sources.",
    )


class EvidenceBundle(BaseModel):
    """The aggregator's structured output for a single section."""

    body: str = Field(description="Markdown narrative for the section.")
    claims: list[Claim] = Field(default_factory=list)
    contradictions: list[Contradiction] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------


@dataclass
class _Numbered:
    index: int
    ref: SourceRef


def render_section_body(bundle: EvidenceBundle) -> str:
    """Render an EvidenceBundle into final markdown.

    The body is appended with a "Sources" footer enumerating every distinct
    source ref across claims and contradictions, plus an explicit
    "Conflicts in source" section if any contradictions were surfaced.

    When the bundle carries supported claims, each claim's footnote
    markers (``[1]``, ``[2]``…) are appended to the body — either next
    to the matching sentence (when the claim text appears verbatim in
    the body) or as a "Supporting claims" list when the body is a
    paraphrase. Without this the reader has the source list at the
    bottom but no way to tell which sentence each source backs up.
    """
    sources = _enumerate_sources(bundle)
    source_index_for: dict[str, int] = {entry.ref.render(): entry.index for entry in sources}

    parts: list[str] = []
    body_with_markers = _annotate_body_with_markers(bundle, source_index_for)
    if body_with_markers.strip():
        parts.append(body_with_markers.strip())

    unmatched_claims = [c for c in bundle.claims if c.sources and not _claim_text_in_body(c, bundle.body)]
    if unmatched_claims:
        parts.append("")
        parts.append("## Supporting claims")
        for claim in unmatched_claims:
            markers = _markers_for(claim.sources, source_index_for)
            suffix = f" {markers}" if markers else ""
            parts.append(f"- {claim.text.strip()}{suffix}")

    if bundle.contradictions:
        parts.append("")
        parts.append("## Conflicts in source")
        parts.append(
            "_The walker found disagreements across files. Migration teams "
            "should resolve these before re-implementation._"
        )
        for entry in bundle.contradictions:
            parts.append("")
            parts.append(f"- **{entry.summary.strip()}**")
            for position in entry.positions:
                refs = _format_refs(position.sources)
                parts.append(f"  - {position.text.strip()} {refs}".rstrip())

    if sources:
        parts.append("")
        parts.append("## Sources")
        for entry in sources:
            parts.append(f"{entry.index}. `{entry.ref.render()}`")

    return "\n".join(parts).strip()


def _format_refs(refs: list[SourceRef]) -> str:
    if not refs:
        return ""
    rendered = ", ".join(f"`{ref.render()}`" for ref in refs)
    return f"({rendered})"


def _enumerate_sources(bundle: EvidenceBundle) -> list[_Numbered]:
    seen: dict[str, _Numbered] = {}
    next_index = 1
    iterables: list[list[SourceRef]] = [c.sources for c in bundle.claims]
    for entry in bundle.contradictions:
        for position in entry.positions:
            iterables.append(position.sources)
    for refs in iterables:
        for ref in refs:
            key = ref.render()
            if key not in seen:
                seen[key] = _Numbered(index=next_index, ref=ref)
                next_index += 1
    return list(seen.values())


def _markers_for(refs: list[SourceRef], source_index_for: dict[str, int]) -> str:
    """Return the bracketed footnote markers for a list of source refs."""
    indices: list[int] = []
    seen: set[int] = set()
    for ref in refs:
        idx = source_index_for.get(ref.render())
        if idx is not None and idx not in seen:
            seen.add(idx)
            indices.append(idx)
    if not indices:
        return ""
    return "".join(f"[{i}]" for i in indices)


def _claim_text_in_body(claim: Claim, body: str) -> bool:
    """True when the claim's exact text appears in the body, modulo whitespace."""
    needle = " ".join(claim.text.split())
    haystack = " ".join(body.split())
    return bool(needle) and needle in haystack


def _annotate_body_with_markers(bundle: EvidenceBundle, source_index_for: dict[str, int]) -> str:
    """Append claim-level markers next to matching sentences in the body.

    Conservative substring match: only annotate when the claim's text
    appears verbatim in the body. If the aggregator paraphrased, the
    claim falls through to the "Supporting claims" list rather than
    getting attached to the wrong sentence.
    """
    if not bundle.body or not bundle.claims:
        return bundle.body
    annotated = bundle.body
    for claim in bundle.claims:
        if not claim.sources:
            continue
        # ``_claim_text_in_body`` is the gate that decides "match" vs.
        # "paraphrase"; we use the same predicate here so a claim
        # classified as inline-matchable always actually gets inlined,
        # never silently dropped between the two passes.
        if not _claim_text_in_body(claim, annotated):
            continue
        markers = _markers_for(claim.sources, source_index_for)
        if not markers:
            continue
        text = claim.text.strip()
        if text and text in annotated and markers not in annotated:
            annotated = annotated.replace(text, text + markers, 1)
    return annotated


def coalesce_refs(refs: list[SourceRef]) -> list[SourceRef]:
    """Deduplicate refs by rendered form, preserving first-seen order."""
    seen: dict[str, SourceRef] = {}
    for ref in refs:
        key = ref.render()
        if key not in seen:
            seen[key] = ref
    return list(seen.values())
