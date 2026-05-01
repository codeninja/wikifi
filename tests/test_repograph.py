"""Repo graph + file classification tests."""

from __future__ import annotations

from pathlib import Path

from wikifi.repograph import FileKind, build_graph, classify


def test_classify_extension_only():
    assert classify(Path("schema.sql")) is FileKind.SQL
    assert classify(Path("api.proto")) is FileKind.PROTOBUF
    assert classify(Path("schema.graphql")) is FileKind.GRAPHQL


def test_classify_application_code():
    assert classify(Path("src/app.py")) is FileKind.APPLICATION_CODE
    assert classify(Path("src/app.ts")) is FileKind.APPLICATION_CODE
    assert classify(Path("src/app.go")) is FileKind.APPLICATION_CODE


def test_classify_migration_path():
    assert classify(Path("backend/migrations/0001_init.sql")) is FileKind.MIGRATION
    assert classify(Path("alembic/versions/abc.py")) is FileKind.MIGRATION


def test_classify_openapi_via_sample():
    assert classify(Path("api.yaml"), sample="openapi: 3.0.3\ninfo: ...") is FileKind.OPENAPI
    assert classify(Path("api.json"), sample='{"openapi": "3.0.0"}') is FileKind.OPENAPI


def test_classify_other():
    assert classify(Path("README.md")) is FileKind.OTHER
    assert classify(Path("data.csv")) is FileKind.OTHER


def test_build_graph_python_imports(tmp_path: Path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("")
    (tmp_path / "pkg" / "a.py").write_text("from pkg.b import thing\nimport os\n")
    (tmp_path / "pkg" / "b.py").write_text("def thing(): return 1\n")

    files = [Path("pkg/__init__.py"), Path("pkg/a.py"), Path("pkg/b.py")]
    graph = build_graph(repo_root=tmp_path, files=files)

    a_node = graph.get("pkg/a.py")
    assert a_node is not None
    assert "pkg/b.py" in a_node.imports

    b_node = graph.get("pkg/b.py")
    assert b_node is not None
    assert "pkg/a.py" in b_node.imported_by


def test_build_graph_js_imports(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.js").write_text("import { run } from './worker';\n")
    (tmp_path / "src" / "worker.js").write_text("export function run() {}\n")

    files = [Path("src/main.js"), Path("src/worker.js")]
    graph = build_graph(repo_root=tmp_path, files=files)
    main_node = graph.get("src/main.js")
    assert main_node is not None
    assert "src/worker.js" in main_node.imports


def test_neighbor_paths_caps_results(tmp_path: Path):
    """neighbors() bounds the prompt-side noise."""
    (tmp_path / "hub.py").write_text("\n".join(f"from leaf{i} import foo" for i in range(20)))
    for i in range(20):
        (tmp_path / f"leaf{i}.py").write_text("def foo(): pass\n")
    files = [Path("hub.py")] + [Path(f"leaf{i}.py") for i in range(20)]
    graph = build_graph(repo_root=tmp_path, files=files)
    neighbors = graph.neighbor_paths("hub.py", limit=5)
    assert len(neighbors) == 5


def test_build_graph_skips_unreadable_files(tmp_path: Path):
    """Missing-file path is exercised even if no other tests trip it."""
    files = [Path("ghost.py")]
    graph = build_graph(repo_root=tmp_path, files=files)
    # No edges produced; graph still records a node with empty imports.
    node = graph.get("ghost.py")
    assert node is not None
    assert node.imports == ()
