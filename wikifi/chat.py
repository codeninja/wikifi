"""Interactive chat REPL grounded in a target project's ``.wikifi/`` content.

The session loads every populated section markdown file and bundles them into
a single system prompt. The user then carries on a multi-turn conversation
with the configured LLM provider, with all history preserved across turns
inside the session.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from wikifi.providers.base import ChatMessage, LLMProvider
from wikifi.sections import SECTIONS, Section
from wikifi.wiki import WikiLayout

log = logging.getLogger("wikifi.chat")

CHAT_SYSTEM_PROMPT = (
    "You are wikifi-chat, an assistant for exploring a technology-agnostic wiki "
    "extracted from a codebase. The wiki sections that follow describe the system's "
    "domains, intent, capabilities, entities, integrations, cross-cutting concerns, "
    "hard specifications, and derived personas, user stories, and diagrams.\n\n"
    "Ground every answer in this material. When the wiki does not cover something, "
    "say so plainly rather than inventing detail. Cite section names when helpful."
)

EXIT_COMMANDS = frozenset({"/exit", "/quit", "/q"})
RESET_COMMAND = "/reset"
SECTIONS_COMMAND = "/sections"
HELP_COMMAND = "/help"


@dataclass
class LoadedSection:
    section: Section
    body: str


@dataclass
class ChatSession:
    """Multi-turn chat backed by a provider and a frozen wiki context."""

    provider: LLMProvider
    system_prompt: str
    history: list[ChatMessage] = field(default_factory=list)

    def send(self, user_message: str) -> str:
        self.history.append({"role": "user", "content": user_message})
        reply = self.provider.chat(system=self.system_prompt, messages=self.history)
        self.history.append({"role": "assistant", "content": reply})
        return reply

    def reset(self) -> None:
        self.history.clear()


def load_wiki_sections(layout: WikiLayout) -> list[LoadedSection]:
    """Read every section file under ``.wikifi/`` that exists and is non-empty.

    Sections that haven't been populated yet (still carrying the ``init``
    placeholder body) are filtered out so they don't dilute the context.
    """
    if not layout.wiki_dir.exists():
        raise FileNotFoundError(f"No .wikifi/ directory at {layout.root}. Run `wikifi init` and `wikifi walk` first.")

    loaded: list[LoadedSection] = []
    for section in SECTIONS:
        path = layout.section_path(section)
        if not path.exists():
            continue
        body = path.read_text(encoding="utf-8").strip()
        if not body or _looks_unpopulated(body):
            continue
        loaded.append(LoadedSection(section=section, body=body))
    return loaded


def build_system_prompt(loaded: Iterable[LoadedSection]) -> str:
    """Bundle loaded section bodies into a single system prompt."""
    parts = [CHAT_SYSTEM_PROMPT, "", "=== Wiki Context ==="]
    for entry in loaded:
        parts.extend(["", entry.body])
    return "\n".join(parts).strip() + "\n"


def run_repl(
    *,
    layout: WikiLayout,
    provider: LLMProvider,
    console: Console,
    input_fn: Callable[[str], str] | None = None,
) -> None:
    """Drive the interactive REPL until the user exits."""
    loaded = load_wiki_sections(layout)
    if not loaded:
        console.print(
            "[yellow]No populated sections found in .wikifi/. "
            "Run `wikifi walk` first so chat has material to ground in.[/yellow]"
        )
        return

    session = ChatSession(provider=provider, system_prompt=build_system_prompt(loaded))
    prompt = input_fn or console.input

    _print_banner(console=console, layout=layout, provider=provider, loaded=loaded)

    while True:
        try:
            line = prompt("[bold cyan]you›[/bold cyan] ")
        except (EOFError, KeyboardInterrupt):
            console.print()
            break

        line = line.strip()
        if not line:
            continue
        if line in EXIT_COMMANDS:
            break
        if line == HELP_COMMAND:
            _print_help(console)
            continue
        if line == RESET_COMMAND:
            session.reset()
            console.print("[dim]conversation reset; wiki context retained.[/dim]")
            continue
        if line == SECTIONS_COMMAND:
            _print_sections(console, loaded)
            continue

        try:
            reply = session.send(line)
        except Exception as exc:  # provider failures shouldn't kill the REPL
            log.exception("chat turn failed")
            console.print(f"[red]error from provider:[/red] {exc}")
            continue

        console.print(Panel(Markdown(reply), title="wikifi", border_style="green"))


def _looks_unpopulated(body: str) -> bool:
    return "_Not yet populated. Run `wikifi walk`" in body


def _print_banner(
    *,
    console: Console,
    layout: WikiLayout,
    provider: LLMProvider,
    loaded: list[LoadedSection],
) -> None:
    console.print(
        Panel.fit(
            f"[bold]wikifi chat[/bold]\n"
            f"wiki: [cyan]{layout.wiki_dir}[/cyan]\n"
            f"provider: [cyan]{provider.name}[/cyan]  model: [cyan]{provider.model}[/cyan]\n"
            f"sections loaded: [cyan]{len(loaded)}[/cyan]\n\n"
            "Type [bold]/help[/bold] for commands, [bold]/exit[/bold] to quit.",
            title="ready",
        )
    )


def _print_help(console: Console) -> None:
    console.print(
        "[bold]commands[/bold]\n"
        "  /help       show this list\n"
        "  /sections   list loaded wiki sections\n"
        "  /reset      clear conversation history (wiki context kept)\n"
        "  /exit       leave the chat (also Ctrl+D)"
    )


def _print_sections(console: Console, loaded: list[LoadedSection]) -> None:
    console.print("[bold]loaded sections[/bold]")
    for entry in loaded:
        size = len(entry.body)
        console.print(f"  [cyan]{entry.section.id:<22}[/cyan] {entry.section.title}  ({size} chars)")
