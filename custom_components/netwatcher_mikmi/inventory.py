"""Pure deterministic inventory correlation. No Home Assistant dependency.

DHCP `bound` is an address lease, NOT proof that a client is online.
Xiaomi client lists can aggregate a whole mesh; no node is inferred by default.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .const import MAX_DEVICES
from .security import mac_normalize


def _yes(value: Any) -> bool:
    return str(value).lower() in ("true", "yes", "1")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fresh(record: dict[str, Any], now: float, seconds: int) -> bool:
    return (now - float(record.get("last_seen_epoch", 0) or 0)) <= seconds


class Inventory:
    """Persistent MAC inventory, independent of polling implementation."""

    def __init__(self, state: dict[str, Any] | None = None):
        source = state or {}
        self.devices: dict[str, dict[str, Any]] = dict(source.get("devices", {}))
        self.baseline_complete: bool = bool(source.get("baseline_complete", False))
        self.max_devices = MAX_DEVICES

    def dump(self) -> dict[str, Any]:
        return {"baseline_complete": self.baseline_complete, "devices": self.devices}

    def ingest(
        self,
        router: dict[str, list[dict[str, str]]] | None,
        wifi: list[dict[str, Any]] | None,
        timestamp: float,
        offline_after: int,
        direct_hosts: set[str],
        lan_ports: set[str],
        alert_existing: bool = False,
        wifi_complete: bool = True,
        xiaomi_configured: bool = False,
    ) -> list[dict[str, Any]]:
        """Return notification events. Partial source failures never cause false offline."""
        events: list[dict[str, Any]] = []
        router_ok = router is not None
        wifi_ok = wifi is not None and wifi_complete
        first_router_snapshot = router_ok and not self.baseline_complete
        live: set[str] = set()
        wifi_macs: set[str] = set()
        lease_macs: set[str] = set()
        now = datetime.fromtimestamp(timestamp, timezone.utc).isoformat()

        def get_record(mac: str) -> dict[str, Any] | None:
            if mac not in self.devices:
                if len(self.devices) >= self.max_devices:
                    return None
                self.devices[mac] = {
                    "mac": mac,
                    "first_seen": now,
                    "last_seen": None,
                    "last_seen_epoch": 0,
                    "online": "unknown",
                    "approved": False,
                    "alerted_dynamic": False,
                    "baseline_exempt": (first_router_snapshot and not alert_existing) or (not self.baseline_complete and not alert_existing),
                    "connection": "unknown",
                    "ap_name": None,
                    "ip": None,
                    "comment": "",
                    "host_name": "",
                    "dhcp_dynamic": None,
                    "dhcp_status": "unmanaged",
                    "evidence": "none",
                    "confidence": "low",
                }
            return self.devices[mac]

        if router_ok:
            for lease in router.get("leases", []):
                mac = mac_normalize(lease.get("active-mac-address") or lease.get("mac-address"))
                if mac is None:
                    continue
                record = get_record(mac)
                if record is None:
                    continue
                lease_macs.add(mac)
                bound = str(lease.get("status", "")).lower() == "bound"
                dynamic = _yes(lease.get("dynamic"))
                record["dhcp_dynamic"] = dynamic
                record["dhcp_status"] = str(lease.get("status") or "unknown")
                record["comment"] = str(lease.get("comment") or "")[:160]
                record["host_name"] = str(lease.get("host-name") or "")[:120]
                ip = (lease.get("active-address") if bound else None) or lease.get("address")
                if ip:
                    record["ip"] = str(ip)[:64]
                record["dhcp_server"] = str(lease.get("server") or "")[:80]
                # Alert only after presence evidence is correlated below. A
                # still-bound DHCP lease alone is not an online observation.

            # Reclassify records not present in CURRENT DHCP snapshot, never infer dynamic.
            for mac, record in self.devices.items():
                if mac not in lease_macs:
                    record["dhcp_dynamic"] = None
                    record["dhcp_status"] = "unmanaged"

            for arp in router.get("arp", []):
                mac = mac_normalize(arp.get("mac-address"))
                if not mac or _yes(arp.get("disabled")):
                    continue
                # Some RouterOS versions omit `complete`; a MAC means an ARP mapping exists.
                if str(arp.get("complete", "true")).lower() in ("false", "no", "0"):
                    continue
                record = get_record(mac)
                if record is None:
                    continue
                live.add(mac)
                if mac not in lease_macs and arp.get("address"):
                    record["ip"] = str(arp["address"])[:64]
                record["evidence"] = "mikrotik_arp"
                record["confidence"] = "medium"

            # Only ports explicitly marked as single-device LAN endpoint are LAN proof.
            # Bridge FDB may include switches/APs and is not presence proof.
            fdb: dict[str, set[str]] = {}
            for host in router.get("bridge_hosts", []):
                mac = mac_normalize(host.get("mac-address"))
                interface = str(host.get("on-interface", ""))
                if mac and interface in lan_ports and not _yes(host.get("local")):
                    fdb.setdefault(mac, set()).add(interface)
            for mac, interfaces in fdb.items():
                if len(interfaces) == 1:
                    record = get_record(mac)
                    if record is not None:
                        record["connection"] = "lan"
                        record["port"] = next(iter(interfaces))
                        record["ap_name"] = None
                        record["evidence"] = "mikrotik_bridge_host_direct_port"
                        record["confidence"] = "medium"

        if wifi is not None:
            # An AP can return aggregate mesh clients. Use source host as AP only
            # after explicit administrator confirmation, AND no duplicate origins.
            grouped: dict[str, list[dict[str, Any]]] = {}
            for observation in wifi:
                mac = mac_normalize(observation.get("mac"))
                if mac:
                    grouped.setdefault(mac, []).append(observation)
            for mac, observations in grouped.items():
                record = get_record(mac)
                if record is None:
                    continue
                active = [obs for obs in observations if obs.get("online") is True]
                if not active:
                    continue
                wifi_macs.add(mac)
                live.add(mac)
                obs = active[0]
                if obs.get("ip") and mac not in lease_macs:
                    record["ip"] = str(obs["ip"])[:64]
                if obs.get("name"):
                    record["xiaomi_name"] = str(obs["name"])[:120]
                record["wifi_signal"] = obs.get("signal")
                record["wifi_band"] = str(obs.get("band") or "")[:20]
                # The MiWiFi library can report wired/aggregate clients; only
                # signal or band is a hint that the association is wireless.
                signal = obs.get("signal")
                wireless_hint = bool(obs.get("band")) or (
                    isinstance(signal, (int, float)) and not isinstance(signal, bool)
                    and -120 <= signal <= 100 and signal != 0
                )
                if wireless_hint:
                    record["connection"] = "wifi"
                    record["evidence"] = "xiaomi_wireless_client"
                    record["confidence"] = "medium"
                    sources = {o.get("source_host") for o in active}
                    source = next(iter(sources)) if len(sources) == 1 else None
                    if source in direct_hosts:
                        record["ap_name"] = str(obs.get("source_name") or source)[:80]
                        record["confidence"] = "high"
                        record["evidence"] = "verified_direct_ap_client_list"
                    else:
                        record["ap_name"] = None
                elif record.get("connection") != "lan":
                    record["connection"] = "unknown"
                    record["ap_name"] = None
                    record["evidence"] = "xiaomi_client_without_radio_evidence"
                    record["confidence"] = "low"

        for mac, record in self.devices.items():
            previous = record.get("online", "unknown")
            if mac in live:
                record["last_seen_epoch"] = timestamp
                record["last_seen"] = now
                record["online"] = "online"
                if previous == "offline":
                    events.append({"type": "connected", "mac": mac})
                if (record.get("dhcp_dynamic") is True and
                        record.get("dhcp_status") == "bound" and
                        not record.get("alerted_dynamic") and
                        not record.get("baseline_exempt")):
                    record["alerted_dynamic"] = True
                    events.append({"type": "new_dynamic", "mac": mac, "ip": record.get("ip"),
                                   "comment": record.get("comment"), "name": self.display_name(record),
                                   "first_seen": record.get("first_seen")})
                continue
            # Never mark offline unless MikroTik AND every configured Wi-Fi
            # collector produced a valid snapshot; no mass-disconnect on failures.
            all_healthy = router_ok and (not xiaomi_configured or wifi_ok)
            if not all_healthy:
                record["online"] = "unknown"
            elif record.get("last_seen_epoch") and not _fresh(record, timestamp, offline_after):
                record["online"] = "offline"
                if previous == "online":
                    events.append({"type": "disconnected", "mac": mac})
            else:
                # Preserve the last online state during the offline grace
                # period. Otherwise a 30-second poll overwrites it with
                # 'unknown' and the eventual offline transition is never sent.
                if record.get("last_seen_epoch") and _fresh(record, timestamp, offline_after):
                    record["online"] = previous if previous == "online" else "unknown"
                else:
                    record["online"] = "unknown"

        if router_ok:
            self.baseline_complete = True
        return events

    @staticmethod
    def display_name(record: dict[str, Any]) -> str:
        return str(record.get("alias") or record.get("comment") or record.get("xiaomi_name") or record.get("host_name") or record["mac"])

    def statistics(self) -> dict[str, int]:
        data = self.devices.values()
        return {
            "total": len(self.devices),
            "online": sum(d.get("online") == "online" for d in data),
            "offline": sum(d.get("online") == "offline" for d in data),
            "unknown": sum(d.get("online") == "unknown" for d in data),
            "dynamic": sum(d.get("dhcp_dynamic") is True for d in data),
            "unapproved": sum(not d.get("approved", False) for d in data),
        }

    def rows(self, status: str = "all", search: str = "", offset: int = 0, limit: int = 100) -> tuple[list[dict[str, Any]], int]:
        needle = search.strip().casefold()[:100]
        filtered = []
        for record in self.devices.values():
            if status in ("online", "offline", "unknown") and record.get("online") != status:
                continue
            if status == "dynamic" and record.get("dhcp_dynamic") is not True:
                continue
            if status == "unapproved" and record.get("approved") is True:
                continue
            name = self.display_name(record)
            if needle and needle not in " ".join(str(record.get(k) or "") for k in ("mac", "ip", "comment", "host_name", "xiaomi_name", "alias", "ap_name", "port")).casefold():
                continue
            filtered.append({**record, "name": name})
        filtered.sort(key=lambda d: (-float(d.get("last_seen_epoch") or 0), d["mac"]))
        return filtered[offset:offset + min(limit, 200)], len(filtered)
