"""Fake VLM for offline tests (recorded responses)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hylyre.drivers.base import VlmClientBase


@dataclass
class FakeVlmClient(VlmClientBase):
    """Pops scripted dicts per ``vision_json`` call; records calls."""

    responses: list[dict[str, Any]]
    calls: list[tuple[str, str, int]] = field(default_factory=list)

    async def vision_json(
        self,
        *,
        instruction: str,
        screenshot_png: bytes,
        response_schema: str,
    ) -> dict[str, Any]:
        self.calls.append((instruction, response_schema, len(screenshot_png)))
        if not self.responses:
            raise RuntimeError("FakeVlmClient: no canned responses left")
        return self.responses.pop(0)
