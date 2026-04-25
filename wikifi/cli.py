from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from wikifi import __version__
from wikifi.orchestrator import explain_error, init_workspace, walk


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            wiki_dir = init_workspace(Path(args.path), force_config=args.force)
            print(f"Initialized wikifi workspace at {wiki_dir}")
            return 0
        if args.command == "walk":
            result = walk(Path(args.path))
            if args.json:
                print(json.dumps(result.as_summary(), indent=2, sort_keys=True))
            else:
                print(
                    "wikifi walk completed: "
                    f"{len(result.notes)} notes, "
                    f"{result.aggregation_stats.successful_writes} primary sections, "
                    f"{result.derivative_stats.successful_writes} derivative sections."
                )
                print(f"Summary: {result.layout.summary_markdown}")
            return 0
        if args.command == "version":
            print(__version__)
            return 0
    except Exception as exc:  # noqa: BLE001
        code, message = explain_error(exc)
        print(message, file=sys.stderr)
        return code

    parser.print_help()
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wikifi",
        description="Walk a codebase and produce a technology-agnostic wiki of system intent.",
    )
    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser("init", help="Create the .wikifi workspace layout.")
    init_parser.add_argument("path", nargs="?", default=".", help="Target repository root.")
    init_parser.add_argument("--force", action="store_true", help="Rewrite .wikifi/config.toml and .wikifi/.gitignore.")

    walk_parser = subparsers.add_parser(
        "walk", help="Run the full introspection/extraction/aggregation/derivation walk."
    )
    walk_parser.add_argument("path", nargs="?", default=".", help="Target repository root.")
    walk_parser.add_argument("--json", action="store_true", help="Print the execution summary as JSON.")

    subparsers.add_parser("version", help="Print the wikifi version.")
    return parser
