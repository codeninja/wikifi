from __future__ import annotations

from wikifi.models import Settings
from wikifi.traversal import discover_source_files


def test_traversal_filters_non_production_and_truncates_large_files(tmp_path) -> None:
    (tmp_path / "README.md").write_text("# Sample\n\nExplains the product.", encoding="utf-8")
    (tmp_path / "app.py").write_text(
        "class OrderLedger:\n"
        "    def capture_payment_intent(self):\n"
        "        return 'tracks payment obligations for operators'\n",
        encoding="utf-8",
    )
    (tmp_path / "__init__.py").write_text("x = 1\n", encoding="utf-8")
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_app.py").write_text("def test_placeholder():\n    assert True\n", encoding="utf-8")
    (tmp_path / "large.py").write_text("def keep():\n    return 'domain evidence'\n" * 20, encoding="utf-8")
    (tmp_path / "image.png").write_bytes(b"\x00\x01\x02")

    settings = Settings(max_file_bytes=80, min_content_bytes=12)

    summary, sources, skipped = discover_source_files(tmp_path, settings)

    assert summary.file_count == 5
    assert summary.selected_file_count == 2
    assert "README.md" in summary.manifest_files
    assert {source.relative_path for source in sources} == {"app.py", "large.py"}
    large = next(source for source in sources if source.relative_path == "large.py")
    assert large.truncated is True
    skipped_reasons = {item.relative_path: item.reason for item in skipped}
    assert skipped_reasons["__init__.py"] == "near_empty_content"
    assert skipped_reasons["tests/test_app.py"] == "non_production_artifact"
    assert skipped_reasons["image.png"] == "excluded_path"
