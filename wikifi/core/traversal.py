import os
from pathlib import Path
from typing import Dict, List, Tuple

import pathspec

from wikifi.config import get_settings
from wikifi.llm import llm_provider
from wikifi.models import DirectorySummary, IntrospectionAssessment


class TraversalEngine:
    def __init__(self):
        self.settings = get_settings()
        self.root_path = Path(self.settings.root_path)
        self.spec = self._build_pathspec()

    def _build_pathspec(self) -> pathspec.PathSpec:
        patterns = list(self.settings.exclude_patterns)
        gitignore_path = self.root_path / ".gitignore"
        if gitignore_path.exists():
            with open(gitignore_path, "r", encoding="utf-8") as f:
                patterns.extend(f.readlines())
        return pathspec.PathSpec.from_lines("gitwildmatch", patterns)

    def _is_excluded(self, path: Path) -> bool:
        try:
            rel_path = path.relative_to(self.root_path)
        except ValueError:
            return True
        return self.spec.match_file(str(rel_path))

    def get_file_stats(self, file_path: Path) -> Tuple[int, bool]:
        """Returns (size, is_valid_size)"""
        try:
            size = file_path.stat().st_size
            if size < self.settings.min_content_length:
                return size, False
            if size > self.settings.max_file_size:
                return self.settings.max_file_size, True  # We truncate later during extraction
            return size, True
        except OSError:
            return 0, False

    def traverse(self) -> Tuple[List[Path], DirectorySummary]:
        valid_files = []
        total_size = 0
        ext_dist: Dict[str, int] = {}
        manifest_presence = False

        manifest_files = {"package.json", "pyproject.toml", "Cargo.toml", "go.mod", "pom.xml", "build.gradle"}

        for dirpath, dirnames, filenames in os.walk(self.root_path):
            current_dir = Path(dirpath)

            # Prune directories in-place to avoid walking excluded trees
            dirnames[:] = [d for d in dirnames if not self._is_excluded(current_dir / d)]

            for filename in filenames:
                file_path = current_dir / filename
                if self._is_excluded(file_path):
                    continue

                if filename in manifest_files:
                    manifest_presence = True

                size, is_valid = self.get_file_stats(file_path)
                if not is_valid:
                    continue

                valid_files.append(file_path)
                total_size += size
                ext = file_path.suffix.lower()
                ext_dist[ext] = ext_dist.get(ext, 0) + 1

        summary = DirectorySummary(
            file_count=len(valid_files),
            total_size=total_size,
            extension_distribution=ext_dist,
            manifest_presence=manifest_presence,
        )
        return valid_files, summary

    def get_introspection_assessment(
        self, summary: DirectorySummary, manifests_content: str
    ) -> IntrospectionAssessment:
        prompt = (
            "Analyze the following repository structural summary and manifest contents.\n\n"
            f"File Count: {summary.file_count}\n"
            f"Total Size: {summary.total_size} bytes\n"
            f"Extension Distribution: {summary.extension_distribution}\n"
            f"Manifest Presence: {summary.manifest_presence}\n\n"
            f"Manifest Contents (snippets):\n{manifests_content}\n\n"
            "Based on this structural data, provide an introspection assessment."
        )
        return llm_provider.generate_structured(prompt, IntrospectionAssessment)

    def extract_manifests(self, valid_files: List[Path]) -> str:
        manifest_names = {
            "package.json",
            "pyproject.toml",
            "Cargo.toml",
            "go.mod",
            "pom.xml",
            "build.gradle",
            "README.md",
        }
        content = ""
        for p in valid_files:
            if p.name in manifest_names:
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        text = f.read(5000)  # Truncate large manifests for the prompt
                        content += f"--- {p.name} ---\n{text}\n\n"
                except Exception:
                    pass
        return content


def run_introspection() -> Tuple[List[Path], DirectorySummary, IntrospectionAssessment]:
    engine = TraversalEngine()
    valid_files, summary = engine.traverse()
    manifests_content = engine.extract_manifests(valid_files)
    assessment = engine.get_introspection_assessment(summary, manifests_content)
    return valid_files, summary, assessment
