"""Optional per-device scanner entities from MikroTik observations."""
from __future__ import annotations

from homeassistant.components.device_tracker import ScannerEntity, SourceType
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_TRACKERS

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    if not entry.options.get(CONF_TRACKERS, False):
        return
    coord = entry.runtime_data.coordinator
    tracked: set[str] = set()

    @callback
    def add_new() -> None:
        entities = []
        for mac in coord.inventory.devices:
            if mac not in tracked:
                tracked.add(mac)
                entities.append(MikMiTracker(coord, entry, mac))
        if entities:
            async_add_entities(entities)

    add_new()
    entry.async_on_unload(coord.async_add_listener(add_new))


class MikMiTracker(CoordinatorEntity, ScannerEntity):
    _attr_has_entity_name = False
    def __init__(self, coordinator, entry, mac):
        super().__init__(coordinator)
        self._mac = mac
        self._attr_unique_id = f"{entry.entry_id}_device_{mac}"

    @property
    def _record(self):
        return self.coordinator.inventory.devices.get(self._mac, {})

    @property
    def name(self):
        return self.coordinator.inventory.display_name(self._record)

    @property
    def available(self):
        return True

    @property
    def is_connected(self):
        return self._record.get("online") == "online"

    @property
    def icon(self):
        """Show link type and presence without changing the underlying tracker state."""
        link = self._record.get("connection")
        online = self._record.get("online")
        if link == "wifi":
            return "mdi:wifi" if online == "online" else "mdi:wifi-off"
        if link == "lan":
            return "mdi:lan-connect" if online == "online" else "mdi:lan-disconnect"
        return "mdi:devices" if online == "online" else "mdi:help-network"

    @property
    def source_type(self):
        return SourceType.ROUTER

    @property
    def mac_address(self):
        return self._mac

    @property
    def ip_address(self):
        return self._record.get("ip")

    @property
    def hostname(self):
        return self._record.get("host_name")

    @property
    def extra_state_attributes(self):
        return {key: self._record.get(key) for key in
                ("comment", "dhcp_dynamic", "dhcp_status", "connection", "ap_name", "port", "last_seen", "evidence", "confidence")}
