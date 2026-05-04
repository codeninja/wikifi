"""Result types emitted by specialized extractors.

Specialized extractors short-circuit the LLM on schema/IDL files —
their output flows into the same notes store the LLM extractor writes
to, so the dispatch contract is just ``(rel_path, text) -> SpecializedResult``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from wikifi.evidence import SourceRef


@dataclass
class SpecializedFinding:
    section_id: str
    finding: str
    sources: list[SourceRef] = field(default_factory=list)


@dataclass
class SpecializedResult:
    findings: list[SpecializedFinding] = field(default_factory=list)
    summary: str = ""


# Each extractor takes ``(rel_path, text)`` and returns a SpecializedResult.
ExtractorFn = Callable[[str, str], SpecializedResult]
