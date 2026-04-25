from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any

from wikifi.constants import PRIMARY_SECTIONS
from wikifi.models import ExtractionNote, IntrospectionAssessment, SourceFile
from wikifi.providers import LLMProvider, ProviderError
from wikifi.text import dedupe, domain_language, first_sentence, summarize_text

EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["role_summary", "finding", "categories", "gaps"],
    "properties": {
        "role_summary": {"type": "string"},
        "finding": {"type": "string"},
        "categories": {"type": "object"},
        "gaps": {"type": "array", "items": {"type": "string"}},
    },
}


def extract_notes(
    sources: tuple[SourceFile, ...],
    assessment: IntrospectionAssessment,
    provider: LLMProvider,
    *,
    allow_fallback: bool,
) -> tuple[tuple[ExtractionNote, ...], str]:
    notes: list[ExtractionNote] = []
    provider_failures = 0
    for source in sources:
        try:
            note = _provider_note(source, assessment, provider)
        except ProviderError as exc:
            provider_failures += 1
            if not allow_fallback:
                raise
            note = _heuristic_note(source, provider_status=f"fallback: {exc}")
        notes.append(note)

    if provider_failures:
        status = f"provider degraded; deterministic fallback used for {provider_failures} file(s)"
    else:
        status = f"provider {provider.provider_id} completed extraction"
    return tuple(notes), status


def _provider_note(source: SourceFile, assessment: IntrospectionAssessment, provider: LLMProvider) -> ExtractionNote:
    system = (
        "You extract technology-agnostic domain knowledge from source files. Describe what the system does and why. "
        "Do not recommend a target architecture, language, or framework. Preserve gaps explicitly."
    )
    prompt = "\n".join(
        [
            f"Repository purpose: {assessment.inferred_purpose}",
            f"Source file: {source.relative_path}",
            "Summarize this file as migration-ready domain knowledge.",
            "Map findings into these category keys when supported by evidence: "
            + ", ".join(section.key for section in PRIMARY_SECTIONS),
            "Source content:",
            source.content,
        ]
    )
    payload = provider.generate_json(system=system, prompt=prompt, schema=EXTRACTION_SCHEMA)
    role_summary = _payload_string(payload, "role_summary") or _fallback_role(source)
    finding = _payload_string(payload, "finding") or _fallback_finding(source)
    categories = _payload_categories(payload.get("categories"))
    gaps = tuple(str(item) for item in payload.get("gaps", []) if str(item).strip())
    return ExtractionNote.build(
        file_reference=source.relative_path,
        role_summary=domain_language(role_summary),
        finding=domain_language(finding),
        categories=categories or _heuristic_categories(source),
        evidence=_evidence(source),
        source_digest=source.digest,
        provider_used=provider.provider_id,
        gaps=gaps,
    )


def _heuristic_note(source: SourceFile, *, provider_status: str = "deterministic local analysis") -> ExtractionNote:
    categories = _heuristic_categories(source)
    gaps = (
        "AI provider output was unavailable, so this note preserves deterministic local evidence instead of "
        "fabricating unstated intent.",
    )
    return ExtractionNote.build(
        file_reference=source.relative_path,
        role_summary=_fallback_role(source),
        finding=_fallback_finding(source),
        categories=categories,
        evidence=_evidence(source),
        source_digest=source.digest,
        provider_used=provider_status,
        gaps=gaps,
    )


def _heuristic_categories(source: SourceFile) -> dict[str, list[str]]:
    path_text = source.relative_path.replace("_", " ").replace("-", " ")
    lower = (source.relative_path + "\n" + source.content[:4000]).lower()
    categories: dict[str, list[str]] = {section.key: [] for section in PRIMARY_SECTIONS}

    categories["domains"].append(f"{_human_name(source)} participates in the system's automated knowledge workflow.")
    categories["intent"].append(_fallback_finding(source))
    categories["capabilities"].extend(_capability_findings(source))
    categories["entities"].extend(_entity_findings(source))
    categories["hard_specifications"].extend(_hard_spec_findings(source))

    if any(token in lower for token in ("http", "url", "host", "api", "provider", "request")):
        categories["external_dependencies"].append(
            f"{_human_name(source)} references external or host-provided services through an abstract boundary."
        )
    if any(token in lower for token in ("cli", "command", "orchestr", "pipeline", "stage", "handoff")):
        categories["integrations"].append(
            f"{_human_name(source)} coordinates handoffs between user commands and internal processing stages."
        )
    if any(token in lower for token in ("log", "summary", "metric", "status", "error", "fallback", "skip")):
        categories["cross_cutting"].append(
            f"{_human_name(source)} preserves operational visibility, fault tolerance, or traceability concerns."
        )
    if source.truncated:
        categories["hard_specifications"].append(
            f"{path_text} exceeded the configured file-size boundary and was truncated before analysis."
        )
    categories["inline_schematics"].append(f"{_human_name(source)} contributes evidence to aggregate Mermaid diagrams.")

    return {key: dedupe(value) for key, value in categories.items()}


