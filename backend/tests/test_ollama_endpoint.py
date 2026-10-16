"""Ollama must be reachable both on a host and across a Compose network."""
import json

import httpx
import pytest

from backend.analyzer.llm_client import _call_ollama


@pytest.mark.asyncio
@pytest.mark.parametrize("base,expected", [
    (None, "http://localhost:11434/api/generate"),
    ("http://ollama:11434/", "http://ollama:11434/api/generate"),
])
async def test_ollama_uses_configured_endpoint(monkeypatch, base, expected):
    if base is None:
        monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    else:
        monkeypatch.setenv("OLLAMA_BASE_URL", base)
    real_client = httpx.AsyncClient

    def handler(request):
        assert str(request.url) == expected
        assert json.loads(request.content)["model"] == "qwen2.5:7b"
        return httpx.Response(200, json={"response": "Ready", "eval_count": 1})

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: real_client(
        transport=httpx.MockTransport(handler), **kwargs))
    result = await _call_ollama("Test", "You are helpful.", "qwen2.5:7b", 32)
    assert result["text"] == "Ready"
