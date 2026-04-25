from __future__ import annotations

from pathlib import Path

from wikifi.filters import (
    HARD_EXCLUDED_DIRS,
    NOTABLE_MANIFESTS,
    is_hard_excluded_dir,
    is_probably_binary,
    render_tree,
    scan,
    stripped_size,
)


def test_hard_excluded_membership():
    assert is_hard_excluded_dir(".git")
    assert is_hard_excluded_dir("node_modules")
    assert is_hard_excluded_dir(".wikifi")
    assert not is_hard_excluded_dir("src")


def test_manifests_recognised():
    assert "pyproject.toml" in NOTABLE_MANIFESTS
    assert "package.json" in NOTABLE_MANIFESTS


def test_is_probably_binary_extension(tmp_path: Path):
    image = tmp_path / "x.png"
    image.write_bytes(b"\x89PNG\x00")
    assert is_probably_binary(image)


def test_is_probably_binary_nul_byte(tmp_path: Path):
    blob = tmp_path / "blob.bin"
    blob.write_bytes(b"hello\x00world")
    assert is_probably_binary(blob)


def test_is_probably_binary_text(tmp_path: Path):
    text = tmp_path / "x.txt"
    text.write_text("hello\nworld\n", encoding="utf-8")
    assert not is_probably_binary(text)


def test_stripped_size(tmp_path: Path):
    p = tmp_path / "f.txt"
    p.write_text("  ab  cd  \n", encoding="utf-8")
    assert stripped_size(p) == 4


def test_scan_partitions_files(sample_repo: Path):
    report = scan(sample_repo, max_file_bytes=200_000, min_content_bytes=16)
    in_scope_names = {p.name for p in report.in_scope}
    assert "billing.py" in in_scope_names
    assert "README.md" in in_scope_names
    # __init__ stub falls below min_content_bytes (16)
    skipped_names = {p.name for p in report.skipped_min_bytes}
    assert "__init__.py" in skipped_names
    excluded = {p.as_posix() for p in report.skipped_excluded}
    # node_modules dir is hard-excluded, so its files don't even reach skipped_excluded;
    # gitignored *.log does land in skipped_excluded; binary asset too.
    assert "ignored.log" in excluded
    assert "asset.png" in excluded
    assert any("node_modules" not in p for p in excluded)
    # No hard-excluded directory entries should appear anywhere in the report.
    for hard in HARD_EXCLUDED_DIRS:
        for p in report.in_scope + report.skipped_excluded + report.skipped_min_bytes:
            assert hard not in p.parts


def test_render_tree(sample_repo: Path):
    out = render_tree(sample_repo, depth=3)
    assert "src/" in out
    assert "billing.py" in out
    assert "node_modules" not in out  # hard-excluded
