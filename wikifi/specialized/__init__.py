"""Type-aware extractors for high-signal source artifacts.

Each module in this package implements one or more parsers that consume
a file's text and emit structured findings in the same shape the LLM
extractor produces. Import from the concrete module — never from this
``__init__.py`` — per the project's no-re-exports rule:

- :mod:`wikifi.specialized.models` — finding/result dataclasses
- :mod:`wikifi.specialized.dispatch` — :func:`select` for kind → extractor
- :mod:`wikifi.specialized.sql` / ``openapi`` / ``protobuf`` / ``graphql`` —
  the per-format extractors
"""
