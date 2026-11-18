"""Aggregate inventory and router health sensors; no huge state attributes."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

METRICS = (
    ("total", "Devices total"),
    ("online", "Devices online"),
    ("offline", "Devices offline"),
    ("unknown", "Devices unknown"),
    ("dynamic", "DHCP dynamic devices"),
    ("unapproved", "Unapproved devices"),
)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data.coordinator
    async_add_entities([InventorySensor(coordinator, entry, key, name) for key, name in METRICS] +
                       [SourceSensor(coordinator, entry, key) for key in ("mikrotik", "xiaomi", "router_logs")] +
                       [CpuSensor(coordinator, entry)])


class MikMiEntity(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    def __init__(self, coordinator, entry: ConfigEntry, key: str, name: str) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_name = name
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)}, name="Netwatcher MikMi")


class InventorySensor(MikMiEntity):
    _attr_native_unit_of_measurement = "devices"
    _attr_state_class = "measurement"
    def __init__(self, coordinator, entry, key, name):
        super().__init__(coordinator, entry, key, name)

    @property
    def native_value(self):
        return self.coordinator.inventory.statistics().get(self._key, 0)

    @property
    def available(self):
        return True  # Historical/unknown inventory still available when source fails.


class SourceSensor(MikMiEntity):
    def __init__(self, coordinator, entry, source):
        super().__init__(coordinator, entry, f"source_{source}", f"{source.title()} source")
        self._source = source

    @property
    def native_value(self):
        info = self.coordinator.source_health[self._source]
        if info["error"] == "disabled":
            return "disabled"
        if info["error"] == "not_polled":
            return "unknown"
        return "online" if info["ok"] else "unavailable"

    @property
    def extra_state_attributes(self):
        info = self.coordinator.source_health[self._source]
        return {"last_success_epoch": info["last_success"], "error_category": info["error"]}

    @property
    def available(self):
        return True


class CpuSensor(MikMiEntity):
    _attr_native_unit_of_measurement = "%"
    _attr_state_class = "measurement"
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "router_cpu", "MikroTik CPU load")

    @property
    def native_value(self):
        resource = (self.coordinator.data or {}).get("router", {}).get("resource") or {}
        try:
            return int(resource["cpu-load"])
        except (KeyError, ValueError, TypeError):
            return None

    @property
    def available(self):
        return self.coordinator.source_health["mikrotik"]["ok"]
