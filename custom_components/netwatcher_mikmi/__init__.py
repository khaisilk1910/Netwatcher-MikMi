"""Netwatcher MikMi custom integration. LAN-only collectors, local inventory."""
from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback, CoreState, EVENT_HOMEASSISTANT_STARTED
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .coordinator import MikMiCoordinator
from .frontend import register_card
from .inventory import Inventory
from .log_monitor import RouterLogMonitor

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor", "device_tracker"]


@dataclass
class RuntimeData:
    coordinator: MikMiCoordinator
    store: Store
    log_store: Store


@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/inventory",
    vol.Optional("entry_id", default=""): str,
    vol.Optional("status", default="all"): vol.In(["all", "online", "offline", "unknown", "dynamic", "unapproved"]),
    vol.Optional("search", default=""): str,
    vol.Optional("offset", default=0): vol.All(vol.Coerce(int), vol.Range(min=0, max=100000)),
    vol.Optional("limit", default=100): vol.All(vol.Coerce(int), vol.Range(min=1, max=200)),
})
@callback
def ws_inventory(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    if not connection.user.is_admin:
        connection.send_error(msg["id"], "unauthorized", "Admin access required")
        return
    entries = hass.data.get(DOMAIN, {})
    runtime = entries.get(msg["entry_id"]) if msg["entry_id"] else next(iter(entries.values()), None)
    if runtime is None:
        connection.send_error(msg["id"], "not_found", "Netwatcher entry not found")
        return
    coord = runtime.coordinator
    records, count = coord.inventory.rows(msg["status"], msg["search"], msg["offset"], msg["limit"])
    connection.send_result(msg["id"], {
        "devices": records, "count": count, "statistics": coord.inventory.statistics(),
        "source_health": coord.source_health, "entry_id": coord.entry.entry_id,
        "baseline_complete": coord.inventory.baseline_complete,
    })


@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/approve",
    vol.Required("entry_id"): str,
    vol.Required("mac"): str,
    vol.Required("approved"): bool,
})
@callback
def ws_approve(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    from .security import mac_normalize
    if not connection.user.is_admin:
        connection.send_error(msg["id"], "unauthorized", "Admin access required")
        return
    runtime = hass.data.get(DOMAIN, {}).get(msg["entry_id"])
    mac = mac_normalize(msg["mac"])
    if not runtime or not mac or mac not in runtime.coordinator.inventory.devices:
        connection.send_error(msg["id"], "not_found", "Device not found")
        return
    runtime.coordinator.inventory.devices[mac]["approved"] = msg["approved"]
    runtime.store.async_delay_save(runtime.coordinator.inventory.dump, 5)
    runtime.coordinator.async_update_listeners()
    connection.send_result(msg["id"], {"ok": True})


@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/test_zalo",
    vol.Required("entry_id"): str,
})
@websocket_api.async_response
async def ws_test_zalo(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Explicit, admin-only test; payload and token never come from browser."""
    if not connection.user.is_admin:
        connection.send_error(msg["id"], "unauthorized", "Admin access required")
        return
    runtime = hass.data.get(DOMAIN, {}).get(msg["entry_id"])
    if runtime is None:
        connection.send_error(msg["id"], "not_found", "Netwatcher entry not found")
        return
    result = await runtime.coordinator.zalo.send_test()
    connection.send_result(msg["id"], result)



@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/router_logs",
    vol.Optional("entry_id", default=""): str,
    vol.Optional("category", default="all"): vol.In(["all", "security", "warning"]),
    vol.Optional("search", default=""): str,
    vol.Optional("offset", default=0): vol.All(vol.Coerce(int), vol.Range(min=0, max=10000)),
    vol.Optional("limit", default=50): vol.All(vol.Coerce(int), vol.Range(min=1, max=100)),
})
@callback
def ws_router_logs(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Admin-only log viewer; no access for guest/non-admin dashboards."""
    if not connection.user.is_admin:
        connection.send_error(msg["id"], "unauthorized", "Admin access required")
        return
    entries = hass.data.get(DOMAIN, {})
    runtime = entries.get(msg["entry_id"]) if msg["entry_id"] else next(iter(entries.values()), None)
    if runtime is None:
        connection.send_error(msg["id"], "not_found", "Netwatcher entry not found")
        return
    monitor = runtime.coordinator.log_monitor
    rows, count = monitor.rows(category=msg["category"], search=msg["search"],
                               offset=msg["offset"], limit=msg["limit"])
    connection.send_result(msg["id"], {
        "logs": rows, "count": count,
        "enabled": bool(runtime.coordinator._settings.get("enable_router_logs", True)),
        "source_health": runtime.coordinator.source_health["router_logs"],
        "entry_id": runtime.coordinator.entry.entry_id,
        "baselined": monitor.baselined,
    })

async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    hass.data.setdefault(DOMAIN, {})
    websocket_api.async_register_command(hass, ws_inventory)
    websocket_api.async_register_command(hass, ws_approve)
    websocket_api.async_register_command(hass, ws_test_zalo)
    websocket_api.async_register_command(hass, ws_router_logs)

    async def setup_frontend(_event=None):
        try:
            await register_card(hass)
        except Exception:  # Frontend failure must not break network monitoring.
            _LOGGER.warning("Netwatcher Lovelace card registration failed; see README manual resource", exc_info=True)

    if hass.state == CoreState.running:
        hass.async_create_background_task(setup_frontend(), f"{DOMAIN} frontend")
    else:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, setup_frontend)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Upgrade from v0.2.0 OA mode: never reuse official-account credentials
    # or silently begin personal-account delivery. Purge old OA secrets.
    legacy_oa = {"zalo_enabled", "zalo_access_token", "zalo_user_ids",
                 "zalo_group_ids", "zalo_auto_refresh", "zalo_refresh_token",
                 "zalo_app_id", "zalo_secret_key"}
    if legacy_oa.intersection(entry.options):
        clean_options = {k: v for k, v in entry.options.items() if k not in legacy_oa}
        hass.config_entries.async_update_entry(entry, options=clean_options)
        _LOGGER.info("Legacy Zalo OA settings discarded; personal Zalo Bot remains opt-in")
    store = Store(hass, 1, f"{DOMAIN}_{entry.entry_id}")
    previous = await store.async_load()
    inventory = Inventory(previous)
    log_store = Store(hass, 1, f"{DOMAIN}_logs_{entry.entry_id}")
    previous_logs = await log_store.async_load()
    log_monitor = RouterLogMonitor(previous_logs)
    coord = MikMiCoordinator(hass, entry, inventory, store, log_monitor, log_store)
    runtime = RuntimeData(coordinator=coord, store=store, log_store=log_store)
    entry.runtime_data = runtime
    hass.data[DOMAIN][entry.entry_id] = runtime
    entry.async_on_unload(entry.add_update_listener(_options_updated))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # Essential: slow/unreachable router MUST NOT delay Home Assistant startup.
    entry.async_create_background_task(hass, coord.async_refresh(), f"{DOMAIN} initial polling")
    return True


async def _options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    result = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if result:
        runtime: RuntimeData = entry.runtime_data
        await runtime.coordinator.async_shutdown()
        await runtime.store.async_save(runtime.coordinator.inventory.dump())
        await runtime.log_store.async_save(runtime.coordinator.log_monitor.dump())
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return result
