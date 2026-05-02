"""SQL DDL + migration extractor.

Pulls table definitions, columns, primary/foreign keys, indexes, and
constraints. Each table becomes an ``entities`` finding; foreign keys
become ``integrations``-style relationships if they cross obvious
service boundaries (heuristic), and ``cross_cutting`` for storage
invariants like ``UNIQUE`` and ``NOT NULL`` constraints.

Migration files (Alembic/Knex/Flyway/etc.) are extracted with the same
parser and additionally tagged in the summary so the migration team can
spot forward-only schema changes vs. baseline DDL.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from wikifi.evidence import SourceRef
from wikifi.specialized.models import SpecializedFinding, SpecializedResult

# Line-number tracking is precise to "the line containing the matched
# keyword" — that's specific enough for citations and avoids the cost
# of a full SQL parser. Migrations frequently mix dialects; we tolerate
# anything that loosely matches the keyword grammar.
_CREATE_TABLE_RE = re.compile(
    r"create\s+(?:or\s+replace\s+)?(?:temporary\s+)?table\s+(?:if\s+not\s+exists\s+)?"
    r"([\"`\[\]\w.]+)\s*\((.*?)\)\s*;",
    re.IGNORECASE | re.DOTALL,
)
_ALTER_TABLE_RE = re.compile(
    r"alter\s+table\s+([\"`\[\]\w.]+)\s+(.*?);",
    re.IGNORECASE | re.DOTALL,
)
_FK_RE = re.compile(
    r"foreign\s+key\s*\(([^)]+)\)\s*references\s+([\"`\[\]\w.]+)\s*\(([^)]+)\)",
    re.IGNORECASE,
)
_REF_INLINE_RE = re.compile(r"references\s+([\"`\[\]\w.]+)\s*\(([^)]+)\)", re.IGNORECASE)
_UNIQUE_RE = re.compile(r"\bunique\b", re.IGNORECASE)
_NOT_NULL_RE = re.compile(r"\bnot\s+null\b", re.IGNORECASE)
_INDEX_RE = re.compile(
    r"create\s+(?:unique\s+)?index\s+(?:if\s+not\s+exists\s+)?([\"`\[\]\w.]+)\s+on\s+([\"`\[\]\w.]+)",
    re.IGNORECASE,
)


@dataclass
class _TableHit:
    name: str
    line: int
    body: str
    columns: list[str] = field(default_factory=list)
    fks: list[tuple[str, str, str]] = field(default_factory=list)


def extract(rel_path: str, text: str) -> SpecializedResult:
    return _extract(rel_path, text, migration=False)


def extract_migration(rel_path: str, text: str) -> SpecializedResult:
    return _extract(rel_path, text, migration=True)


def _extract(rel_path: str, text: str, *, migration: bool) -> SpecializedResult:
    findings: list[SpecializedFinding] = []
    tables: list[_TableHit] = []
    altered_tables: set[str] = set()

    for match in _CREATE_TABLE_RE.finditer(text):
        name = _strip_ident(match.group(1))
        body = match.group(2)
        line = _line_of(text, match.start())
        hit = _TableHit(name=name, line=line, body=body)
        _populate_columns(hit)
        tables.append(hit)

    for hit in tables:
        bullet_lines = ", ".join(hit.columns) if hit.columns else "(no columns parsed)"
        prefix = "Migration adds" if migration else "Persists"
        findings.append(
            SpecializedFinding(
                section_id="entities",
                finding=(f"{prefix} the **{hit.name}** entity. Columns: {bullet_lines}."),
                sources=[SourceRef(file=rel_path, lines=(hit.line, hit.line))],
            )
        )

        for column, ref_table, ref_column in hit.fks:
            findings.append(
                SpecializedFinding(
                    section_id="integrations",
                    finding=(
                        f"`{hit.name}.{column}` references "
                        f"`{ref_table}.{ref_column}` — a hard relational link "
                        "between these entities."
                    ),
                    sources=[SourceRef(file=rel_path, lines=(hit.line, hit.line))],
                )
            )

        constraints = _parse_constraints(hit.body)
        if constraints:
            findings.append(
                SpecializedFinding(
                    section_id="cross_cutting",
                    finding=(f"Storage invariants on **{hit.name}**: {constraints}."),
                    sources=[SourceRef(file=rel_path, lines=(hit.line, hit.line))],
                )
            )

    for match in _ALTER_TABLE_RE.finditer(text):
        line = _line_of(text, match.start())
        target = _strip_ident(match.group(1))
        action = match.group(2).strip()
        altered_tables.add(target)
        prefix = "Migration alters" if migration else "Alters"
        findings.append(
            SpecializedFinding(
                section_id="entities",
                finding=(f"{prefix} entity **{target}**: {_summarize_alter(action)}."),
                sources=[SourceRef(file=rel_path, lines=(line, line))],
            )
        )

    for match in _INDEX_RE.finditer(text):
        line = _line_of(text, match.start())
        idx = _strip_ident(match.group(1))
        target = _strip_ident(match.group(2))
        findings.append(
            SpecializedFinding(
                section_id="cross_cutting",
                finding=(
                    f"Index `{idx}` on **{target}** — encodes a query-time "
                    "performance invariant the new system must preserve."
                ),
                sources=[SourceRef(file=rel_path, lines=(line, line))],
            )
        )

    if migration:
        # Count both newly-created tables AND tables targeted by ALTER —
        # a migration that only ALTERs still touches its targets, and
        # a "0 table(s)" summary on an ALTER-only file misled callers
        # browsing the report.
        touched = len({hit.name for hit in tables} | altered_tables)
        summary = f"Migration touches {touched} table(s)."
    else:
        summary = f"Schema for {len(tables)} table(s)."
    return SpecializedResult(findings=findings, summary=summary)


def _populate_columns(hit: _TableHit) -> None:
    """Pull column names + foreign-key edges from a CREATE TABLE body."""
    body = hit.body
    columns: list[str] = []
    fks: list[tuple[str, str, str]] = []

    for fk in _FK_RE.finditer(body):
        local_cols = [c.strip().strip('"`[]') for c in fk.group(1).split(",")]
        ref_table = _strip_ident(fk.group(2))
        ref_cols = [c.strip().strip('"`[]') for c in fk.group(3).split(",")]
        for lc, rc in zip(local_cols, ref_cols, strict=False):
            fks.append((lc, ref_table, rc))

    # Split top-level commas so we can read column lines.
    for raw_line in _split_top_level_commas(body):
        line = raw_line.strip()
        if not line:
            continue
        lowered = line.lower()
        if lowered.startswith(("primary key", "foreign key", "unique", "constraint", "check", "index")):
            continue
        # First token is the column name (may be quoted).
        match = re.match(r"\s*([\"`\[]?[\w]+[\"`\]]?)", line)
        if not match:
            continue
        column = match.group(1).strip('"`[]')
        columns.append(column)

        ref = _REF_INLINE_RE.search(line)
        if ref:
            ref_table = _strip_ident(ref.group(1))
            ref_cols = [c.strip().strip('"`[]') for c in ref.group(2).split(",")]
            for rc in ref_cols:
                fks.append((column, ref_table, rc))

    hit.columns = columns
    hit.fks = fks


def _split_top_level_commas(body: str) -> list[str]:
    """Split on commas that are not inside parentheses."""
    out: list[str] = []
    depth = 0
    buf: list[str] = []
    for ch in body:
        if ch == "(":
            depth += 1
            buf.append(ch)
        elif ch == ")":
            depth = max(0, depth - 1)
            buf.append(ch)
        elif ch == "," and depth == 0:
            out.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        out.append("".join(buf))
    return out


def _parse_constraints(body: str) -> str:
    bits: list[str] = []
    if _UNIQUE_RE.search(body):
        bits.append("UNIQUE")
    if _NOT_NULL_RE.search(body):
        bits.append("NOT NULL")
    return ", ".join(bits)


def _summarize_alter(action: str) -> str:
    cleaned = " ".join(action.split())
    if len(cleaned) > 160:
        cleaned = cleaned[:157] + "..."
    return cleaned


def _strip_ident(name: str) -> str:
    return name.strip().strip('"`[]')


def _line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1
