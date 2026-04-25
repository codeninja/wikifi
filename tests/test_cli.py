from typer.testing import CliRunner

from wikifi.main import app

runner = CliRunner()


def test_init_command(tmp_path, monkeypatch):
    # Mock settings to point to tmp_path
    monkeypatch.setenv("WORKSPACE_PATH", str(tmp_path / ".wikifi"))

    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    assert "Initialized workspace" in result.stdout
    assert (tmp_path / ".wikifi" / "config.json").exists()


def test_init_command_existing_workspace(tmp_path, monkeypatch):
    workspace = tmp_path / ".wikifi"
    workspace.mkdir(parents=True)
    monkeypatch.setenv("WORKSPACE_PATH", str(workspace))

    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    assert "Workspace already exists" in result.stdout


def test_walk_command(tmp_path, monkeypatch):
    monkeypatch.setenv("ROOT_PATH", str(tmp_path))
    monkeypatch.setenv("WORKSPACE_PATH", str(tmp_path / ".wikifi"))

    (tmp_path / "test.py").write_text(
        "print('hello world! this is a longer file to pass the 64 byte minimum content length filter.')"
    )

    result = runner.invoke(app, ["walk"])
    assert result.exit_code == 0
    assert "Walk completed" in result.stdout
    assert (tmp_path / ".wikifi" / "execution_summary.json").exists()
