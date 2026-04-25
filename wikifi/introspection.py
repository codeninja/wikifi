from __future__ import annotations

from pathlib import Path

from wikifi.models import DirectorySummary, IntrospectionAssessment, SourceFile
from wikifi.text import dedupe, first_sentence, summarize_text

LANGUAGE_BY_EXTENSION = {
    ".c": "C-family source",
    ".cc": "C-family source",
    ".clj": "Functional application source",
    ".cpp": "C-family source",
    ".cs": "Managed application source",
    ".css": "Visual presentation rules",
    ".ex": "Concurrent application source",
    ".exs": "Concurrent application source",
    ".go": "Service-oriented application source",
    ".h": "C-family source",
    ".hpp": "C-family source",
    ".html": "User interface markup",
    ".java": "Object-oriented application source",
    ".js": "Interactive application source",
    ".jsx": "Interactive application source",
    ".kt": "Object-oriented application source",
    ".kts": "Object-oriented application source",
    ".php": "Server-side application source",
    ".py": "Application source",
    ".rb": "Dynamic application source",
    ".rs": "Systems application source",
    ".scala": "Functional application source",
    ".sql": "Data persistence definitions",
    ".swift": "Client application source",
    ".ts": "Typed interactive application source",
    ".tsx": "Typed interactive application source",
}


def assess_repository(
    root: Path, summary: DirectorySummary, sources: tuple[SourceFile, ...]
) -> IntrospectionAssessment:
    primary_languages = _primary_languages(summary)
    inferred_purpose = _infer_purpose(root, summary, sources)
    scope_description = (
        f"Selected {summary.selected_file_count} production source files from {summary.file_count} traversable files. "
        "Documentation, manifests, tests, dependency caches, generated assets, and workspace artifacts were used only "
        "for routing or excluded from extraction."
    )
    rationale = (
        "The assessment is derived from repository structure, notable manifests, extension distribution, and immutable "
        "path filters before any source content is parsed."
    )
    gaps: list[str] = []
    if not sources:
        gaps.append("No production source files met the traversal thresholds.")
    if not summary.manifest_files:
        gaps.append("No notable manifest or documentation files were present for structural routing.")

    return IntrospectionAssessment(
        primary_languages=tuple(primary_languages),
        inferred_purpose=inferred_purpose,
        classification_rationale=rationale,
        scope_description=scope_description,
        notable_gaps=tuple(gaps),
    )


def _primary_languages(summary: DirectorySummary) -> list[str]:
    ranked = sorted(
        (
            (count, LANGUAGE_BY_EXTENSION.get(extension, f"{extension} artifacts"))
            for extension, count in summary.extension_distribution.items()
            if extension in LANGUAGE_BY_EXTENSION
        ),
        reverse=True,
    )
    return dedupe(language for _, language in ranked[:3]) or ["Unclassified source artifacts"]


def _infer_purpose(root: Path, summary: DirectorySummary, sources: tuple[SourceFile, ...]) -> str:
    readme_candidates = [
        Path(item) for item in summary.documentation_files if Path(item).name.lower().startswith("readme")
    ]
    for relative in readme_candidates:
        path = root / relative
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for line in content.splitlines():
            cleaned = line.strip(" #\t")
            if cleaned and not cleaned.startswith(">"):
                return first_sentence(summarize_text(cleaned, limit=220))

    if sources:
        stems = dedupe(Path(source.relative_path).stem.replace("_", " ").replace("-", " ") for source in sources[:8])
        return "A system centered on " + ", ".join(stems[:5]) + "."
    return "The system purpose could not be inferred from the allowed source boundary."
