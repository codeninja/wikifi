"""Typer-driven CLI for wikifi.

Entry point: ``wikifi`` (declared in ``pyproject.toml`` ``[project.scripts]``).

- ``wikifi init`` — scaffold the ``.wikifi/`` directory in CWD
- ``wikifi walk`` — run the full Stage 1→2→3→4 pipeline against CWD
- ``wikifi chat`` — interactive REPL with ``.wikifi/`` content as context
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from wikifi import __version__
from wikifi.chat import run_repl
from wikifi.config import get_settings
from wikifi.orchestrator import build_provider, init_wiki, run_walk
from wikifi.wiki import WikiLayout

app = typer.Typer(
    help="Walk a codebase and produce a technology-agnostic markdown wiki of its intent.",
    no_args_is_help=True,
    add_completion=False,
    invoke_without_command=True,
)

console = Console()

TargetArg = Annotated[
    Path | None,
    typer.Argument(
        help="Target project root. Defaults to the current working directory.",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
]


@app.callback()
def _root(
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable debug logging.")] = False,
    version: Annotated[bool, typer.Option("--version", help="Print wikifi version and exit.")] = False,
) -> None:
    """Configure shared options across subcommands."""
    if version:
        console.print(f"wikifi {__version__}")
        raise typer.Exit()
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


@app.command()
def init(target: TargetArg = None) -> None:
    """Create the .wikifi/ skeleton in the target project."""
    target = target or Path.cwd()
    settings = get_settings()
    paths = init_wiki(root=target, settings=settings)
    console.print(
        Panel.fit(
            f"[green]Initialized .wikifi/ in [bold]{target}[/bold][/green]\n"
            f"provider = {settings.provider}\n"
            f"model = {settings.model}\n"
            f"ollama_host = {settings.ollama_host}\n\n"
            f"{len(paths)} files / dirs in place. Run [bold]wikifi walk[/bold] to populate.",
            title="wikifi init",
        )
    )


@app.command()
def walk(target: TargetArg = None) -> None:
    """Walk the target codebase and populate every wiki section."""
    target = target or Path.cwd()
    settings = get_settings()
    console.print(
        Panel.fit(
            f"[bold]wikifi walk[/bold] — target=[cyan]{target}[/cyan] model=[cyan]{settings.model}[/cyan]",
            title="starting",
        )
    )
    report = run_walk(root=target, settings=settings)

    table = Table(title="Walk report", show_header=True, header_style="bold")
    table.add_column("Stage")
    table.add_column("Result")
    table.add_row(
        "1. Introspection",
        f"include={len(report.introspection.include)} "
        f"exclude={len(report.introspection.exclude)} "
        f"langs={', '.join(report.introspection.primary_languages) or '?'}",
    )
    table.add_row(
        "2. Extraction",
        f"seen={report.extraction.files_seen} "
        f"contributed={report.extraction.files_with_findings} "
        f"findings={report.extraction.findings_total} "
        f"skipped={report.extraction.files_skipped}",
    )
    table.add_row(
        "3. Aggregation",
        f"sections_written={report.aggregation.sections_written} sections_empty={report.aggregation.sections_empty}",
    )
    table.add_row(
        "4. Derivation",
        f"sections_derived={report.derivation.sections_derived} sections_skipped={report.derivation.sections_skipped}",
    )
    console.print(table)
    console.print(f"\n[green]Done.[/green] Wiki at [bold]{target}/.wikifi/[/bold]")


@app.command()
def chat(target: TargetArg = None) -> None:
    """Open an interactive REPL with .wikifi/ section content as context."""
    target = target or Path.cwd()
    layout = WikiLayout(root=target)
    if not layout.wiki_dir.exists():
        console.print(
            f"[red]No .wikifi/ directory at {target}.[/red] "
            "Run [bold]wikifi init[/bold] and [bold]wikifi walk[/bold] first."
        )
        raise typer.Exit(code=1)

    settings = get_settings()
    provider = build_provider(settings)
    run_repl(layout=layout, provider=provider, console=console)


def main() -> None:
    """Entry point referenced by [project.scripts] in pyproject.toml."""
    app()


if __name__ == "__main__":
    main()
