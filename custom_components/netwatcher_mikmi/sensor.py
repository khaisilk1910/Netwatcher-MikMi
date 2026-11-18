"""Compact HA sensors. No client lists or router log payloads in Recorder."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

METRIC_ICONS = {
    "total": "mdi:devices", "online": "mdi:check-network", "offline": "mdi:lan-disconnect",
"dynamic": "mdi:alert-network",
    "unapproved": "mdi:shield-alert-outline",
}
SOURCE_ICONS = {"mikrotik": "mdi:router-network", "router_logs": "mdi:text-box-search-outline", "netwatch": "mdi:monitor-eye"}

METRICS = (
    ("total", "Devices total"),
    ("online", "Devices online"),
    ("offline", "Devices offline"),
    ("dynamic", "DHCP dynamic devices"),
    ("unapproved", "Unapproved devices"),
)


@dataclass(frozen=True)
class HealthField:
    key: str
    name: str
    source: str
    unit: str | None = None
    icon: str | None = None
    device_class: SensorDeviceClass | None = None
    numeric: bool = True


HARDWARE_FIELDS: tuple[HealthField, ...] = (
    # Keep `router_cpu` unique ID stable across v0.3 → v0.4 upgrades.
    HealthField("router_cpu", "MikroTik CPU load", "cpu", "%", "mdi:cpu-64-bit"),
    HealthField("router_ram", "MikroTik RAM usage", "ram", "%", "mdi:memory"),
    HealthField("router_temperature", "MikroTik temperature", "temperature", "°C", "mdi:thermometer", SensorDeviceClass.TEMPERATURE),
    HealthField("router_cpu_temperature", "MikroTik CPU temperature", "cpu_temperature", "°C", "mdi:thermometer", SensorDeviceClass.TEMPERATURE),
    HealthField("router_board_temperature", "MikroTik board temperature", "board_temperature", "°C", "mdi:thermometer", SensorDeviceClass.TEMPERATURE),
    HealthField("router_storage", "MikroTik storage usage", "storage", "%", "mdi:harddisk"),
    HealthField("router_voltage", "MikroTik voltage", "voltage", "V", "mdi:flash", SensorDeviceClass.VOLTAGE),
    HealthField("router_fan_rpm", "MikroTik fan speed", "fan_rpm", "rpm", "mdi:fan"),
    HealthField("router_total_ram", "MikroTik total RAM", "total_ram_mib", "MiB", "mdi:memory"),
    HealthField("router_free_ram", "MikroTik free RAM", "free_ram_mib", "MiB", "mdi:memory"),
    HealthField("router_cpu_count", "MikroTik CPU count", "cpu_count", None, "mdi:cpu-64-bit"),
    HealthField("router_cpu_frequency", "MikroTik CPU frequency", "cpu_frequency_mhz", "MHz", "mdi:speedometer"),
    HealthField("router_uptime", "MikroTik uptime", "uptime_seconds", "s", "mdi:clock-outline"),
    HealthField("router_model", "MikroTik model", "model", None, "mdi:router-wireless", numeric=False),
    HealthField("router_routeros", "MikroTik RouterOS version", "routeros_version", None, "mdi:information", numeric=False),
    HealthField("router_firmware", "MikroTik RouterBOARD firmware", "firmware", None, "mdi:chip", numeric=False),
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    runtime = entry.runtime_data
    coordinator = runtime.coordinator
    hardware = runtime.hardware
    entities = [InventorySensor(coordinator, entry, key, name) for key, name in METRICS]
    entities.extend(SourceSensor(coordinator, entry, key) for key in ("mikrotik", "router_logs", "netwatch"))
    entities.extend(HardwareSensor(hardware, entry, field) for field in HARDWARE_FIELDS)
    entities.append(NetwatchDownSensor(coordinator, entry))
    entities.extend(WanTrafficSensor(coordinator, entry, direction) for direction in ("rx_bps", "tx_bps"))
    async_add_entities(entities)


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
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry, key, name):
        super().__init__(coordinator, entry, key, name)
        self._attr_icon = METRIC_ICONS.get(key, "mdi:devices")

    @property
    def native_value(self):
        return self.coordinator.inventory.statistics().get(self._key, 0)

    @property
    def available(self):
        return True  # Historical inventory remains available when source fails.


class SourceSensor(MikMiEntity):
    def __init__(self, coordinator, entry, source):
        super().__init__(coordinator, entry, f"source_{source}", f"{source.title()} source")
        self._source = source
        self._attr_icon = SOURCE_ICONS.get(source, "mdi:lan")

    @property
    def native_value(self):
        info = self.coordinator.source_health[self._source]
        if info["error"] == "disabled":
            return "disabled"
        if info["error"] == "not_polled":
            return "initializing"
        return "online" if info["ok"] else "unavailable"

    @property
    def extra_state_attributes(self):
        info = self.coordinator.source_health[self._source]
        return {"last_success_epoch": info["last_success"], "error_category": info["error"]}

    @property
    def available(self):
        return True


class HardwareSensor(MikMiEntity):
    def __init__(self, coordinator, entry: ConfigEntry, field: HealthField) -> None:
        super().__init__(coordinator, entry, field.key, field.name)
        self._field = field
        self._attr_icon = field.icon
        self._attr_native_unit_of_measurement = field.unit
        if field.numeric:
            self._attr_state_class = SensorStateClass.MEASUREMENT
        if field.device_class:
            self._attr_device_class = field.device_class

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        section = "board" if not self._field.numeric else "readings"
        return data.get(section, {}).get(self._field.source)

    @property
    def available(self):
        return bool(self.coordinator.last_update_success and self.native_value is not None and self.native_value != "")

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        if self._field.source in ("cpu", "ram", "temperature"):
            return {"alert": data.get("alerts", {}).get(self._field.source, {}),
                    "sampled_at": data.get("sampled_at")}
        return {}


class NetwatchDownSensor(MikMiEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "probes"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "netwatch_down", "MikroTik Netwatch probes down")
        self._attr_icon = "mdi:lan-disconnect"

    @property
    def native_value(self):
        return sum(row.get("status", "").lower() == "down" and row.get("disabled", "false").lower() != "true"
                   for row in self.coordinator.netwatch_rows)

    @property
    def available(self):
        return self.coordinator.source_health["netwatch"]["ok"]


class WanTrafficSensor(MikMiEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "bit/s"

    def __init__(self, coordinator, entry: ConfigEntry, direction: str) -> None:
        super().__init__(coordinator, entry, f"router_wan_{direction}",
                         "MikroTik WAN RX" if direction == "rx_bps" else "MikroTik WAN TX")
        self._direction = direction
        self._attr_icon = "mdi:download-network" if direction == "rx_bps" else "mdi:upload-network"

    @property
    def native_value(self):
        return self.coordinator.wan_traffic.get(self._direction)

    @property
    def available(self):
        return bool(self.coordinator.source_health["mikrotik"]["ok"]
                    and self.coordinator.wan_traffic.get("name")
                    and self.native_value is not None)

    @property
    def extra_state_attributes(self):
        return {"interface": self.coordinator.wan_traffic.get("name"),
                "running": self.coordinator.wan_traffic.get("running")}
