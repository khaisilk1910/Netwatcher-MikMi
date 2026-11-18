"""Narrow, read-only RouterOS API-SSL client (stdlib; synchronous; executor only).

Pins the server certificate BEFORE sending credentials. No TOFU and no writes.
Commands are a hard-coded allow-list of '/print' only.
"""
from __future__ import annotations

import hashlib
import hmac
import socket
import ssl
from typing import Any

from .security import fingerprint_sha256, private_ipv4

SOCKET_TIMEOUT = 8
MAX_WORD_BYTES = 1_048_576
MAX_ROWS = 5000
# `=.proplist` limits the returned data, not the capabilities of the account.
COMMANDS = {
    "leases": ("/ip/dhcp-server/lease/print", "mac-address,address,active-address,active-mac-address,host-name,comment,dynamic,status,disabled,server,last-seen"),
    "arp": ("/ip/arp/print", "mac-address,address,interface,complete,disabled"),
    "bridge_hosts": ("/interface/bridge/host/print", "mac-address,on-interface,bridge,local,age"),
    "interfaces": ("/interface/print", "name,running,disabled,rx-byte,tx-byte,type"),
}

class RouterError(Exception):
    """Safe error category (never embeds credentials or untrusted reply text)."""

class RouterAuthError(RouterError):
    """API authentication rejected."""

class RouterCertificateError(RouterError):
    """TLS fingerprint mismatch."""


def _encode_length(n: int) -> bytes:
    if n < 0x80:
        return bytes([n])
    if n < 0x4000:
        return (n | 0x8000).to_bytes(2, "big")
    if n < 0x200000:
        return (n | 0xC00000).to_bytes(3, "big")
    if n < 0x10000000:
        return (n | 0xE0000000).to_bytes(4, "big")
    return b"\xF0" + n.to_bytes(4, "big")


