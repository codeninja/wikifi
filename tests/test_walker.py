from wikifi.walker import (
    DEFAULT_EXCLUDES,
    WalkConfig,
    iter_files,
    read_manifest_files,
    summarize_tree,
)


def test_iter_files_skips_default_excludes(mini_target):
    # `min_content_bytes=0` so the synthetic fixture's small files still appear.
    files = {p.as_posix() for p in iter_files(WalkConfig(root=mini_target, min_content_bytes=0))}
    assert "src/fakeapp/api.py" in files
    assert "src/fakeapp/domain.py" in files
    assert "pyproject.toml" in files
    assert all("node_modules" not in p for p in files)
    assert all("__pycache__" not in p for p in files)
    assert all(not p.startswith("dist/") for p in files)


def test_iter_files_skips_near_empty_files(tmp_path):
    """Stubs and one-liners get filtered before extraction (timeout protection)."""
    big = tmp_path / "real.py"
    big.write_text("def real_function():\n    return 'meaningful content here'\n" * 5)
    stub = tmp_path / "__init__.py"
    stub.write_text('__version__ = "0.1.0"\n')
    empty = tmp_path / "empty.py"
    empty.write_text("\n  \n")
    files = {p.as_posix() for p in iter_files(WalkConfig(root=tmp_path, min_content_bytes=64))}
    assert "real.py" in files
    assert "__init__.py" not in files
    assert "empty.py" not in files


def test_min_content_bytes_zero_disables_the_filter(tmp_path):
    stub = tmp_path / "__init__.py"
    stub.write_text('__version__ = "0.1.0"\n')
    files = {p.as_posix() for p in iter_files(WalkConfig(root=tmp_path, min_content_bytes=0))}
    assert "__init__.py" in files


def test_iter_files_honors_extra_excludes(mini_target):
    config = WalkConfig(root=mini_target, extra_excludes=("src/fakeapp/api.py",), min_content_bytes=0)
    files = {p.as_posix() for p in iter_files(config)}
    assert "src/fakeapp/api.py" not in files
    assert "src/fakeapp/domain.py" in files


def test_iter_files_skips_oversized(mini_target):
    big = mini_target / "huge.txt"
    big.write_text("x" * 1000)
    files = {p.as_posix() for p in iter_files(WalkConfig(root=mini_target, max_file_bytes=100, min_content_bytes=0))}
    assert "huge.txt" not in files


def test_summarize_tree_includes_root_and_subdirs(mini_target):
    summaries = summarize_tree(WalkConfig(root=mini_target), max_depth=3)
    paths = {s.rel_path for s in summaries}
    assert "" in paths  # root
    assert "src" in paths
    assert "src/fakeapp" in paths
    assert all("node_modules" not in p for p in paths)


def test_summarize_tree_records_notable_files(mini_target):
    summaries = summarize_tree(WalkConfig(root=mini_target), max_depth=3)
    root_summary = next(s for s in summaries if s.rel_path == "")
    assert "pyproject.toml" in root_summary.notable_files
    assert "README.md" in root_summary.notable_files


def test_read_manifest_files_truncates_and_skips_missing(mini_target):
    big = mini_target / "huge_manifest.toml"
    big.write_text("a = " + ("'x'" * 5000) + "\n")
    out = read_manifest_files(
        WalkConfig(root=mini_target),
        paths=["pyproject.toml", "huge_manifest.toml", "does_not_exist.toml"],
        max_bytes=200,
    )
    assert "pyproject.toml" in out
    assert "does_not_exist.toml" not in out
    assert "[truncated]" in out["huge_manifest.toml"]


def test_default_excludes_cover_common_dirs():
    for needle in (".git/", "node_modules/", "__pycache__/", ".wikifi/"):
        assert needle in DEFAULT_EXCLUDES
