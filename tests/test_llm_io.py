from __future__ import annotations

import json

import pytest
from pydantic import BaseModel

from wikifi.llm_io import _extract_json_object, request_structured, request_text, strip_top_level_heading
from wikifi.providers.base import ProviderError
from wikifi.providers.fake import FakeProvider


class _Sample(BaseModel):
    name: str
    count: int


def test_extract_json_object_strips_fence():
    raw = '```json\n{"a": 1}\n```'
    assert json.loads(_extract_json_object(raw)) == {"a": 1}


def test_extract_json_object_finds_embedded():
    raw = 'thinking text {"a": 2} trailing'
    assert json.loads(_extract_json_object(raw)) == {"a": 2}


def test_request_structured_validates():
    provider = FakeProvider(responses=[json.dumps({"name": "x", "count": 5})])
    out = request_structured(provider, prompt="p", system=None, model_cls=_Sample, think="high")
    assert isinstance(out, _Sample)
    assert out.count == 5


def test_request_structured_rejects_invalid():
    provider = FakeProvider(responses=[json.dumps({"name": "x"})])
    with pytest.raises(ProviderError):
        request_structured(provider, prompt="p", system=None, model_cls=_Sample)


def test_request_structured_handles_thinking_chatter():
    provider = FakeProvider(responses=["The answer is " + json.dumps({"name": "y", "count": 1})])
    out = request_structured(provider, prompt="p", system=None, model_cls=_Sample)
    assert out.name == "y"


def test_request_text_returns_stripped():
    provider = FakeProvider(responses=["  hello  \n"])
    assert request_text(provider, prompt="p", system=None) == "hello"


def test_strip_top_level_heading_demotes_h1():
    md = "# Title\nbody\n"
    out = strip_top_level_heading(md)
    assert out.startswith("## Title")


def test_strip_top_level_heading_preserves_h2():
    md = "## Title\nbody\n"
    assert strip_top_level_heading(md).startswith("## Title")
