"""Protobuf IDL extractor.

Surfaces ``message`` types as entities and ``service``/``rpc`` blocks as
integration touchpoints. Proto files are pure contract: a migration team
re-implementing in a new stack can read these findings directly into
their interface design.
"""

from __future__ import annotations

import re

from wikifi.evidence import SourceRef
from wikifi.specialized import SpecializedFinding, SpecializedResult

_MESSAGE_RE = re.compile(r"^\s*message\s+(\w+)\s*\{", re.MULTILINE)
_SERVICE_RE = re.compile(r"^\s*service\s+(\w+)\s*\{", re.MULTILINE)
_RPC_RE = re.compile(
    r"^\s*rpc\s+(\w+)\s*\(\s*(stream\s+)?([\w.]+)\s*\)\s*returns\s*\(\s*(stream\s+)?([\w.]+)\s*\)",
    re.MULTILINE,
)
_ENUM_RE = re.compile(r"^\s*enum\s+(\w+)\s*\{", re.MULTILINE)
_PACKAGE_RE = re.compile(r"^\s*package\s+([\w.]+)\s*;", re.MULTILINE)


def extract(rel_path: str, text: str) -> SpecializedResult:
    findings: list[SpecializedFinding] = []
    summary_bits: list[str] = []

    package_match = _PACKAGE_RE.search(text)
    package = package_match.group(1) if package_match else ""

    messages = [(m.group(1), _line(text, m.start())) for m in _MESSAGE_RE.finditer(text)]
    enums = [(m.group(1), _line(text, m.start())) for m in _ENUM_RE.finditer(text)]
    services = [(m.group(1), _line(text, m.start())) for m in _SERVICE_RE.finditer(text)]
    rpcs = [
        (m.group(1), m.group(3), m.group(5), bool(m.group(2)), bool(m.group(4)), _line(text, m.start()))
        for m in _RPC_RE.finditer(text)
    ]

    if messages:
        summary_bits.append(f"{len(messages)} message(s)")
        bullets = "\n".join(f"  - **{name}**" for name, _ in messages[:25])
        more = f"\n  - … {len(messages) - 25} more message(s) elided." if len(messages) > 25 else ""
        findings.append(
            SpecializedFinding(
                section_id="entities",
                finding=(
                    f"Protocol entities {('in package `' + package + '`') if package else ''}:\n" + bullets + more
                ),
                sources=[SourceRef(file=rel_path, lines=(messages[0][1], messages[-1][1]))],
            )
        )

    if enums:
        bullets = "\n".join(f"  - **{name}**" for name, _ in enums[:15])
        findings.append(
            SpecializedFinding(
                section_id="entities",
                finding=("Enum types (closed value sets):\n" + bullets),
                sources=[SourceRef(file=rel_path, lines=(enums[0][1], enums[-1][1]))],
            )
        )

    for service_name, line in services:
        related = [r for r in rpcs if line <= r[5]]
        bullets = "\n".join(
            f"  - `{name}({_arrow(in_msg, in_stream)}) -> {_arrow(out_msg, out_stream)}`"
            for name, in_msg, out_msg, in_stream, out_stream, _ in related[:25]
        )
        findings.append(
            SpecializedFinding(
                section_id="integrations",
                finding=(
                    f"Service **{service_name}** exposes the following RPCs:\n"
                    + (bullets if bullets else "  - (no RPCs detected)")
                ),
                sources=[SourceRef(file=rel_path, lines=(line, line))],
            )
        )
    if services:
        summary_bits.append(f"{len(services)} service(s)")
    if rpcs:
        summary_bits.append(f"{len(rpcs)} rpc(s)")
        findings.append(
            SpecializedFinding(
                section_id="capabilities",
                finding=(
                    f"Wire protocol exposes {len(rpcs)} remote procedure(s) across {len(services) or 1} service(s)."
                ),
                sources=[SourceRef(file=rel_path)],
            )
        )

    return SpecializedResult(
        findings=findings,
        summary=("Proto file: " + ", ".join(summary_bits)) if summary_bits else "Proto file.",
    )


def _arrow(name: str, stream: bool) -> str:
    return f"stream {name}" if stream else name


def _line(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1
