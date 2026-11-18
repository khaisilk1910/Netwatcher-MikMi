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
    "resource": ("/system/resource/print", "cpu-load,free-memory,total-memory,uptime,version,board-name"),
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
        while True:
            response = cls._sentence(conn)
            if not response:
                continue
            kind = response[0]
            if kind in ("!trap", "!fatal"):
                if auth:
                    raise RouterAuthError("RouterOS login rejected")
                raise RouterError("RouterOS rejected a read-only command")
            if kind == "!done":
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

    def fetch(self) -> dict[str, list[dict[str, str]]]:
        """Fetch an atomic RouterOS snapshot; no mutations, no unpinned TLS."""
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE  # Explicit cert pin is the trust anchor.
        try:
            with socket.create_connection((self.host, self.port), timeout=SOCKET_TIMEOUT) as raw:
                with ctx.wrap_socket(raw, server_hostname=None) as conn:
                    conn.settimeout(SOCKET_TIMEOUT)
                    der = conn.getpeercert(binary_form=True)
                    if not der or not hmac.compare_digest(hashlib.sha256(der).hexdigest(), self.fingerprint):
                        raise RouterCertificateError("RouterOS certificate fingerprint mismatch")
                    self._command(conn, ["/login", f"=name={self.username}", f"=password={self.password}"], auth=True)
                    result = {}
                    for key, (command, columns) in COMMANDS.items():
                        result[key] = self._command(conn, [command, f"=.proplist={columns}"])
                    return result
        except (socket.timeout, OSError, ssl.SSLError) as exc:
            raise RouterError("RouterOS API-SSL connection failed") from exc

    def fetch_logs(self) -> list[dict[str, str]]:
        """Fetch /log memory read-only using an independently pinned TLS session.

        This method must ONLY run in hass.async_add_executor_job.  Returning
        the newest 1500 rows avoids retaining huge log buffers in memory.
        """
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE  # SHA256 pin verified before credentials.
        try:
            with socket.create_connection((self.host, self.port), timeout=SOCKET_TIMEOUT) as raw:
                with ctx.wrap_socket(raw, server_hostname=None) as conn:
                    conn.settimeout(SOCKET_TIMEOUT)
                    der = conn.getpeercert(binary_form=True)
                    if not der or not hmac.compare_digest(hashlib.sha256(der).hexdigest(), self.fingerprint):
                        raise RouterCertificateError("RouterOS certificate fingerprint mismatch")
                    self._command(conn, ["/login", f"=name={self.username}", f"=password={self.password}"], auth=True)
                    rows = self._command(conn, ["/log/print", "=.proplist=.id,time,topics,message"])
                    return rows[-1500:]
        except (socket.timeout, OSError, ssl.SSLError) as exc:
            raise RouterError("RouterOS log read failed") from exc
