"""Command-line interface for wikifi."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from wikifi import __version__
from wikifi.config import load_settings
from wikifi.factory import build_provider
from wikifi.logging_setup import configure as configure_logging
from wikifi.pipeline import run_walk
from wikifi.providers.base import ProviderError
from wikifi.workspace import provision_workspace


@click.group(help="wikifi — walk a codebase and produce a technology-agnostic wiki.")
@click.version_option(__version__, prog_name="wikifi")
@click.option("-v", "--verbose", count=True, help="Increase logging verbosity (-v / -vv).")
@click.pass_context
def cli(ctx: click.Context, verbose: int) -> None:
    configure_logging(verbosity=1 + verbose)
    ctx.ensure_object(dict)
    ctx.obj["verbosity"] = verbose


@cli.command(help="Provision the .wikifi/ workspace inside a target repository.")
@click.option(
    "--target",
    "-t",
    type=click.Path(file_okay=False, exists=True, path_type=Path),
    default=Path.cwd(),
    show_default="cwd",
)
def init(target: Path) -> None:
    settings = load_settings(target)
    workspace = provision_workspace(target, wiki_dir_name=settings.wiki_dir_name)
    click.echo(f"workspace ready: {workspace.wiki_dir}")
    click.echo(f"intermediate notes (gitignored): {workspace.notes_dir}")


@cli.command(help="Walk the target repository and synthesize the wiki.")
@click.option(
    "--target",
    "-t",
    type=click.Path(file_okay=False, exists=True, path_type=Path),
    default=Path.cwd(),
    show_default="cwd",
)
@click.option(
    "--keep-notes",
    is_flag=True,
    default=False,
    help="Skip clearing .wikifi/.notes/ before extraction.",
)
@click.option(
    "--no-healthcheck",
    is_flag=True,
    default=False,
    help="Skip the provider connectivity probe (use only for offline tests).",
)
def walk(target: Path, keep_notes: bool, no_healthcheck: bool) -> None:
    settings = load_settings(target)
    try:
        provider = build_provider(settings)
    except ProviderError as exc:
        click.echo(f"provider configuration error: {exc}", err=True)
        sys.exit(2)

    if no_healthcheck:
        provider.healthcheck = lambda: None  # type: ignore[method-assign]

    summary = run_walk(target, settings=settings, provider=provider, keep_notes=keep_notes)

    click.echo("")
    click.echo("walk complete:")
    click.echo(
        json.dumps(
            {
                "files_in_scope": summary.files_in_scope,
                "extraction_notes_written": summary.extraction_notes_written,
                "extraction_failures": summary.extraction_failures,
                "primary_sections_written": summary.primary_sections_written,
                "primary_sections_empty": summary.primary_sections_empty,
                "derivative_sections_written": summary.derivative_sections_written,
                "derivative_sections_empty": summary.derivative_sections_empty,
                "duration_seconds": (summary.finished_at - summary.started_at).total_seconds(),
            },
            indent=2,
        )
    )


@cli.command(help="Print the resolved configuration for a target repository.")
@click.option(
    "--target",
    "-t",
    type=click.Path(file_okay=False, exists=True, path_type=Path),
    default=Path.cwd(),
    show_default="cwd",
)
def config(target: Path) -> None:
    settings = load_settings(target)
    click.echo(json.dumps(settings.model_dump(), indent=2))


def main() -> None:  # entry point referenced from pyproject.toml
    cli(prog_name="wikifi")


if __name__ == "__main__":
    main()
