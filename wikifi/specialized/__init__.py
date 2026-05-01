"""Type-aware extractors for high-signal source artifacts.

Schema files, IDLs, OpenAPI specs, and migrations carry the system's
contracts in machine-readable form. Running them through the same prose
LLM extractor as application code is wasteful and lossy: the structure
is already there, the extractor just has to read it.

Each module in this package implements one or more parsers that consume
the file's text and emit a list of structured findings, in the same
``{section_id, finding, sources}`` shape the LLM extractor produces.
That keeps the downstream aggregator interface unchanged — the
specialized path is a drop-in replacement for the LLM call when the
file kind is recognized.

Extractor selection lives in :func:`select` below.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field

from wikifi.evidence import SourceRef
from wikifi.repograph import FileKind

log = logging.getLogger("wikifi.specialized")


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


def select(kind: FileKind) -> ExtractorFn | None:
    """Return the specialized extractor for a file kind, or ``None``."""
    from wikifi.specialized import graphql, openapi, protobuf, sql

    table: dict[FileKind, ExtractorFn] = {
        FileKind.SQL: sql.extract,
        FileKind.MIGRATION: sql.extract_migration,
        FileKind.OPENAPI: openapi.extract,
        FileKind.PROTOBUF: protobuf.extract,
        FileKind.GRAPHQL: graphql.extract,
    }
    return table.get(kind)
