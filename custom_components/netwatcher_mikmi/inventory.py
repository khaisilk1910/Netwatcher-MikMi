"""MikroTik-only device inventory. DHCP leases are not online evidence.

RouterOS ARP/FDB entries can outlive a disconnected Wi-Fi client; the resulting
presence is a best-effort observation, not proof of an active Wi-Fi association.
"""
from __future__ import annotations

from datetime import datetime, timezone
from ipaddress import ip_address
from typing import Any

from .const import MAX_DEVICES
from .security import mac_normalize


def _yes(value: Any) -> bool:
    return str(value).lower() in ("true", "yes", "1")


class Inventory:
    """Persistent MAC inventory with version-independent migration."""

    def __init__(self, state: dict[str, Any] | None = None):
        source = state or {}
        self.devices: dict[str, dict[str, Any]] = dict(source.get("devices", {}))
        self.baseline_complete = bool(source.get("baseline_complete", False))
        self.max_devices = MAX_DEVICES
        for record in self.devices.values():
            old_status = record.get("online")
            record["online"] = "online" if old_status == "online" else "offline"
            record.setdefault("last_good_online", "online" if old_status == "online" else "offline")
            # Link evidence from a retired collector must never be treated as current.
            for key in tuple(record):
                if key in ("wifi_band", "wifi_signal", "xiaomi_name"):
                    record.pop(key, None)
            if (record.get("connection") == "wifi" and record.get("evidence") != "mikrotik_wifi_registration") or str(record.get("evidence", "")).startswith(("xiaomi_", "verified_direct_ap_")):
                record["connection"] = None
                record["port"] = None
                record["ap_name"] = None
                record["evidence"] = "not_verified"
                record["confidence"] = "low"
            elif record.get("connection") not in ("lan", "wifi"):
                record["connection"] = None

    def dump(self) -> dict[str, Any]:
        return {"baseline_complete": self.baseline_complete, "devices": self.devices}

    def ingest(self, router: dict[str, list[dict[str, str]]] | None,
               timestamp: float, offline_after: int, lan_ports: set[str],
               alert_existing: bool = False) -> list[dict[str, Any]]:
        """Ingest a complete RouterOS snapshot, never alert on a source failure.

        The UI has exactly two device states. On a failed read, it shows Offline
        but retains last_good_online to avoid a synthetic reconnection alert.
        """
        if router is None:
            for record in self.devices.values():
                record["online"] = "offline"
            return []

        now = datetime.fromtimestamp(timestamp, timezone.utc).isoformat()
        first_snapshot = not self.baseline_complete
        live: set[str] = set()
        lease_macs: set[str] = set()
        events: list[dict[str, Any]] = []

        def get_record(mac: str) -> dict[str, Any] | None:
            if mac not in self.devices:
                if len(self.devices) >= self.max_devices:
                    return None
                self.devices[mac] = {
                    "mac": mac, "first_seen": now, "first_seen_epoch": timestamp,
                    "last_seen": None, "last_seen_epoch": 0,
                    "online": "offline", "last_good_online": "offline", "approved": False,
                    "alerted_dynamic": False,
                    "baseline_exempt": first_snapshot and not alert_existing,
                    "connection": None, "port": None, "ap_name": None,
                    "ip": None, "comment": "", "host_name": "",
                    "dhcp_dynamic": None, "dhcp_status": "unmanaged",
                    "evidence": "none", "confidence": "low",
                }
            return self.devices[mac]

        for lease in router.get("leases", []):
            mac = mac_normalize(lease.get("active-mac-address") or lease.get("mac-address"))
            if mac is None:
                continue
            record = get_record(mac)
            if record is None:
                continue
            lease_macs.add(mac)
            bound = str(lease.get("status", "")).lower() == "bound"
            record["dhcp_dynamic"] = _yes(lease.get("dynamic"))
            record["dhcp_status"] = str(lease.get("status") or "unmanaged")
            record["comment"] = str(lease.get("comment") or "")[:160]
            record["host_name"] = str(lease.get("host-name") or "")[:120]
            ip = (lease.get("active-address") if bound else None) or lease.get("address")
            if ip:
                record["ip"] = str(ip)[:64]
            record["dhcp_server"] = str(lease.get("server") or "")[:80]

        for mac, record in self.devices.items():
            if mac not in lease_macs:
                record["dhcp_dynamic"] = None
                record["dhcp_status"] = "unmanaged"

        for arp in router.get("arp", []):
            mac = mac_normalize(arp.get("mac-address"))
            if not mac or _yes(arp.get("disabled")):
                continue
            if str(arp.get("complete", "true")).lower() in ("false", "no", "0"):
                continue
            record = get_record(mac)
            if record is None:
                continue
            live.add(mac)
            if mac not in lease_macs and arp.get("address"):
                record["ip"] = str(arp["address"])[:64]
            record["evidence"] = "mikrotik_arp_cache"
            record["confidence"] = "low"  # RouterOS may retain entries after disconnect.

        # Only known single-device endpoint ports warrant classifying as wired.
        fdb: dict[str, set[str]] = {}
        for host in router.get("bridge_hosts", []):
            mac = mac_normalize(host.get("mac-address"))
            interface = str(host.get("on-interface", ""))
            if mac and interface in lan_ports and not _yes(host.get("local")):
                fdb.setdefault(mac, set()).add(interface)
        for mac, interfaces in fdb.items():
            if len(interfaces) != 1:
                continue
            record = get_record(mac)
            if record is not None:
                record["connection"] = "lan"
                record["port"] = next(iter(interfaces))
                record["ap_name"] = None
                record["evidence"] = "mikrotik_direct_lan_port"
                record["confidence"] = "medium"

        # MikroTik wireless registration lists are optional and may be empty on
        # hardware without RouterOS WiFi packages or with different permissions.
        associated_macs: set[str] = set()
        for table in ("wifi_registration", "wireless_registration"):
            for station in router.get(table, []):
                mac = mac_normalize(station.get("mac-address"))
                if not mac or _yes(station.get("disabled")):
                    continue
                record = get_record(mac)
                if record is None:
                    continue
                live.add(mac)
                associated_macs.add(mac)
                record["connection"] = "wifi"
                record["wifi_table"] = table
                record["ap_name"] = str(station.get("interface") or "")[:80] or None
                record["port"] = record["ap_name"]
                record["evidence"] = "mikrotik_wifi_registration"
                record["confidence"] = "high"

        # An ARP mapping is a cache, not a live radio connection. Once a MAC
        # was observed on MikroTik's own Wi-Fi registration table, a healthy
        # current table that lacks that station takes priority over cached ARP.
        # An optional-table API error must never be interpreted as no clients.
        unverified_wifi: set[str] = set()
        for mac, record in self.devices.items():
            table = record.get("wifi_table")
            if table in ("wifi_registration", "wireless_registration") and mac not in associated_macs:
                live.discard(mac)
                if router.get(f"{table}_ok") is not True:
                    unverified_wifi.add(mac)

        for mac, record in self.devices.items():
            # last_good_online reflects only successful polls. Never use an
            # unavailable-source UI state for event transition decisions.
            previous = record.get("last_good_online", "offline")
            if mac in live:
                record["last_seen_epoch"] = timestamp
                record["last_seen"] = now
                new_status = "online"
                if previous == "offline" and not first_snapshot and record.get("last_good_seen", False):
                    events.append({"type": "connected", "mac": mac})
                if record.get("dhcp_dynamic") is True and record.get("dhcp_status") == "bound" and not record.get("alerted_dynamic") and not record.get("baseline_exempt"):
                    record["alerted_dynamic"] = True
                    events.append({"type": "new_dynamic", "mac": mac, "ip": record.get("ip"),
                                   "comment": record.get("comment"), "name": self.display_name(record),
                                   "first_seen": record.get("first_seen")})
            else:
                last_seen = float(record.get("last_seen_epoch") or 0)
                new_status = "online" if previous == "online" and last_seen and timestamp - last_seen < offline_after else "offline"
                if (new_status == "offline" and previous == "online" and not first_snapshot
                        and mac not in unverified_wifi):
                    events.append({"type": "disconnected", "mac": mac})
            record["online"] = new_status
            if mac in unverified_wifi:
                # RouterOS radio table failed; the two-state UI may show
                # Offline but must not generate a synthetic transition.
                continue
            record["last_good_online"] = new_status
            record["last_good_seen"] = True

        self.baseline_complete = True
        return events

    @staticmethod
    def display_name(record: dict[str, Any]) -> str:
        return str(record.get("alias") or record.get("comment") or record.get("host_name") or record.get("mac") or "Device")

    def statistics(self) -> dict[str, int]:
        data = self.devices.values()
        return {
            "total": len(self.devices),
            "online": sum(d.get("online") == "online" for d in data),
            "offline": sum(d.get("online") != "online" for d in data),
            "dynamic": sum(d.get("dhcp_dynamic") is True for d in data),
            "unapproved": sum(not d.get("approved", False) for d in data),
        }

    def rows(self, status: str = "all", search: str = "", offset: int = 0, limit: int = 100,
             sort_by: str = "recent", sort_dir: str = "desc") -> tuple[list[dict[str, Any]], int]:
        needle = search.strip().casefold()[:100]
        filtered = []
        for record in self.devices.values():
            if status in ("online", "offline") and record.get("online") != status:
                continue
            if status == "dynamic" and record.get("dhcp_dynamic") is not True:
                continue
            if status == "unapproved" and record.get("approved") is True:
                continue
            name = self.display_name(record)
            if needle and needle not in " ".join(str(record.get(k) or "") for k in ("mac", "ip", "comment", "host_name", "alias", "ap_name", "port")).casefold():
                continue
            filtered.append({**record, "name": name})
        if sort_by == "name":
            filtered.sort(key=lambda d: (d["name"].casefold(), d["mac"]),
                          reverse=sort_dir == "desc")
        elif sort_by == "ip":
            # Sort by numeric address, not lexicographic text: .9 < .100.
            # Missing/invalid addresses always remain at the bottom.
            ipv4, ipv6, missing = [], [], []
            for device in filtered:
                try:
                    address = ip_address(str(device.get("ip") or ""))
                except ValueError:
                    missing.append(device)
                    continue
                (ipv4 if address.version == 4 else ipv6).append((int(address), device))
            for group in (ipv4, ipv6):
                group.sort(key=lambda item: (item[0], item[1]["name"].casefold(), item[1]["mac"]),
                           reverse=sort_dir == "desc")
            missing.sort(key=lambda d: (d["name"].casefold(), d["mac"]))
            filtered = [device for _address, device in ipv4 + ipv6] + missing
        else:
            # Preserve the preexisting default (most recently seen first).
            filtered.sort(key=lambda d: (-float(d.get("last_seen_epoch") or 0), d["mac"]))
        return filtered[offset:offset + min(limit, 200)], len(filtered)
