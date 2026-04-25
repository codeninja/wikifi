import os
from pathlib import Path
from typing import List
import pathspec
from wikifi.config import settings
from wikifi.models import DirectorySummary

class RepoWalker:
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir).resolve()
        self.spec = self._load_ignore_spec()
        self.manifest_names = {
            "pyproject.toml", "package.json", "Makefile", "Dockerfile", 
            "docker-compose.yml", "go.mod", "Cargo.toml", "requirements.txt",
            "README.md", "VISION.md", "CLAUDE.md"
        }

    def _load_ignore_spec(self):
        patterns = settings.exclude_patterns
        # Try to load .gitignore if it exists
        gitignore_path = self.root_dir / ".gitignore"
        if gitignore_path.exists():
            with open(gitignore_path, "r") as f:
                patterns.extend(f.readlines())
        return pathspec.PathSpec.from_lines("gitwildmatch", patterns)

    def is_ignored(self, path: Path) -> bool:
        relative_path = path.relative_to(self.root_dir)
        return self.spec.match_file(str(relative_path))

    def walk(self) -> List[Path]:
        in_scope_files = []
        for root, dirs, files in os.walk(self.root_dir):
            root_path = Path(root)
            
            # Prune ignored directories
            dirs[:] = [d for d in dirs if not self.is_ignored(root_path / d)]
            
            for file in files:
                file_path = root_path / file
                if not self.is_ignored(file_path):
                    if self._should_include(file_path):
                        in_scope_files.append(file_path)
        return in_scope_files

    def _should_include(self, file_path: Path) -> bool:
        if not file_path.is_file():
            return False
        
        # Check size
        size = file_path.stat().st_size
        if size > settings.max_file_size:
            # We truncate during extraction, but we still include it if it's substantive
            pass
        
        # Check if it's too small (stripped content check happens later or here)
        # For now, just check raw size as a proxy
        if size < settings.min_content_bytes:
            return False
            
        return True

    def summarize(self, in_scope_files: List[Path]) -> DirectorySummary:
        summary = DirectorySummary()
        summary.file_count = len(in_scope_files)
        
        for file_path in in_scope_files:
            stat = file_path.stat()
            summary.total_size += stat.st_size
            
            ext = file_path.suffix or "no_extension"
            summary.extension_distribution[ext] = summary.extension_distribution.get(ext, 0) + 1
            
            if file_path.name in self.manifest_names:
                summary.manifests.append(str(file_path.relative_to(self.root_dir)))
                
        return summary
