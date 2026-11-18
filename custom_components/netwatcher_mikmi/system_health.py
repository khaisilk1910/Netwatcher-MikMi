"""Aggregate system health; never reveals client identifiers."""
from __future__ import annotations

from homeassistant.core import HomeAssistant

from .const import DOMAIN


async def async_get_system_health_info(hass: HomeAssistant) -> dict:
    entries = hass.data.get(DOMAIN, {})
    return {
        "configured_entries": len(entries),
        "monitored_devices": sum(len(runtime.coordinator.inventory.devices) for runtime in entries.values()),
        "mikrotik_healthy": sum(runtime.coordinator.source_health["mikrotik"]["ok"] for runtime in entries.values()),
        "mikrotik_hardware_healthy": sum(bool(runtime.hardware.last_update_success) for runtime in entries.values()),
        "mikrotik_logs_healthy": sum(runtime.coordinator.source_health["router_logs"]["ok"] for runtime in entries.values()),
    }
