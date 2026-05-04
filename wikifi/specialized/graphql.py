"""GraphQL SDL extractor.

Pulls types, inputs, queries, mutations, and subscriptions. Maps them to
``entities`` (types/inputs) and ``capabilities`` + ``integrations``
(query/mutation/subscription roots).

Modular GraphQL schemas often split root types across files using
``extend type Query`` / ``extend type Mutation``; we treat those exactly
like the base declaration so capabilities don't disappear when a schema
is composed from many files.
"""

from __future__ import annotations

import re

from wikifi.evidence import SourceRef
from wikifi.specialized.models import SpecializedFinding, SpecializedResult

_TYPE_RE = re.compile(r"^\s*type\s+(\w+)\s*(?:implements\s+[^\{]+)?\{", re.MULTILINE)
# ``extend type Query { ... }`` is the standard way to add fields to a
# root from a separate SDL file; treat it as a same-named root.
_EXTEND_TYPE_RE = re.compile(r"^\s*extend\s+type\s+(\w+)\s*(?:implements\s+[^\{]+)?\{", re.MULTILINE)
_INPUT_RE = re.compile(r"^\s*input\s+(\w+)\s*\{", re.MULTILINE)
_INTERFACE_RE = re.compile(r"^\s*interface\s+(\w+)\s*\{", re.MULTILINE)
_ENUM_RE = re.compile(r"^\s*enum\s+(\w+)\s*\{", re.MULTILINE)
_SCHEMA_FIELD_RE = re.compile(r"^\s*(\w+)\s*(?:\([^)]*\))?\s*:\s*[^\n]+", re.MULTILINE)


def extract(rel_path: str, text: str) -> SpecializedResult:
    findings: list[SpecializedFinding] = []
    summary_bits: list[str] = []

    # Anchor line numbers on the captured *name* offset, not the match
    # start. The leading ``^\s*`` in each pattern can consume the
    # preceding newline (``\s`` is newline-aware by default), which
    # would otherwise put the line number one above the actual
    # declaration and confuse :func:`_block_after`.
    types = [(m.group(1), _line(text, m.start(1))) for m in _TYPE_RE.finditer(text)]
    extensions = [(m.group(1), _line(text, m.start(1))) for m in _EXTEND_TYPE_RE.finditer(text)]
    inputs = [(m.group(1), _line(text, m.start(1))) for m in _INPUT_RE.finditer(text)]
    interfaces = [(m.group(1), _line(text, m.start(1))) for m in _INTERFACE_RE.finditer(text)]
    enums = [(m.group(1), _line(text, m.start(1))) for m in _ENUM_RE.finditer(text)]

    root_names = {"Query", "Mutation", "Subscription"}
    domain_types = [t for t in types if t[0] not in root_names]
    # Root declarations come from both ``type Query { ... }`` and
    # ``extend type Query { ... }`` forms.
    root_types = [t for t in types if t[0] in root_names] + [t for t in extensions if t[0] in root_names]

    if domain_types:
        summary_bits.append(f"{len(domain_types)} type(s)")
        bullets = "\n".join(f"  - **{name}**" for name, _ in domain_types[:25])
        findings.append(
            SpecializedFinding(
                section_id="entities",
                finding=("GraphQL domain types:\n" + bullets),
                sources=[
                    SourceRef(
                        file=rel_path,
                        lines=(domain_types[0][1], domain_types[-1][1]),
                    )
                ],
            )
        )

    if interfaces:
        bullets = "\n".join(f"  - **{name}**" for name, _ in interfaces)
        findings.append(
            SpecializedFinding(
                section_id="entities",
                finding=("Interfaces (shared shape contracts):\n" + bullets),
                sources=[SourceRef(file=rel_path)],
            )
        )

    if inputs:
        bullets = "\n".join(f"  - **{name}**" for name, _ in inputs[:25])
        findings.append(
            SpecializedFinding(
                section_id="entities",
                finding=("Input types (request payload shapes):\n" + bullets),
                sources=[SourceRef(file=rel_path)],
            )
        )

    if enums:
        bullets = "\n".join(f"  - **{name}**" for name, _ in enums[:15])
        findings.append(
            SpecializedFinding(
                section_id="entities",
                finding=("Enum types (closed value sets):\n" + bullets),
                sources=[SourceRef(file=rel_path)],
            )
        )

    if root_types:
        # Pull each root's fields by scanning the snippet between its
        # declaration line and the matching closing brace. Multiple
        # root declarations (the file may contain ``extend type Query``
        # blocks) get one finding each.
        for name, line in root_types:
            block = _block_after(text, line)
            fields = _SCHEMA_FIELD_RE.findall(block)
            bullets = "\n".join(f"  - `{f}`" for f in fields[:30])
            section_id = "capabilities" if name in {"Query", "Mutation"} else "integrations"
            findings.append(
                SpecializedFinding(
                    section_id=section_id,
                    finding=(f"GraphQL **{name}** root exposes:\n" + (bullets or "  - (no fields detected)")),
                    sources=[SourceRef(file=rel_path, lines=(line, line))],
                )
            )
        # Deduped name list for the summary (Query/Mutation likely repeat
        # across base + extend blocks).
        seen_root_names: list[str] = []
        for name, _ in root_types:
            if name not in seen_root_names:
                seen_root_names.append(name)
        summary_bits.append(", ".join(seen_root_names) + " roots")

    return SpecializedResult(
        findings=findings,
        summary=("GraphQL SDL: " + ", ".join(summary_bits)) if summary_bits else "GraphQL SDL.",
    )


def _line(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _block_after(text: str, line: int) -> str:
    """Return the body lines between ``line`` and the matching ``}``.

    Walks the source brace-depth-aware so an indented closing brace
    (``  }``) ends the block — many SDL formatters indent the closing
    brace, and a column-0-only check would consume every type that
    follows.
    """
    lines = text.splitlines()
    start_index = max(0, line - 1)
    out: list[str] = []
    depth = 0
    started = False
    for ln in lines[start_index:]:
        opens = ln.count("{")
        closes = ln.count("}")
        if not started:
            # The declaration line carries the opening ``{``; record it
            # but don't emit the declaration itself as a body line.
            depth += opens - closes
            started = True
            if depth <= 0:
                # ``type X {}`` on a single line — empty body.
                break
            continue
        if closes and depth - closes <= 0:
            # The line that closes the block — stop before consuming it.
            break
        depth += opens - closes
        out.append(ln)
    return "\n".join(out)
