from wikifi.core.pipeline import run_pipeline


def test_pipeline_no_files(tmp_path):
    # setup_env fixture sets ROOT_PATH to tmp_path
    # tmp_path is empty initially
    summary = run_pipeline()
    assert summary.completion_status == "halted"
    assert "No valid files" in summary.consolidated_findings


def test_pipeline_with_files(tmp_path):
    # Create some dummy files to trigger extraction
    (tmp_path / "test.py").write_text(
        "print('hello world! this is a longer file to pass the 64 byte minimum content length filter.')"
    )
    (tmp_path / "package.json").write_text(
        '{"name": "test", "description": "a longer description to pass the minimum content length"}'
    )

    summary = run_pipeline()
    assert summary.completion_status == "success"
    assert "2 notes extracted" in summary.consolidated_findings

    # Check outputs exist
    workspace = tmp_path / ".wikifi"
    assert (workspace / "notes").exists()
    assert len(list((workspace / "notes").iterdir())) == 2

    assert (workspace / "domains.md").exists()
    assert (workspace / "intent.md").exists()
    assert (workspace / "user_personas.md").exists()
