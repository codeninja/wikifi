from pathlib import Path

import typer
from rich.console import Console

from wikifi.config import get_settings
from wikifi.core.pipeline import run_pipeline

app = typer.Typer()
console = Console()


@app.command()
def init():
    """
    Initialize the .wikifi workspace.
    """
    settings = get_settings()
    workspace = Path(settings.workspace_path)

    if not workspace.exists():
        workspace.mkdir(parents=True, exist_ok=True)
        console.print(f"[bold green]Initialized workspace at {workspace}[/bold green]")

        # Write default config.json
        config_file = workspace / "config.json"
        with open(config_file, "w", encoding="utf-8") as f:
            f.write("{}")

        console.print(f"[bold green]Created default config at {config_file}[/bold green]")
    else:
        console.print(f"[bold yellow]Workspace already exists at {workspace}[/bold yellow]")


@app.command()
def walk():
    """
    Walk the codebase and generate the technology-agnostic wiki.
    """
    settings = get_settings()
    workspace = Path(settings.workspace_path)

    if not workspace.exists():
        console.print("[bold yellow]Workspace not found. Auto-provisioning...[/bold yellow]")
        init()

    console.print("[bold blue]Starting wikifi walk...[/bold blue]")
    summary = run_pipeline()
    console.print("\n[bold green]Walk completed![/bold green]")
    console.print(f"Status: {summary.completion_status}")
    console.print(f"Findings: {summary.consolidated_findings}")

    # Save execution summary
    summary_file = workspace / "execution_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(summary.model_dump_json(indent=2))

    console.print(f"Execution summary saved to {summary_file}")


if __name__ == "__main__":
    app()
