"""Fingerprint tests."""

from __future__ import annotations

from pathlib import Path

from wikifi.fingerprint import FINGERPRINT_LENGTH, hash_bytes, hash_file, hash_text


def test_hash_text_is_stable_and_short():
    a = hash_text("hello world")
    b = hash_text("hello world")
    assert a == b
    assert len(a) == FINGERPRINT_LENGTH
    assert all(c in "0123456789abcdef" for c in a)


def test_hash_text_diverges_on_change():
    assert hash_text("hello") != hash_text("hello!")


def test_hash_bytes_handles_arbitrary_bytes():
    assert hash_bytes(b"\x00\x01\x02") != hash_bytes(b"\x00\x01\x03")


def test_hash_file_reads_bytes_from_disk(tmp_path: Path):
    target = tmp_path / "file.txt"
    target.write_bytes(b"contents")
    assert hash_file(target) == hash_bytes(b"contents")
