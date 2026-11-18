"""Non-blocking polling and correlation for MikroTik RouterOS."""
from __future__ import annotations

import logging
import time
from datetime import timedelta
from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_LAN_PORTS, CONF_NOTIFY_EXISTING,
    CONF_NOTIFY_PERSISTENT, CONF_OFFLINE_AFTER, CONF_POLL_INTERVAL,
    CONF_ROUTER_FINGERPRINT, CONF_ROUTER_HOST, CONF_ROUTER_PASSWORD,
    CONF_ROUTER_PORT, CONF_ROUTER_USERNAME, DEFAULT_OFFLINE, DEFAULT_POLL, DOMAIN,
    EVENT_CONNECTED, EVENT_DISCONNECTED, EVENT_NEW_DYNAMIC,
    CONF_LOG_ENABLED, CONF_LOG_INTERVAL, CONF_WAN_ALERTS, CONF_ZALO_NOTIFY_WAN,
    CONF_LOGIN_FAIL_THRESHOLD, CONF_FIREWALL_THRESHOLD, DEFAULT_LOG_INTERVAL,
    EVENT_WAN_SECURITY, CONF_NETWATCH_ENABLED, CONF_NETWATCH_INTERVAL,
    DEFAULT_NETWATCH_INTERVAL, CONF_WAN_INTERFACE,
)
from .inventory import Inventory
from .log_monitor import RouterLogMonitor
from .zalo import ZaloNotifier
from .routeros import RouterOSReader
from .traffic import InterfaceRateTracker, choose_wan
from .security import port_names

_LOGGER = logging.getLogger(__name__)


class MikMiCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """One timer; RouterOS blocking I/O always runs in an HA executor thread."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, inventory: Inventory, store: Store, log_monitor: RouterLogMonitor, log_store: Store) -> None:
        self.entry = entry
        self.inventory = inventory
        self.store = store
        self.log_monitor = log_monitor
        self.log_store = log_store
        self._log_next_poll = 0.0
        self._log_polling = False
        self._netwatch_next_poll = 0.0
        self._netwatch_polling = False
        self.netwatch_rows: list[dict[str, Any]] = []
        settings = {**entry.data, **entry.options}
        self._settings = settings
        self._router = RouterOSReader(
            settings[CONF_ROUTER_HOST], settings.get(CONF_ROUTER_PORT, 8729),
            settings[CONF_ROUTER_USERNAME], settings[CONF_ROUTER_PASSWORD],
            settings[CONF_ROUTER_FINGERPRINT],
        )
        self._rate_tracker = InterfaceRateTracker()
        self.wan_traffic: dict[str, Any] = {"name": None, "rx_bps": None, "tx_bps": None, "running": False}
        self.zalo = ZaloNotifier(hass, settings)
        self.source_health: dict[str, dict[str, Any]] = {
            "mikrotik": {"ok": False, "last_success": None, "error": "not_polled"},
            "router_logs": {"ok": False, "last_success": None,
                            "error": "not_polled" if settings.get(CONF_LOG_ENABLED, True) else "disabled"},
            "netwatch": {"ok": False, "last_success": None,
                         "error": "not_polled" if settings.get(CONF_NETWATCH_ENABLED, False) else "disabled"},
        }
        super().__init__(
            hass, _LOGGER, config_entry=entry, name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(seconds=int(settings.get(CONF_POLL_INTERVAL, DEFAULT_POLL))),
        )

    def _health(self, name: str, ok: bool, error: str | None = None) -> None:
        previous = self.source_health[name]["ok"]
        previous_error = self.source_health[name]["error"]
        info = self.source_health[name]
        info["ok"] = ok
        info["error"] = error
        if ok:
            info["last_success"] = time.time()
            if not previous:
                _LOGGER.info("Netwatcher source recovered: %s", name)
        elif previous or previous_error == "not_polled":
            _LOGGER.warning("Netwatcher source unavailable: %s (category=%s)", name, error)

    def _schedule_logs(self) -> None:
        """Separate polling path: router log I/O NEVER blocks inventory refresh."""
        if not self._settings.get(CONF_LOG_ENABLED, True) or self._log_polling:
            return
        now = time.monotonic()
        if now < self._log_next_poll:
            return
        self._log_polling = True
        self._log_next_poll = now + max(30, int(self._settings.get(CONF_LOG_INTERVAL, DEFAULT_LOG_INTERVAL)))
        self.entry.async_create_background_task(
            self.hass, self._async_poll_router_logs(), f"{DOMAIN} RouterOS logs"
        )

    async def _async_poll_router_logs(self) -> None:
        """Read log, deduplicate, classify, and optionally notify security alerts."""
        try:
            rows = await self.hass.async_add_executor_job(self._router.fetch_logs)
            incidents = self.log_monitor.ingest(
                rows, login_failures=int(self._settings.get(CONF_LOGIN_FAIL_THRESHOLD, 3)),
                firewall_probes=int(self._settings.get(CONF_FIREWALL_THRESHOLD, 10)),
            )
            self.log_store.async_delay_save(self.log_monitor.dump, 10)
            self._health("router_logs", True)
            if incidents:
                _LOGGER.info("Netwatcher detected %d WAN security log candidates", len(incidents))
            for incident in incidents[:10]:
                if not self._settings.get(CONF_WAN_ALERTS, False):
                    continue
                self.hass.bus.async_fire(EVENT_WAN_SECURITY, {**incident, "entry_id": self.entry.entry_id})
                if self._settings.get(CONF_NOTIFY_PERSISTENT, True):
                    from .log_monitor import safe_text
                    category = safe_text(incident["category"], 60)
                    source = safe_text(incident["source_ip"], 50)
                    persistent_notification.async_create(
                        self.hass,
                        f"Sự kiện: {category} | IP nguồn: {source} | Số lần trong 5 phút: {incident['count']}. "
                        "Xem log MikroTik trong Netwatcher để đối chiếu; chưa kết luận có xâm nhập.",
                        title="Netwatcher MikMi: phát hiện truy cập WAN đáng ngờ",
                        notification_id=f"netwatcher_security_{self.entry.entry_id}_{category}",
                    )
                if self._settings.get(CONF_ZALO_NOTIFY_WAN, False) and self.zalo.enabled:
                    self.entry.async_create_background_task(
                        self.hass, self.zalo.send_security_alert(dict(incident)),
                        f"{DOMAIN} WAN security Zalo"
                    )
            self.async_update_listeners()  # UI/source sensor without a full inventory poll.
        except Exception as exc:
            # Do not put untrusted RouterOS log text or credentials into HA logs.
            self._health("router_logs", False, type(exc).__name__)
        finally:
            self._log_polling = False

    def _schedule_netwatch(self) -> None:
        """Read *existing* Netwatch checks off the inventory critical path."""
        if not self._settings.get(CONF_NETWATCH_ENABLED, False) or self._netwatch_polling:
            return
        now = time.monotonic()
        if now < self._netwatch_next_poll:
            return
        self._netwatch_polling = True
        self._netwatch_next_poll = now + max(60, int(self._settings.get(CONF_NETWATCH_INTERVAL, DEFAULT_NETWATCH_INTERVAL)))
        self.entry.async_create_background_task(
            self.hass, self._async_poll_netwatch(), f"{DOMAIN} RouterOS Netwatch"
        )

    async def _async_poll_netwatch(self) -> None:
        try:
            rows = await self.hass.async_add_executor_job(self._router.fetch_netwatch)
            allowed = {"host", "name", "comment", "status", "type", "disabled",
                       "rtt-avg", "rtt-min", "rtt-max", "rtt-jitter", "loss-percent", "since"}
            # Bound row count, length, and fields before showing router-supplied text.
            self.netwatch_rows = [{k: str(v)[:180] for k, v in r.items() if k in allowed}
                                  for r in rows[:250]]
            self._health("netwatch", True)
            self.async_update_listeners()
        except Exception as exc:
            self._health("netwatch", False, type(exc).__name__)
        finally:
            self._netwatch_polling = False

    async def _async_update_data(self) -> dict[str, Any]:
        self._schedule_logs()
        self._schedule_netwatch()
        snapshot = None
        try:
            snapshot = await self.hass.async_add_executor_job(self._router.fetch)
        except Exception as exc:  # Keep other collectors and UI usable.
            self._health("mikrotik", False, type(exc).__name__)
        else:
            self._health("mikrotik", True)
            rows = snapshot.get("interfaces", [])
            rates = self._rate_tracker.ingest(rows)
            chosen = choose_wan(rows, str(self._settings.get(CONF_WAN_INTERFACE, "")).strip())
            self.wan_traffic = {"name": chosen,
                                **(rates.get(chosen) or {"rx_bps": None, "tx_bps": None, "running": False})}

        now = time.time()
        events = self.inventory.ingest(
            router=snapshot, timestamp=now,
            offline_after=int(self._settings.get(CONF_OFFLINE_AFTER, DEFAULT_OFFLINE)),
            lan_ports=port_names(str(self._settings.get(CONF_LAN_PORTS, ""))),
            alert_existing=bool(self._settings.get(CONF_NOTIFY_EXISTING, False)),
        )
        self.store.async_delay_save(self.inventory.dump, 10)
        zalo_scheduled = 0
        persistent_created = 0
        if events:
            _LOGGER.info("Netwatcher changes detected: %s", ", ".join(str(e["type"]) for e in events[:30]))
        for event in events:
            event_type = event.pop("type")
            record = self.inventory.devices.get(event.get("mac", ""), {})
            enriched = {**event, "entry_id": self.entry.entry_id}
            # Start outbound notification as a managed task. Never block poll / startup.
            if self.zalo.wants(event_type) and zalo_scheduled < 30:
                self.entry.async_create_background_task(
                    self.hass, self.zalo.send_event(event_type, dict(record)),
                    f"{DOMAIN} Zalo {event_type}",
                )
                zalo_scheduled += 1
            if event_type == "new_dynamic":
                self.hass.bus.async_fire(EVENT_NEW_DYNAMIC, enriched)
                if bool(self._settings.get(CONF_NOTIFY_PERSISTENT, True)) and persistent_created < 30:
                    persistent_created += 1
                    persistent_notification.async_create(
                        self.hass,
                        f"MAC: {event['mac']} | IP: {event.get('ip') or 'unknown'} | Comment: {event.get('comment') or '-'}",
                        title="Netwatcher MikMi: new dynamic DHCP device",
                        notification_id=f"netwatcher_mikmi_{event['mac'].replace(':', '')}",
                    )
            elif event_type == "connected":
                self.hass.bus.async_fire(EVENT_CONNECTED, enriched)
            elif event_type == "disconnected":
                self.hass.bus.async_fire(EVENT_DISCONNECTED, enriched)
        if zalo_scheduled == 30 and len(events) > 30:
            _LOGGER.warning("Zalo alert batch capped at 30 events this poll")
        statistics = self.inventory.statistics()
        _LOGGER.debug(
            "Netwatcher poll complete: router=%s inventory=%d online=%d offline=%d events=%d",
            self.source_health["mikrotik"]["ok"],
            statistics["total"], statistics["online"], statistics["offline"], len(events),
        )
        return {"statistics": statistics, "sources": self.source_health.copy(), "timestamp": now,
                "router": {"resource": snapshot.get("resource", [{}])[0] if snapshot and snapshot.get("resource") else None,
                           "interfaces": snapshot.get("interfaces", []) if snapshot else []}}

    async def async_shutdown(self) -> None:
        """Shut down HA's polling machinery, cancel any pending refresh."""
        await super().async_shutdown()
