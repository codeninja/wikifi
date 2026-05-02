"""Evidence model + rendering tests."""

from __future__ import annotations

from wikifi.evidence import (
    Claim,
    Contradiction,
    EvidenceBundle,
    SourceRef,
    coalesce_refs,
    render_section_body,
)


def test_source_ref_render():
    assert SourceRef(file="a.py").render() == "a.py"
    assert SourceRef(file="a.py", lines=(10, 10)).render() == "a.py:10"
    assert SourceRef(file="a.py", lines=(10, 25)).render() == "a.py:10-25"


def test_claim_supported_flag():
    assert not Claim(text="x").supported()
    assert Claim(text="x", sources=[SourceRef(file="a.py")]).supported()


def test_render_section_body_includes_sources_footer():
    bundle = EvidenceBundle(
        body="The system manages orders.",
        claims=[
            Claim(text="Orders carry line items.", sources=[SourceRef(file="src/order.py", lines=(1, 30))]),
            Claim(text="Orders are immutable once placed.", sources=[SourceRef(file="src/order.py", lines=(1, 30))]),
        ],
    )
    out = render_section_body(bundle)
    assert "The system manages orders." in out
    assert "## Sources" in out
    assert "src/order.py:1-30" in out
    # Same source ref is deduped — only one numbered entry.
    assert out.count("src/order.py:1-30") == 1


def test_render_section_body_renders_contradictions():
    bundle = EvidenceBundle(
        body="Order pricing is calculated downstream.",
        contradictions=[
            Contradiction(
                summary="Whether tax is computed at order time or invoice time.",
                positions=[
                    Claim(text="Tax is computed at order time.", sources=[SourceRef(file="src/order.py")]),
                    Claim(text="Tax is computed at invoice time.", sources=[SourceRef(file="src/invoice.py")]),
                ],
            )
        ],
    )
    out = render_section_body(bundle)
    assert "Conflicts in source" in out
    assert "Tax is computed at order time" in out
    assert "Tax is computed at invoice time" in out
    assert "src/order.py" in out
    assert "src/invoice.py" in out


def test_render_section_body_omits_footer_when_no_sources():
    bundle = EvidenceBundle(body="Plain body, no claims.")
    out = render_section_body(bundle)
    assert "Plain body, no claims." in out
    assert "## Sources" not in out


def test_coalesce_refs_dedupes_by_render():
    refs = [
        SourceRef(file="a.py", lines=(1, 10)),
        SourceRef(file="a.py", lines=(1, 10)),
        SourceRef(file="b.py"),
    ]
    out = coalesce_refs(refs)
    assert len(out) == 2
    assert {r.render() for r in out} == {"a.py:1-10", "b.py"}


def test_render_section_body_inserts_claim_markers_inline():
    """Each supported claim's text in the body picks up its `[N]` marker.

    Without inline markers the reader has the source list at the bottom
    of the section but no way to tell which sentence each source backs.
    """
    bundle = EvidenceBundle(
        body="Orders carry line items. Tax is computed downstream.",
        claims=[
            Claim(text="Orders carry line items.", sources=[SourceRef(file="src/order.py", lines=(1, 30))]),
            Claim(text="Tax is computed downstream.", sources=[SourceRef(file="src/billing.py", lines=(40, 60))]),
        ],
    )
    out = render_section_body(bundle)
    # Markers are appended next to the matching sentences, in source order.
    assert "Orders carry line items.[1]" in out
    assert "Tax is computed downstream.[2]" in out
    # Sources footer still enumerates the distinct refs.
    assert "1. `src/order.py:1-30`" in out
    assert "2. `src/billing.py:40-60`" in out


def test_render_section_body_paraphrased_claims_listed_as_supporting():
    """Claims whose text doesn't appear verbatim go in a Supporting list.

    A conservative inline match avoids attaching markers to the wrong
    sentence when the aggregator paraphrased — the claim still gets a
    citation, just out-of-line.
    """
    bundle = EvidenceBundle(
        body="The system tracks orders end-to-end.",
        claims=[
            Claim(
                text="Order state transitions are persisted on every change.",
                sources=[SourceRef(file="src/order.py", lines=(80, 95))],
            ),
        ],
    )
    out = render_section_body(bundle)
    assert "## Supporting claims" in out
    assert "Order state transitions are persisted on every change." in out
    assert "[1]" in out  # marker still attached to the supporting-claim entry
    assert "1. `src/order.py:80-95`" in out
