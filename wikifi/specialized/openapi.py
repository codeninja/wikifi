"""OpenAPI / Swagger contract extractor.

OpenAPI specs are migration gold: every public endpoint, request/response
body, and authentication method is enumerated in one structured document.
We avoid pulling PyYAML as a hard dependency by attempting JSON first,
then falling back to a small permissive YAML parser sufficient for the
keys we read. Specs that exceed the parser's limits are flagged with a
single ``capabilities`` finding noting the parse failure rather than
crashing the walk.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from wikifi.evidence import SourceRef
from wikifi.specialized import SpecializedFinding, SpecializedResult

log = logging.getLogger("wikifi.specialized.openapi")


def extract(rel_path: str, text: str) -> SpecializedResult:
    spec = _parse(text)
    if spec is None:
        return SpecializedResult(
            findings=[
                SpecializedFinding(
                    section_id="capabilities",
                    finding=(
                        "An API contract was found but could not be parsed for "
                        "structured extraction. Migration teams should consult "
                        "this file directly for endpoint inventory."
                    ),
                    sources=[SourceRef(file=rel_path)],
                )
            ],
            summary="Unparseable API spec — manual review recommended.",
        )

    findings: list[SpecializedFinding] = []
    summary_bits: list[str] = []

    info = spec.get("info") or {}
    if isinstance(info, dict) and (title := info.get("title")):
        findings.append(
            SpecializedFinding(
                section_id="intent",
                finding=(
                    f"The system exposes a public API titled **{title}**"
                    + (f" (v{info.get('version')})" if info.get("version") else "")
                    + (f": {info.get('description')}" if info.get("description") else ".")
                ),
                sources=[SourceRef(file=rel_path)],
            )
        )

    paths = spec.get("paths") or {}
    if isinstance(paths, dict):
        verbs = ("get", "post", "put", "patch", "delete", "head", "options")
        endpoints: list[tuple[str, str, str]] = []
        for path, ops in paths.items():
            if not isinstance(ops, dict):
                continue
            for verb in verbs:
                op = ops.get(verb)
                if not isinstance(op, dict):
                    continue
                description = op.get("summary") or op.get("description") or ""
                endpoints.append((verb.upper(), str(path), str(description)))
        if endpoints:
            summary_bits.append(f"{len(endpoints)} endpoint(s)")
            top = endpoints[:20]
            bullets = "\n".join(f"  - `{verb} {path}`{(' — ' + desc) if desc else ''}" for verb, path, desc in top)
            more = f"\n  - … {len(endpoints) - 20} more endpoint(s) elided." if len(endpoints) > 20 else ""
            findings.append(
                SpecializedFinding(
                    section_id="capabilities",
                    finding=("Public API surface (subset shown):\n" + bullets + more),
                    sources=[SourceRef(file=rel_path)],
                )
            )
            findings.append(
                SpecializedFinding(
                    section_id="integrations",
                    finding=(
                        f"Inbound integration: HTTP API exposes {len(endpoints)} endpoint(s) for external consumers."
                    ),
                    sources=[SourceRef(file=rel_path)],
                )
            )

    components = spec.get("components") or {}
    schemas = components.get("schemas") if isinstance(components, dict) else None
    if isinstance(schemas, dict) and schemas:
        names = list(schemas.keys())
        summary_bits.append(f"{len(names)} schema(s)")
        bullets = "\n".join(f"  - **{name}**" for name in names[:25])
        more = f"\n  - … {len(names) - 25} more schema(s) elided." if len(names) > 25 else ""
        findings.append(
            SpecializedFinding(
                section_id="entities",
                finding=("API schemas (request/response models):\n" + bullets + more),
                sources=[SourceRef(file=rel_path)],
            )
        )

    security = components.get("securitySchemes") if isinstance(components, dict) else None
    if isinstance(security, dict) and security:
        types = sorted({(v or {}).get("type", "?") for v in security.values() if isinstance(v, dict)})
        findings.append(
            SpecializedFinding(
                section_id="cross_cutting",
                finding=("Authentication contract for the API: scheme(s) " + ", ".join(f"`{t}`" for t in types) + "."),
                sources=[SourceRef(file=rel_path)],
            )
        )

    return SpecializedResult(
        findings=findings,
        summary="API contract: " + ", ".join(summary_bits) if summary_bits else "API contract.",
    )


def _parse(text: str) -> dict[str, Any] | None:
    stripped = text.strip()
    if not stripped:
        return None
    if stripped.startswith("{"):
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            return None
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:
        return _shallow_yaml(stripped)
    try:
        loaded = yaml.safe_load(stripped)
    except Exception as exc:  # pragma: no cover - depends on installed PyYAML
        log.warning("yaml parse failed: %s", exc)
        return None
    return loaded if isinstance(loaded, dict) else None


# ---------------------------------------------------------------------------
# Tiny YAML fallback — only handles the OpenAPI subset we need (top-level
# keys, simple nested dicts, and method blocks under paths).
# ---------------------------------------------------------------------------


_KEY_RE = re.compile(r"^(\s*)([\w./{}-]+):\s*(.*)$")


def _shallow_yaml(text: str) -> dict[str, Any] | None:
    """Best-effort YAML parser sufficient for OpenAPI's known shape.

    Returns nested dicts where each key contributes a string value or a
    nested dict; lists and complex flow-style structures collapse to
    string descriptions, which is fine for the keys :func:`extract`
    actually inspects.
    """
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]
    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        match = _KEY_RE.match(raw_line)
        if not match:
            continue
        indent = len(match.group(1))
        key = match.group(2).strip()
        value = match.group(3).strip()
        while stack and stack[-1][0] >= indent:
            stack.pop()
        if not stack:
            stack.append((-1, root))
        parent = stack[-1][1]
        if value == "" or value == "{}":
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            stripped = value.strip().strip('"').strip("'")
            parent[key] = stripped
    return root or None
