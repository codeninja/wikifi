"""Tests for the chat REPL and ChatSession."""

from __future__ import annotations

from pathlib import Path

import pytest
from rich.console import Console

from wikifi.chat import (
    ChatSession,
    build_system_prompt,
    load_wiki_sections,
    run_repl,
)
from wikifi.wiki import WikiLayout, initialize


def _populate(layout: WikiLayout, *, sections: dict[str, str]) -> None:
    for sid, body in sections.items():
        layout.section_path(sid).write_text(f"# {sid}\n\n{body}\n")


def test_load_wiki_sections_skips_empty_and_unpopulated(tmp_path: Path):
    layout = WikiLayout(root=tmp_path)
    initialize(layout, model="m", provider="ollama", ollama_host="http://h")

    _populate(layout, sections={"intent": "real intent body"})
    layout.section_path("domains").write_text("")  # empty file

    loaded = load_wiki_sections(layout)
    ids = [entry.section.id for entry in loaded]
    assert "intent" in ids
    assert "domains" not in ids
    assert "capabilities" not in ids  # still placeholder body


def test_load_wiki_sections_raises_when_wiki_missing(tmp_path: Path):
    layout = WikiLayout(root=tmp_path)
    with pytest.raises(FileNotFoundError):
        load_wiki_sections(layout)


def test_build_system_prompt_includes_each_loaded_body(tmp_path: Path):
    layout = WikiLayout(root=tmp_path)
    initialize(layout, model="m", provider="ollama", ollama_host="http://h")
    _populate(layout, sections={"intent": "alpha-body", "capabilities": "beta-body"})

    loaded = load_wiki_sections(layout)
    prompt = build_system_prompt(loaded)

    assert "Wiki Context" in prompt
    assert "alpha-body" in prompt
    assert "beta-body" in prompt


def test_chat_session_carries_history(mock_provider_factory):
    provider = mock_provider_factory(chat_responses=["hi there", "second turn"])
    session = ChatSession(provider=provider, system_prompt="SYS")

    assert session.send("hello") == "hi there"
    assert session.send("more") == "second turn"

    assert len(session.history) == 4
    assert session.history[0] == {"role": "user", "content": "hello"}
    assert session.history[1] == {"role": "assistant", "content": "hi there"}
    assert session.history[2] == {"role": "user", "content": "more"}
    assert session.history[3] == {"role": "assistant", "content": "second turn"}

    # Provider received the full running history on the second call.
    assert len(provider.chat_calls[0][1]) == 1
    assert len(provider.chat_calls[1][1]) == 3
    assert provider.chat_calls[0][0] == "SYS"


def test_chat_session_reset_clears_history(mock_provider_factory):
    provider = mock_provider_factory(chat_responses=["a", "b"])
    session = ChatSession(provider=provider, system_prompt="SYS")
    session.send("first")
    session.reset()
    assert session.history == []
    session.send("second")
    # After reset, the provider sees only the new turn — no carryover.
    assert len(provider.chat_calls[1][1]) == 1


def test_run_repl_handles_user_turn_then_exit(tmp_path: Path, mock_provider_factory):
    layout = WikiLayout(root=tmp_path)
    initialize(layout, model="m", provider="ollama", ollama_host="http://h")
    _populate(layout, sections={"intent": "knows the system"})

    provider = mock_provider_factory(chat_responses=["the wiki says X"])
    inputs = iter(["what does it do?", "/exit"])
    console = Console(record=True, force_terminal=False)

    run_repl(
        layout=layout,
        provider=provider,
        console=console,
        input_fn=lambda _prompt: next(inputs),
    )

    assert len(provider.chat_calls) == 1
    output = console.export_text()
    assert "the wiki says X" in output


def test_run_repl_reset_command_clears_history(tmp_path: Path, mock_provider_factory):
    layout = WikiLayout(root=tmp_path)
    initialize(layout, model="m", provider="ollama", ollama_host="http://h")
    _populate(layout, sections={"intent": "body"})

    provider = mock_provider_factory(chat_responses=["one", "two"])
    inputs = iter(["first", "/reset", "second", "/exit"])
    console = Console(record=True, force_terminal=False)

    run_repl(
        layout=layout,
        provider=provider,
        console=console,
        input_fn=lambda _prompt: next(inputs),
    )

    # Both calls saw exactly one user message — reset truncated history between.
    assert len(provider.chat_calls) == 2
    assert len(provider.chat_calls[0][1]) == 1
    assert len(provider.chat_calls[1][1]) == 1


def test_run_repl_warns_when_no_sections_populated(tmp_path: Path, mock_provider_factory):
    layout = WikiLayout(root=tmp_path)
    initialize(layout, model="m", provider="ollama", ollama_host="http://h")

    provider = mock_provider_factory()
    console = Console(record=True, force_terminal=False)

    run_repl(
        layout=layout,
        provider=provider,
        console=console,
        input_fn=lambda _p: "/exit",
    )

    output = console.export_text()
    assert "No populated sections" in output
    assert provider.chat_calls == []


def test_run_repl_keyboard_interrupt_exits_cleanly(tmp_path: Path, mock_provider_factory):
    layout = WikiLayout(root=tmp_path)
    initialize(layout, model="m", provider="ollama", ollama_host="http://h")
    _populate(layout, sections={"intent": "body"})

    provider = mock_provider_factory()
    console = Console(record=True, force_terminal=False)

    def raise_eof(_prompt: str) -> str:
        raise EOFError

    run_repl(layout=layout, provider=provider, console=console, input_fn=raise_eof)
    assert provider.chat_calls == []


def test_run_repl_provider_failure_does_not_crash(tmp_path: Path):
    layout = WikiLayout(root=tmp_path)
    initialize(layout, model="m", provider="ollama", ollama_host="http://h")
    _populate(layout, sections={"intent": "body"})

    class _Boom:
        name = "boom"
        model = "boom-model"

        def complete_json(self, **_kw):  # pragma: no cover - unused
            raise NotImplementedError

        def complete_text(self, **_kw):  # pragma: no cover - unused
            raise NotImplementedError

        def chat(self, **_kw):
            raise RuntimeError("provider down")

    inputs = iter(["question?", "/exit"])
    console = Console(record=True, force_terminal=False)

    run_repl(
        layout=layout,
        provider=_Boom(),
        console=console,
        input_fn=lambda _p: next(inputs),
    )

    output = console.export_text()
    assert "provider down" in output


def test_run_repl_help_and_sections_commands(tmp_path: Path, mock_provider_factory):
    layout = WikiLayout(root=tmp_path)
    initialize(layout, model="m", provider="ollama", ollama_host="http://h")
    _populate(layout, sections={"intent": "body"})

    provider = mock_provider_factory()
    inputs = iter(["/help", "/sections", "/exit"])
    console = Console(record=True, force_terminal=False)

    run_repl(
        layout=layout,
        provider=provider,
        console=console,
        input_fn=lambda _p: next(inputs),
    )

    output = console.export_text()
    assert "loaded sections" in output
    assert "/reset" in output
    assert provider.chat_calls == []
