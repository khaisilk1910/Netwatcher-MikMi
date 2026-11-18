"""Netwatcher MikMi custom integration. LAN-only collectors, local inventory."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback, CoreState, EVENT_HOMEASSISTANT_STARTED
from homeassistant.helpers.storage import Store
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_time_interval

from .const import (DOMAIN, CONF_LOG_ENABLED, CONF_LOG_INTERVAL, DEFAULT_LOG_INTERVAL)
from .coordinator import MikMiCoordinator
from .hardware_coordinator import MikMiHardwareCoordinator
from .frontend import register_card
from .inventory import Inventory
from .log_monitor import RouterLogMonitor

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor", "device_tracker"]
COLUMN_IDS = ("device", "ip", "state", "port", "dhcp", "approved")


@dataclass
class RuntimeData:
    coordinator: MikMiCoordinator
    store: Store
    log_store: Store
    hardware: MikMiHardwareCoordinator
    hardware_store: Store
    preferences_store: Store
    column_preferences: dict[str, list[str]]


@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/inventory",
    vol.Optional("entry_id", default=""): str,
    vol.Optional("status", default="all"): vol.In(["all", "online", "offline", "dynamic", "unapproved"]),
    vol.Optional("search", default=""): str,
    vol.Optional("sort_by", default="recent"): vol.In(["recent", "name", "ip"]),
    vol.Optional("sort_dir", default="desc"): vol.In(["asc", "desc"]),
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
    records, count = coord.inventory.rows(msg["status"], msg["search"], msg["offset"], msg["limit"],
                                           msg["sort_by"], msg["sort_dir"])
    connection.send_result(msg["id"], {
        "devices": records, "count": count, "statistics": coord.inventory.statistics(),
        "source_health": coord.source_health, "entry_id": coord.entry.entry_id,
        "baseline_complete": coord.inventory.baseline_complete,
        "column_preferences": runtime.column_preferences.get(connection.user.id),
        "zalo": coord.zalo.diagnostics(),
        "poll_interval": int(coord._settings.get("poll_interval", 30)),
        "offline_after": int(coord._settings.get("offline_after", 120)),
    })


@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/columns",
    vol.Required("entry_id"): str,
    vol.Required("columns"): vol.All([vol.In(COLUMN_IDS)], vol.Length(min=1, max=len(COLUMN_IDS))),
})
@callback
def ws_columns(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Save column preferences per authenticated HA user (HA Store, not browser)."""
    if not connection.user.is_admin:
        connection.send_error(msg["id"], "unauthorized", "Admin access required")
        return
    runtime = hass.data.get(DOMAIN, {}).get(msg["entry_id"])
    if runtime is None:
        connection.send_error(msg["id"], "not_found", "Netwatcher entry not found")
        return
    columns = list(dict.fromkeys(msg["columns"]))
    if not columns:
        connection.send_error(msg["id"], "invalid", "At least one column is required")
        return
    runtime.column_preferences[connection.user.id] = columns
    runtime.preferences_store.async_delay_save(
        lambda: {"users": runtime.column_preferences}, 2,
    )
    connection.send_result(msg["id"], {"columns": columns})


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


