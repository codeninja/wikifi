import os
from pathlib import Path
from wikifi.walker import RepoWalker

def test_walker_finds_files(tmp_path):
    # Setup tmp repo
    (tmp_path / "src").mkdir()
    main_py = tmp_path / "src" / "main.py"
    main_py.write_text("print('hello world')\n" * 10) # > 64 bytes
    readme_md = tmp_path / "README.md"
    readme_md.write_text("# Test Repo\n" + "This is a test repository for wikifi.\n" * 5)
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("some git config content that doesn't matter")
    
    walker = RepoWalker(str(tmp_path))
    files = walker.walk()
    
    # .git should be ignored
    filenames = [f.name for f in files]
    assert "main.py" in filenames
    assert "README.md" in filenames
    assert "config" not in filenames

def test_walker_summarize(tmp_path):
    main_py = tmp_path / "main.py"
    main_py.write_text("print('hello world')\n" * 10)
    pkg_json = tmp_path / "package.json"
    pkg_json.write_text('{\n  "name": "test-package",\n  "version": "1.0.0"\n}\n' * 5)
    
    walker = RepoWalker(str(tmp_path))
    files = walker.walk()
    summary = walker.summarize(files)
    
    assert summary.file_count == 2
    assert "package.json" in summary.manifests
    assert ".py" in summary.extension_distribution
    assert ".json" in summary.extension_distribution
