"""Bounded, read-only Xiaomi LAN-client collection (no HA dependency).

The library's async_get_status() walks 20+ unrelated endpoints, so it must
not be in the presence polling path. async_get_clients() collects one client
list plus two best-effort telemetry endpoints, and handles token refresh.
"""
from __future__ import annotations

import asyncio
from typing import Any


async def fetch_xiaomi_clients(client: Any, host: str, timeout: int = 20) -> list[dict[str, Any]]:
    async with asyncio.timeout(timeout):
        clients = await client.async_get_clients()
        if not clients:
            # The upstream library can treat a LuCI error payload as an empty
            # client list. Check once so failures do not mass-mark devices away.
            payload = await client.async_luci_request("api/misystem/devicelist")
            if (not isinstance(payload, dict)
                    or not isinstance(payload.get("list"), list)
                    or payload.get("code", 0) not in (0, "0")):
                raise ValueError("Xiaomi device-list API returned no valid snapshot")
    # The client method provides ClientDevice records with online/band/signal.
    # Do not pretend this is a directly attached AP when routers aggregate mesh.
    return [{
        "mac": getattr(c, "mac", ""),
        "ip": getattr(c, "ip", None),
        "name": getattr(c, "name", None),
        "online": getattr(c, "online", False),
        "band": getattr(c, "band", None),
        "signal": getattr(c, "signal", None),
        "source_host": host,
        "source_name": host,
    } for c in clients]
