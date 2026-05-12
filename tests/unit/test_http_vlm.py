"""respx: HttpVlmClient parses OpenAI-style response."""

from __future__ import annotations

import pytest
import respx
from httpx import Response

from hylyre.vlm.http_vlm import HttpVlmClient

URL = "https://api.example.com/v1/chat/completions"


@pytest.mark.asyncio
@respx.mock
async def test_http_vlm_parses_content() -> None:
    respx.post(URL).mock(
        return_value=Response(
            200,
            json={
                "choices": [
                    {"message": {"content": '{"touch": {"x": 3, "y": 4}}'}}
                ]
            },
        )
    )
    client = HttpVlmClient(endpoint=URL)
    out = await client.vision_json(
        instruction="tap",
        screenshot_png=b"\x89PNG\r\n\x1a\n",
        response_schema="tap",
    )
    assert out == {"touch": {"x": 3, "y": 4}}


def test_http_vlm_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HYLYRE_VLM_ENDPOINT", raising=False)
    assert HttpVlmClient.from_env() is None
    monkeypatch.setenv("HYLYRE_VLM_ENDPOINT", "https://x/post")
    c = HttpVlmClient.from_env()
    assert c is not None
    assert c._endpoint == "https://x/post"
