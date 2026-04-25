import asyncio
import typer
from pathlib import Path
from loguru import logger
from wikifi.orchestrator import Orchestrator

app = typer.Typer(name="wikifi", help="Walk a codebase and produce a technology-agnostic wiki.")

@app.command()
def init(target: str = "."):
    """
    Initialize a .wikifi workspace in the target directory.
    """
    async def _run():
        orchestrator = Orchestrator(target)
        await orchestrator.init_workspace()
        typer.echo(f"Initialized .wikifi workspace in {Path(target).resolve()}")

    asyncio.run(_run())

@app.command()
def walk(target: str = "."):
    """
    Walk the target codebase and generate the wiki.
    """
    async def _run():
        orchestrator = Orchestrator(target)
        summary = await orchestrator.walk()
        if summary.success:
            typer.echo("Wiki generation successful!")
        else:
            typer.echo(f"Wiki generation failed: {summary.message}")
            raise typer.Exit(code=1)

    asyncio.run(_run())

if __name__ == "__main__":
    app()
