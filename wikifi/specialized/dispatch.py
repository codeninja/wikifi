"""Dispatch a :class:`FileKind` to its specialized extractor.

Schema files, IDLs, OpenAPI specs, and migrations carry the system's
contracts in machine-readable form. Running them through the same prose
LLM extractor as application code is wasteful and lossy: the structure
is already there, the extractor just has to read it.

Selection respects the file's *path* — not just its kind — so a Python
Alembic/Django migration is not silently routed through the SQL parser.
The classifier upstream (``wikifi.repograph.classify``) tags every file
under a migrations directory as :attr:`FileKind.MIGRATION`; this layer
narrows that to the SQL-shaped subset (``.sql`` / ``.ddl``) and returns
``None`` for the rest, letting them fall through to the LLM path.
"""

from __future__ import annotations

import logging
from pathlib import PurePosixPath

from wikifi.repograph import FileKind
from wikifi.specialized.models import ExtractorFn

log = logging.getLogger("wikifi.specialized")


# Suffixes that the SQL extractor can actually read. Anything else
# tagged :attr:`FileKind.MIGRATION` (e.g. an Alembic ``.py`` script,
# a Django ``0001_initial.py``, a Knex ``.js`` migration) keeps its
# logic in code, not DDL — those belong on the LLM extraction path.
_SQL_MIGRATION_SUFFIXES: frozenset[str] = frozenset({".sql", ".ddl"})


def select(kind: FileKind, *, rel_path: str | None = None) -> ExtractorFn | None:
    """Return the specialized extractor for a file, or ``None``.

    ``rel_path`` is required for :attr:`FileKind.MIGRATION` because the
    classifier marks any file inside a migrations directory as a
    migration, including non-SQL ones. Without the path, we can't tell
    a SQL migration from an Alembic Python script.
    """
    # Imports are lazy so this module stays cheap to load and so the
    # extractors can import freely from ``wikifi.specialized.models``
    # without a circular ``__init__`` dependency.
    from wikifi.specialized import graphql, openapi, protobuf, sql

    if kind is FileKind.SQL:
        return sql.extract
    if kind is FileKind.OPENAPI:
        return openapi.extract
    if kind is FileKind.PROTOBUF:
        return protobuf.extract
    if kind is FileKind.GRAPHQL:
        return graphql.extract
    if kind is FileKind.MIGRATION:
        if rel_path is None:
            return None
        suffix = PurePosixPath(rel_path).suffix.lower()
        if suffix in _SQL_MIGRATION_SUFFIXES:
            return sql.extract_migration
        return None
    return None
