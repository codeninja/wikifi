from wikifi.core.traversal import TraversalEngine


def test_traversal_exclusion(tmp_path):
    (tmp_path / "test.py").write_text("code")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "ignored.js").write_text("ignore me")

    engine = TraversalEngine()
    valid_files, summary = engine.traverse()

    assert len(valid_files) == 0  # test.py is too small (< 64 bytes)

    # Let's make test.py big enough
    (tmp_path / "test.py").write_text("A" * 100)
    valid_files, summary = engine.traverse()

    assert len(valid_files) == 1
    assert valid_files[0].name == "test.py"
    assert summary.file_count == 1

    # Verify node_modules file is excluded
    assert not any("node_modules" in str(p) for p in valid_files)
