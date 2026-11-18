"""Privacy-preserving diagnostics; excludes hosts, IPs, MACs, comments and secrets."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_POLL_INTERVAL, DEFAULT_POLL, VERSION, CONF_ZALO_BOT_ENABLED, CONF_ZALO_NOTIFY_DYNAMIC, CONF_ZALO_NOTIFY_ONLINE, CONF_ZALO_NOTIFY_OFFLINE, CONF_LOG_ENABLED, CONF_WAN_ALERTS, CONF_ZALO_NOTIFY_WAN


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict:
    coord = entry.runtime_data.coordinator
    return {
        "integration": "netwatcher_mikmi",
        "version": VERSION,
        "routeros_source": {
            "ok": coord.source_health["mikrotik"]["ok"],
            "error_category": coord.source_health["mikrotik"]["error"],
        },
        "statistics": coord.inventory.statistics(),
        "hardware_source": {"ok": bool(entry.runtime_data.hardware.last_update_success),
                            "error_category": entry.runtime_data.hardware.source_error},
        "hardware_alerts_enabled": bool(entry.options.get("hardware_alerts_enabled", False)),
        "netwatch_enabled": bool(entry.options.get("netwatch_read_enabled", False)),
        "netwatch_source_ok": bool(coord.source_health["netwatch"]["ok"]),
        "baseline_complete": coord.inventory.baseline_complete,
        "poll_interval": entry.options.get(CONF_POLL_INTERVAL, DEFAULT_POLL),
        "zalo_enabled": bool(entry.options.get(CONF_ZALO_BOT_ENABLED, False)),
        "zalo_notify_dynamic": bool(entry.options.get(CONF_ZALO_NOTIFY_DYNAMIC, True)),
        "zalo_notify_online": bool(entry.options.get(CONF_ZALO_NOTIFY_ONLINE, False)),
        "zalo_notify_offline": bool(entry.options.get(CONF_ZALO_NOTIFY_OFFLINE, False)),
        "zalo_transport": "zalo_bot_personal_service",
        "router_logs_enabled": bool(entry.options.get(CONF_LOG_ENABLED, True)),
        "wan_security_notifications_enabled": bool(entry.options.get(CONF_WAN_ALERTS, False)),
        "zalo_notify_wan_security": bool(entry.options.get(CONF_ZALO_NOTIFY_WAN, False)),
        "router_logs_source": {"ok": coord.source_health["router_logs"]["ok"],
                               "error_category": coord.source_health["router_logs"]["error"]},
        "note": "No credentials, MACs, client IPs, comments, tokens or host IPs in this report",
    }
