"""Stable content fingerprints for files and synthesized text.

Used by three subsystems:

- :mod:`wikifi.cache` keys cached extraction findings by ``hash(file_bytes)``
  and cached aggregations by ``hash(notes_payload)``.
- :mod:`wikifi.evidence` cites source files by ``(path, fingerprint, lines)``
  so a migration team can verify the wiki claim survives a re-walk.
- :mod:`wikifi.repograph` records each file's fingerprint alongside its
  import edges so cross-file context invalidates correctly when source
  changes.

Fingerprints are short hex prefixes of SHA-256: enough entropy to
distinguish every file in any realistic repository (~10 trillion files
before a 50% collision chance with a 12-char prefix), and short enough
to render comfortably inline in citations.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

# Twelve hex chars = 48 bits of entropy. Using a prefix (rather than the
# full digest) keeps citations readable while leaving margin against
# collisions on any realistic codebase.
FINGERPRINT_LENGTH = 12


def hash_text(text: str) -> str:
    """Return a stable short fingerprint for a string."""
    digest = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()
    return digest[:FINGERPRINT_LENGTH]


def hash_bytes(data: bytes) -> str:
    """Return a stable short fingerprint for raw bytes."""
    digest = hashlib.sha256(data).hexdigest()
    return digest[:FINGERPRINT_LENGTH]


def hash_file(path: Path) -> str:
    """Return the fingerprint of the file at ``path``.

    Reads the file as bytes (not text) so the same fingerprint is produced
    regardless of how the cache or extractor later decodes it.
    """
    return hash_bytes(path.read_bytes())
