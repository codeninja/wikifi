"""Logging configuration for wikifi CLI runs."""

from __future__ import annotations

import logging

from rich.logging import RichHandler


def configure(verbosity: int = 1) -> None:
    """Configure root logging with a Rich handler.

    verbosity: 0 = WARNING, 1 = INFO (default), 2+ = DEBUG.
    """
    level = logging.WARNING
    if verbosity == 1:
        level = logging.INFO
    elif verbosity >= 2:
        level = logging.DEBUG

    handler = RichHandler(
        rich_tracebacks=True,
        markup=False,
        show_path=verbosity >= 2,
        show_time=True,
    )
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[handler],
        force=True,
    )
    # Tame noisy 3rd-party loggers.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
