"""Separate bounded fast-path for MikroTik health, with persisted threshold state."""
from __future__ import annotations

import logging
import time
from datetime import timedelta
from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN, DEFAULT_HARDWARE_INTERVAL, DEFAULT_HEALTH_DETAIL_INTERVAL,
    CONF_HARDWARE_INTERVAL, CONF_HEALTH_DETAIL_INTERVAL, CONF_HARDWARE_RECOVERY,
    CONF_HARDWARE_ZALO, CONF_NOTIFY_PERSISTENT, EVENT_HARDWARE_ALERT,
)
from .hardware import HardwareAlertEngine, METRIC_NAMES, normalize_hardware
from .routeros import RouterOSReader
from .zalo import ZaloNotifier

_LOGGER = logging.getLogger(__name__)


class MikMiHardwareCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll resource every 15s, health every 60s, board every 10min.

    Uses independent executor I/O, never waits for inventory or log scans.
    Errors in this path cannot mark all DHCP clients offline.
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, reader: RouterOSReader,
                 store: Store, previous: dict[str, Any] | None, zalo: ZaloNotifier) -> None:
        self.entry = entry
        self.reader = reader
        self.store = store
        self.zalo = zalo
        self.settings = {**entry.data, **entry.options}
        self.alert_engine = HardwareAlertEngine(previous)
        self.alerts: dict[str, Any] = {}
        self.source_error: str | None = "not_polled"
        self.last_success: float | None = None
        self._sensors_due = 0.0
        self._board_due = 0.0
        self._last_state_dump = self.alert_engine.dump()
        super().__init__(
            hass, _LOGGER, config_entry=entry,
            name=f"{DOMAIN}_hardware_{entry.entry_id}",
            update_interval=timedelta(seconds=int(self.settings.get(CONF_HARDWARE_INTERVAL, DEFAULT_HARDWARE_INTERVAL))),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        now = time.monotonic()
        sensors_due = now >= self._sensors_due
        board_due = now >= self._board_due
        try:
            raw = await self.hass.async_add_executor_job(self.reader.fetch_hardware, sensors_due, board_due)
        except Exception as exc:
            category = type(exc).__name__  # Never log external exception text or API credentials.
            if self.source_error != category:
                _LOGGER.warning("MikroTik hardware source not available: %s", category)
            self.source_error = category
            for counter in self.alert_engine.metrics.values():
                counter["high"] = counter["low"] = 0  # outage breaks confirmation streak
            raise UpdateFailed(f"MikroTik hardware source unavailable ({category})") from None

        self.source_error = None
        self.last_success = time.time()
        if sensors_due:
            self._sensors_due = now + int(self.settings.get(CONF_HEALTH_DETAIL_INTERVAL, DEFAULT_HEALTH_DETAIL_INTERVAL))
        if board_due:
            self._board_due = now + 600
        snapshot = normalize_hardware(raw, self.data)
        fresh_metrics = {"cpu", "ram"}
        if sensors_due:
            fresh_metrics.add("temperature")
        events, self.alerts = self.alert_engine.process(
            snapshot["readings"], self.settings, observed=fresh_metrics
        )
        snapshot["alerts"] = self.alerts
        snapshot["poll_intervals"] = {
            "resource": int(self.settings.get(CONF_HARDWARE_INTERVAL, DEFAULT_HARDWARE_INTERVAL)),
            "sensors": int(self.settings.get(CONF_HEALTH_DETAIL_INTERVAL, DEFAULT_HEALTH_DETAIL_INTERVAL)),
        }
        current_dump = self.alert_engine.dump()
        if current_dump != self._last_state_dump:
            self._last_state_dump = current_dump
            self.store.async_delay_save(self.alert_engine.dump, 5)
        for incident in events:
            # Recovery always dismisses an old persistent warning, even if the
            # user disables recovery messages to events and Zalo.
            if incident["kind"] == "recovered":
                persistent_notification.async_dismiss(
                    self.hass, f"netwatcher_hardware_{self.entry.entry_id}_{incident['metric']}"
                )
                if not self.settings.get(CONF_HARDWARE_RECOVERY, True):
                    continue
            safe_event = dict(incident)
            safe_event["entry_id"] = self.entry.entry_id
            safe_event["model"] = snapshot.get("board", {}).get("model") or "MikroTik"
            self.hass.bus.async_fire(EVENT_HARDWARE_ALERT, safe_event)
            metric = incident["metric"]
            value = incident["value"]
            threshold = incident["threshold"]
            notification_id = f"netwatcher_hardware_{self.entry.entry_id}_{metric}"
            if incident["kind"] == "recovered":
                persistent_notification.async_dismiss(self.hass, notification_id)
            elif self.settings.get(CONF_NOTIFY_PERSISTENT, True):
                unit = "°C" if metric == "temperature" else "%"
                persistent_notification.async_create(
                    self.hass,
                    f"{METRIC_NAMES[metric]} = {value:g}{unit} (ngưỡng: {threshold:g}{unit}). "
                    "Đã xác nhận qua nhiều mẫu. Kiểm tra RouterOS và tải thực tế.",
                    title="⚠️ Netwatcher MikMi | Router hardware",
                    notification_id=notification_id,
                )
            if self.settings.get(CONF_HARDWARE_ZALO, False) and self.zalo.enabled:
                self.entry.async_create_background_task(
                    self.hass, self.zalo.send_hardware_alert(safe_event),
                    f"{DOMAIN} hardware Zalo {metric}",
                )
        if events:
            _LOGGER.info("Hardware threshold transitions: %s", ",".join(f"{x['metric']}/{x['kind']}" for x in events))
        return snapshot
