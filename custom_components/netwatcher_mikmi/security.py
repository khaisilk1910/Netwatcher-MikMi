"""Pure input validation; never follow device-provided URLs or LAN discovery hosts."""
from __future__ import annotations

import ipaddress
import re

_MAC_PATTERN = re.compile(r"^(?:[0-9A-F]{2}:){5}[0-9A-F]{2}$")
_FINGERPRINT = re.compile(r"^[0-9a-f]{64}$")
_ALLOWED = [ipaddress.ip_network(x) for x in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")]


def private_ipv4(value: str) -> str:
    """Require a literal RFC1918 IPv4, not hostname/URL (SSRF resistance)."""
    ip = ipaddress.IPv4Address(str(value).strip())
    if not any(ip in network for network in _ALLOWED):
        raise ValueError("Only literal RFC1918 addresses are accepted")
    return str(ip)


def parse_hosts(text: str, max_hosts: int = 10) -> list[str]:
    if not text.strip():
        return []
    parts = [x.strip() for x in text.split(",")]
    if len(parts) > max_hosts or any(not part for part in parts):
        raise ValueError("Invalid host list")
    hosts = [private_ipv4(p) for p in parts]
    if len(set(hosts)) != len(hosts):
        raise ValueError("Duplicate hosts")
    return hosts


def fingerprint_sha256(value: str) -> str:
    normalized = str(value).replace(":", "").strip().lower()
    if not _FINGERPRINT.fullmatch(normalized):
        raise ValueError("Certificate SHA-256 fingerprint must be 64 hex chars")
    return normalized


def mac_normalize(value: object) -> str | None:
    mac = str(value or "").strip().upper().replace("-", ":")
    if len(mac) == 12 and all(c in "0123456789ABCDEF" for c in mac):
        mac = ":".join(mac[x:x+2] for x in range(0, 12, 2))
    return mac if _MAC_PATTERN.fullmatch(mac) else None


def port_names(text: str) -> set[str]:
    values = [x.strip() for x in text.split(",") if x.strip()]
    if len(values) > 100 or any(len(x) > 80 or any(c in x for c in "\r\n\x00") for x in values):
        raise ValueError("Invalid port name list")
    return set(values)


_RECIPIENT = re.compile(r"^[A-Za-z0-9_-]{5,128}$")


def parse_recipients(value: str, maximum: int = 20) -> list[str]:
    """Allow a small explicit allow-list; no URLs, arbitrary chat IDs or headers."""
    parts = [p.strip() for p in re.split(r"[,;\n]+", str(value or "")) if p.strip()]
    if len(parts) > maximum or any(_RECIPIENT.fullmatch(p) is None for p in parts):
        raise ValueError("Invalid Zalo recipient identifiers")
    return list(dict.fromkeys(parts))


def validate_zalo_token(value: str) -> str:
    """Do not allow control characters or whitespace in HTTP credential headers."""
    token = str(value or "").strip()
    if not 8 <= len(token) <= 2048 or any(ord(c) < 33 or ord(c) > 126 for c in token):
        raise ValueError("Invalid Zalo access token")
    return token
