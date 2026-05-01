"""Typer-driven CLI for wikifi.

Entry point: ``wikifi`` (declared in ``pyproject.toml`` ``[project.scripts]``).

- ``wikifi init`` — scaffold the ``.wikifi/`` directory in CWD
- ``wikifi walk`` — run the full Stage 1→2→3→4 pipeline against CWD
- ``wikifi chat`` — interactive REPL with ``.wikifi/`` content as context
- ``wikifi report`` — coverage + quality report on the wiki
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from wikifi import __version__
from wikifi.cache import reset as reset_cache
from wikifi.chat import run_repl
from wikifi.config import get_settings
from wikifi.orchestrator import build_provider, init_wiki, run_walk
from wikifi.report import build_report
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
def walk(
    target: TargetArg = None,
    no_cache: Annotated[
        bool, typer.Option("--no-cache", help="Force a clean re-walk; drop the on-disk cache.")
    ] = False,
    review: Annotated[
        bool,
        typer.Option("--review/--no-review", help="Run the critic + reviser loop on derivative sections."),
    ] = False,
    provider: Annotated[
        str | None,
        typer.Option("--provider", help="Override the configured provider for this walk ('ollama' | 'anthropic')."),
    ] = None,
) -> None:
    """Walk the target codebase and populate every wiki section."""
    target = target or Path.cwd()
    settings = get_settings()
    if no_cache:
        settings = settings.model_copy(update={"use_cache": False})
        reset_cache(WikiLayout(root=target))
    if review:
        settings = settings.model_copy(update={"review_derivatives": True})
    if provider:
        settings = settings.model_copy(update={"provider": provider})

    console.print(
        Panel.fit(
            f"[bold]wikifi walk[/bold] — target=[cyan]{target}[/cyan] "
            f"provider=[cyan]{settings.provider}[/cyan] model=[cyan]{settings.model}[/cyan]\n"
            f"cache=[cyan]{settings.use_cache}[/cyan] graph=[cyan]{settings.use_graph}[/cyan] "
            f"specialized=[cyan]{settings.use_specialized_extractors}[/cyan] "
            f"review=[cyan]{settings.review_derivatives}[/cyan]",
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
    extraction_row = (
        f"seen={report.extraction.files_seen} "
        f"contributed={report.extraction.files_with_findings} "
        f"findings={report.extraction.findings_total} "
        f"skipped={report.extraction.files_skipped} "
        f"cache_hits={report.extraction.cache_hits} "
        f"specialized={report.extraction.specialized_files}"
    )
    table.add_row("2. Extraction", extraction_row)
    table.add_row(
        "3. Aggregation",
        f"sections_written={report.aggregation.sections_written} "
        f"sections_empty={report.aggregation.sections_empty} "
        f"sections_cached={report.aggregation.sections_cached}",
    )
    derivation_row = (
        f"sections_derived={report.derivation.sections_derived} "
        f"sections_skipped={report.derivation.sections_skipped} "
        f"sections_revised={report.derivation.sections_revised}"
    )
    table.add_row("4. Derivation", derivation_row)
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


@app.command()
def report(
    target: TargetArg = None,
    score: Annotated[
        bool,
        typer.Option("--score/--no-score", help="Run the critic on every populated section for quality scoring."),
    ] = False,
) -> None:
    """Print a coverage + quality report for the wiki at ``target``."""
    target = target or Path.cwd()
    layout = WikiLayout(root=target)
    if not layout.wiki_dir.exists():
        console.print(
            f"[red]No .wikifi/ directory at {target}.[/red] "
            "Run [bold]wikifi init[/bold] and [bold]wikifi walk[/bold] first."
        )
        raise typer.Exit(code=1)

    settings = get_settings()
    provider = build_provider(settings) if score else None
    wiki_report = build_report(layout=layout, provider=provider, score=score)
    console.print(Markdown(wiki_report.render()))


def main() -> None:
    """Entry point referenced by [project.scripts] in pyproject.toml."""
    app()


if __name__ == "__main__":
    main()