@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/router_hardware",
    vol.Optional("entry_id", default=""): str,
})
@callback
def ws_router_hardware(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Admin-only hardware snapshot; no serial, password, MAC, or target IP."""
    if not connection.user.is_admin:
        connection.send_error(msg["id"], "unauthorized", "Admin access required")
        return
    entries = hass.data.get(DOMAIN, {})
    runtime = entries.get(msg["entry_id"]) if msg["entry_id"] else next(iter(entries.values()), None)
    if runtime is None:
        connection.send_error(msg["id"], "not_found", "Netwatcher entry not found")
        return
    hardware = runtime.hardware
    data = hardware.data or {}
    connection.send_result(msg["id"], {
        "entry_id": hardware.entry.entry_id,
        "available": bool(hardware.last_update_success and data),
        "source_error": hardware.source_error,
        "last_success": hardware.last_success,
        "readings": data.get("readings", {}),
        "board": data.get("board", {}),
        "sensors": data.get("sensors", {}),
        "alerts": data.get("alerts", {}),
        "poll_intervals": data.get("poll_intervals", {}),
        "wan_traffic": runtime.coordinator.wan_traffic,
    })


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    hass.data.setdefault(DOMAIN, {})
    websocket_api.async_register_command(hass, ws_inventory)
    websocket_api.async_register_command(hass, ws_approve)
    websocket_api.async_register_command(hass, ws_columns)
    websocket_api.async_register_command(hass, ws_test_zalo)
    websocket_api.async_register_command(hass, ws_router_logs)
    websocket_api.async_register_command(hass, ws_router_hardware)

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
    # Purge retired collector credentials from stored configuration on upgrade.
    obsolete = {"xiaomi_hosts", "xiaomi_password", "acknowledge_xiaomi_http_risk", "verified_direct_ap_hosts",
                "netwatch_read_enabled", "netwatch_poll_interval"}
    clean_data = {k: v for k, v in entry.data.items() if k not in obsolete}
    clean_options = {k: v for k, v in entry.options.items() if k not in obsolete}
    if clean_data != dict(entry.data) or clean_options != dict(entry.options):
        hass.config_entries.async_update_entry(entry, data=clean_data, options=clean_options)
        _LOGGER.info("Netwatcher retired credentials and settings cleared from config entry")
    store = Store(hass, 1, f"{DOMAIN}_{entry.entry_id}")
    previous = await store.async_load()
    inventory = Inventory(previous)
    log_store = Store(hass, 1, f"{DOMAIN}_logs_{entry.entry_id}")
    previous_logs = await log_store.async_load()
    log_monitor = RouterLogMonitor(previous_logs)
    coord = MikMiCoordinator(hass, entry, inventory, store, log_monitor, log_store)
    hardware_store = Store(hass, 1, f"{DOMAIN}_hardware_{entry.entry_id}")
    previous_hardware = await hardware_store.async_load()
    preferences_store = Store(hass, 1, f"{DOMAIN}_columns_{entry.entry_id}")
    preferences_data = await preferences_store.async_load() or {}
    column_preferences = {}
    preferences_migrated = False
    for user_id, columns in preferences_data.get("users", {}).items():
        if isinstance(user_id, str) and isinstance(columns, list):
            valid = [col for col in dict.fromkeys(columns) if col in COLUMN_IDS]
            if valid:
                column_preferences[user_id] = valid
            if valid != columns:
                preferences_migrated = True
        else:
            preferences_migrated = True
    # Drop the retired Link key from per-user HA Store without blocking HA startup.
    if preferences_migrated:
        preferences_store.async_delay_save(lambda: {"users": column_preferences}, 2)
    hardware = MikMiHardwareCoordinator(
        hass, entry, coord._router, hardware_store, previous_hardware, coord.zalo
    )
    runtime = RuntimeData(coordinator=coord, store=store, log_store=log_store,
                          hardware=hardware, hardware_store=hardware_store,
                          preferences_store=preferences_store, column_preferences=column_preferences)
    entry.runtime_data = runtime
    hass.data[DOMAIN][entry.entry_id] = runtime
    entry.async_on_unload(entry.add_update_listener(_options_updated))
    # Remove only the two Netwatch entities this integration created previously.
    # No router-side probes, user-created entities or unrelated sensors are touched.
    registry = er.async_get(hass)
    for legacy_key in ("source_netwatch", "netwatch_down"):
        entity_id = registry.async_get_entity_id("sensor", DOMAIN, f"{entry.entry_id}_{legacy_key}")
        if entity_id:
            registry.async_remove(entity_id)
            _LOGGER.info("Removed retired RouterOS monitoring entity: %s", entity_id)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # Essential: slow/unreachable router MUST NOT delay Home Assistant startup.
    entry.async_create_background_task(hass, coord.async_refresh(), f"{DOMAIN} initial polling")
    entry.async_create_background_task(hass, hardware.async_refresh(), f"{DOMAIN} initial hardware polling")
    # Independent log polling is gated to avoid overlapping executor work.
    settings = {**entry.data, **entry.options}
    if settings.get(CONF_LOG_ENABLED, True):
        entry.async_on_unload(async_track_time_interval(
            hass, lambda _now: coord._schedule_logs(),
            timedelta(seconds=max(30, int(settings.get(CONF_LOG_INTERVAL, DEFAULT_LOG_INTERVAL)))),
        ))
    return True


async def _options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    result = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if result:
        runtime: RuntimeData = entry.runtime_data
        await runtime.coordinator.async_shutdown()
        await runtime.hardware.async_shutdown()
        await runtime.hardware_store.async_save(runtime.hardware.alert_engine.dump())
        await runtime.store.async_save(runtime.coordinator.inventory.dump())
        await runtime.log_store.async_save(runtime.coordinator.log_monitor.dump())
        await runtime.preferences_store.async_save({"users": runtime.column_preferences})
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return result