def _capability_findings(source: SourceFile) -> list[str]:
    content = source.content
    findings: list[str] = []
    if source.extension == ".py":
        findings.extend(_python_capabilities(content, source))
    if not findings:
        findings.append(f"{_human_name(source)} provides production behavior within the documented source boundary.")
    return findings


def _python_capabilities(content: str, source: SourceFile) -> list[str]:
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return [f"{_human_name(source)} contains source behavior that could not be structurally parsed."]

    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) and not node.name.startswith("_"):
            names.append(node.name.replace("_", " "))
    if not names:
        return [f"{_human_name(source)} defines internal behavior without public source-level entry points."]
    return [f"{_human_name(source)} exposes behavior for {', '.join(dedupe(names)[:8])}."]


def _entity_findings(source: SourceFile) -> list[str]:
    if source.extension != ".py":
        return []
    try:
        tree = ast.parse(source.content)
    except SyntaxError:
        return []
    entities: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            entities.append(node.name.replace("_", " "))
    if not entities:
        return []
    return [f"{_human_name(source)} defines structured concepts: {', '.join(dedupe(entities)[:10])}."]


def _hard_spec_findings(source: SourceFile) -> list[str]:
    lower = source.content.lower()
    findings: list[str] = []
    for token in ("must", "never", "strict", "required", "threshold", "fallback", "unsupported"):
        if token in lower:
            findings.append(f"{_human_name(source)} contains explicit guardrail language around {token}.")
    return dedupe(findings)


def _fallback_role(source: SourceFile) -> str:
    return f"{_human_name(source)} is a production source artifact in the wikified system boundary."


def _fallback_finding(source: SourceFile) -> str:
    names = _meaningful_terms(source)
    if names:
        return (
            f"{_human_name(source)} supports the system's intent by handling "
            f"{', '.join(names[:6])} in domain-facing workflow terms."
        )
    return f"{_human_name(source)} contributes production behavior, but its exact business role is not explicit."


def _meaningful_terms(source: SourceFile) -> list[str]:
    path_terms = re.split(r"[/_.-]+", source.relative_path)
    content_terms = re.findall(r"\b[A-Za-z][A-Za-z0-9_]{3,}\b", source.content[:3000])
    blocked = {"from", "import", "return", "class", "def", "self", "true", "false", "none", "with"}
    return dedupe(
        domain_language(term.replace("_", " "))
        for term in [*path_terms, *content_terms]
        if term.lower() not in blocked and not term.startswith("__")
    )


def _human_name(source: SourceFile) -> str:
    stem = Path(source.relative_path).stem.replace("_", " ").replace("-", " ")
    return first_sentence(domain_language(stem)).capitalize()


def _evidence(source: SourceFile) -> str:
    return summarize_text(source.content, limit=900)


def _payload_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    return str(value).strip() if value is not None else ""


def _payload_categories(value: Any) -> dict[str, list[str]]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return {}
    if not isinstance(value, dict):
        return {}
    categories: dict[str, list[str]] = {}
    valid_keys = {section.key for section in PRIMARY_SECTIONS}
    for key, raw_items in value.items():
        if key not in valid_keys:
            continue
        if isinstance(raw_items, str):
            items = [raw_items]
        elif isinstance(raw_items, list):
            items = [str(item) for item in raw_items]
        else:
            continue
        categories[key] = dedupe(domain_language(item) for item in items)
    return categories