class RouterOSReader:
    def __init__(self, host: str, port: int, username: str, password: str, fingerprint: str):
        self.host = private_ipv4(host)
        self.port = int(port)
        if not 1 <= self.port <= 65535:
            raise ValueError("Port out of range")
        self.username = username
        self.password = password
        self.fingerprint = fingerprint_sha256(fingerprint)

    @staticmethod
    def _read_exact(conn: ssl.SSLSocket, amount: int) -> bytes:
        result = bytearray()
        while len(result) < amount:
            chunk = conn.recv(amount - len(result))
            if not chunk:
                raise RouterError("Connection closed during read")
            result.extend(chunk)
        return bytes(result)

    @classmethod
    def _read_length(cls, conn: ssl.SSLSocket) -> int:
        first = cls._read_exact(conn, 1)[0]
        if first < 0x80:
            length = first
        elif first < 0xC0:
            length = ((first & 0x3F) << 8) | cls._read_exact(conn, 1)[0]
        elif first < 0xE0:
            length = ((first & 0x1F) << 16) | int.from_bytes(cls._read_exact(conn, 2), "big")
        elif first < 0xF0:
            length = ((first & 0x0F) << 24) | int.from_bytes(cls._read_exact(conn, 3), "big")
        else:
            length = int.from_bytes(cls._read_exact(conn, 4), "big")
        if length > MAX_WORD_BYTES:
            raise RouterError("RouterOS reply word too large")
        return length

    @classmethod
    def _sentence(cls, conn: ssl.SSLSocket) -> list[str]:
        words = []
        while True:
            length = cls._read_length(conn)
            if not length:
                return words
            if len(words) > 128:
                raise RouterError("Too many words in RouterOS reply")
            words.append(cls._read_exact(conn, length).decode("utf-8", errors="replace"))

    @classmethod
    def _command(cls, conn: ssl.SSLSocket, words: list[str], auth: bool = False) -> list[dict[str, str]]:
        conn.sendall(b"".join(_encode_length(len(s.encode("utf-8"))) + s.encode("utf-8") for s in words) + b"\0")
        rows: list[dict[str, str]] = []
        trapped = False
        for _ in range(MAX_ROWS + 16):
            response = cls._sentence(conn)
            if not response:
                continue
            kind = response[0]
            if kind == "!fatal":
                raise RouterAuthError("RouterOS login rejected") if auth else RouterError("RouterOS read failed")
            if kind == "!trap":
                trapped = True
                continue  # Always drain !done before sending another command.
            if kind == "!done":
                if trapped:
                    raise RouterAuthError("RouterOS login rejected") if auth else RouterError("RouterOS read command rejected")
                return rows
            if kind == "!re":
                row: dict[str, str] = {}
                for word in response[1:]:
                    if word.startswith("="):
                        key, sep, val = word[1:].partition("=")
                        if sep:
                            row[key] = val
                rows.append(row)
                if len(rows) > MAX_ROWS:
                    raise RouterError("RouterOS reply exceeds row limit")
        raise RouterError("RouterOS response exceeded sentence limit")

    def _connect_and_read(self, commands: dict[str, tuple[str, str, bool]]) -> dict[str, Any]:
        """A single authenticated, pinned TLS session per bounded batch.

        `optional` commands may not exist on CHR or older boards. Every optional
        trap is drained, without hiding failures of /system/resource.
        """
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE  # SHA-256 pin is checked before password.
        try:
            with socket.create_connection((self.host, self.port), timeout=SOCKET_TIMEOUT) as raw:
                with ctx.wrap_socket(raw, server_hostname=None) as conn:
                    conn.settimeout(SOCKET_TIMEOUT)
                    der = conn.getpeercert(binary_form=True)
                    if not der or not hmac.compare_digest(hashlib.sha256(der).hexdigest(), self.fingerprint):
                        raise RouterCertificateError("RouterOS certificate fingerprint mismatch")
                    self._command(conn, ["/login", f"=name={self.username}", f"=password={self.password}"], auth=True)
                    result = {}
                    for key, (command, columns, optional) in commands.items():
                        try:
                            result[key] = self._command(conn, [command] + ([f"=.proplist={columns}"] if columns else []))
                            if optional:
                                result[f"{key}_ok"] = True
                        except RouterError:
                            if not optional:
                                raise
                            result[key] = []
                            result[f"{key}_ok"] = False
                    return result
        except (socket.timeout, OSError, ssl.SSLError) as exc:
            raise RouterError("RouterOS API-SSL connection failed") from exc

    def fetch_hardware(self, include_sensors: bool = True, include_board: bool = False) -> dict[str, Any]:
        """Read hardware without writes; fast resource + optional slower sensors.

        All values are untrusted strings until normalized by hardware.py.
        """
        commands = {
            "resource": ("/system/resource/print",
                         "cpu-load,free-memory,total-memory,free-hdd-space,total-hdd-space,"
                         "uptime,version,board-name,cpu,cpu-count,cpu-frequency,"
                         "architecture-name,platform,bad-blocks", False),
        }
        if include_sensors:
            commands["health"] = ("/system/health/print", "", True)
        if include_board:
            commands["routerboard"] = ("/system/routerboard/print", "model,factory-firmware,current-firmware,upgrade-firmware,routerboard", True)
        return self._connect_and_read(commands)

    def fetch_netwatch(self) -> list[dict[str, str]]:
        """Read existing RouterOS Netwatch probes (never add probes/scripts)."""
        rows = self._connect_and_read({
            "netwatch": ("/tool/netwatch/print", "host,name,comment,status,type,disabled,"
                         "rtt-avg,rtt-min,rtt-max,rtt-jitter,loss-percent,since", False),
        })["netwatch"]
        return rows[:500]

    def fetch(self) -> dict[str, list[dict[str, str]]]:
        """Fetch inventory only; hardware and RouterOS logs run independently."""
        commands = {key: (command, columns, False)
                    for key, (command, columns) in COMMANDS.items()}
        commands["wifi_registration"] = (
            "/interface/wifi/registration-table/print", "mac-address,interface", True)
        commands["wireless_registration"] = (
            "/interface/wireless/registration-table/print", "mac-address,interface", True)
        return self._connect_and_read(commands)

    def fetch_logs(self) -> list[dict[str, str]]:
        """Memory log read only; HTTPS certificate pinned before credentials."""
        result = self._connect_and_read({
            "logs": ("/log/print", ".id,time,topics,message", False),
        })
        return result["logs"][-1500:]
