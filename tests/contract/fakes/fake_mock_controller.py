"""In-memory mock controller for L2/L3 (no Lyrebird)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from hylyre.drivers.base import MockControllerBase


@dataclass
class FakeMockController(MockControllerBase):
    events: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    _started: bool = False
    _flows: list[dict[str, Any]] = field(default_factory=list)
    _active: dict[str, Any] = field(default_factory=dict)

    async def start_local(
        self,
        *,
        data_root: Path | None = None,
        mock_port: int = 9090,
        no_browser: bool = True,
    ) -> None:
        self._started = True
        self.events.append(
            (
                "start_local",
                {
                    "data_root": str(data_root) if data_root else None,
                    "mock_port": mock_port,
                    "no_browser": no_browser,
                },
            )
        )

    async def stop_local(self) -> None:
        self._started = False
        self.events.append(("stop_local", {}))

    async def activate_group(self, group_id: str) -> None:
        self._active[group_id] = {"id": group_id, "name": group_id}
        self.events.append(("activate_group", {"group_id": group_id}))

    async def deactivate_all(self) -> None:
        self._active.clear()
        self.events.append(("deactivate_all", {}))

    async def status(self) -> dict[str, Any]:
        self.events.append(("status", {}))
        return {"code": 1000, "mock.port": 9090, "message": "fake"}

    async def list_activated_groups(self) -> dict[str, Any]:
        self.events.append(("list_activated_groups", {}))
        return dict(self._active)

    async def list_flows(self) -> list[dict[str, Any]]:
        self.events.append(("list_flows", {}))
        return list(self._flows)

    async def export_flows(
        self, output: Path, *, full_detail: bool = False
    ) -> None:
        self.events.append(
            ("export_flows", {"output": str(output), "full_detail": full_detail})
        )

        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(self._flows, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def seed_flow(self, flow: dict[str, Any]) -> None:
        self._flows.append(flow)
