"""GraphQL SDL extractor.

Pulls types, inputs, queries, mutations, and subscriptions. Maps them to
``entities`` (types/inputs) and ``capabilities`` + ``integrations``
(query/mutation/subscription roots).
"""

from __future__ import annotations

import re

from wikifi.evidence import SourceRef
from wikifi.specialized import SpecializedFinding, SpecializedResult

_TYPE_RE = re.compile(r"^\s*type\s+(\w+)\s*(?:implements\s+[^\{]+)?\{", re.MULTILINE)
_INPUT_RE = re.compile(r"^\s*input\s+(\w+)\s*\{", re.MULTILINE)
_INTERFACE_RE = re.compile(r"^\s*interface\s+(\w+)\s*\{", re.MULTILINE)
_ENUM_RE = re.compile(r"^\s*enum\s+(\w+)\s*\{", re.MULTILINE)
_SCHEMA_FIELD_RE = re.compile(r"^\s*(\w+)\s*(?:\([^)]*\))?\s*:\s*[^\n]+", re.MULTILINE)


def extract(rel_path: str, text: str) -> SpecializedResult:
    findings: list[SpecializedFinding] = []
    summary_bits: list[str] = []

    types = [(m.group(1), _line(text, m.start())) for m in _TYPE_RE.finditer(text)]
    inputs = [(m.group(1), _line(text, m.start())) for m in _INPUT_RE.finditer(text)]
    interfaces = [(m.group(1), _line(text, m.start())) for m in _INTERFACE_RE.finditer(text)]
    enums = [(m.group(1), _line(text, m.start())) for m in _ENUM_RE.finditer(text)]

    domain_types = [t for t in types if t[0] not in {"Query", "Mutation", "Subscription"}]
    root_types = [t for t in types if t[0] in {"Query", "Mutation", "Subscription"}]

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
        # declaration line and the next ``}``.
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
        summary_bits.append(", ".join(name for name, _ in root_types) + " roots")

    return SpecializedResult(
        findings=findings,
        summary=("GraphQL SDL: " + ", ".join(summary_bits)) if summary_bits else "GraphQL SDL.",
    )


def _line(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _block_after(text: str, line: int) -> str:
    """Return the text between line ``line`` and the next top-level ``}``.

    Approximate: enough to read field declarations for a GraphQL root
    type. Matches ``}`` that appears at column 0.
    """
    lines = text.splitlines()
    start = max(0, line - 1)
    out: list[str] = []
    for ln in lines[start:]:
        if ln.startswith("}"):
            break
        out.append(ln)
    return "\n".join(out)
