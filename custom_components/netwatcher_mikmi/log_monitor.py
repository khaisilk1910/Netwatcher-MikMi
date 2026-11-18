"""Local RouterOS log timeline and conservative WAN/security event detection.

Pure Python: deliberately no Home Assistant imports. It never changes a router.
Alert evidence:
 - explicit account login success/failure from a PUBLIC source IP, or
 - a firewall log entry deliberately marked by administrator with the exact
   NWMIKMI-WAN prefix, from a PUBLIC IP.
Neither a generic firewall drop nor DHCP/PPPoE traffic is labelled an attack.
"""
from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
import hashlib
import ipaddress
import re
import time
from typing import Any

MAX_LOG_ROWS = 200  # Current display only, NOT persisted to Home Assistant storage.
MAX_SEEN = 1800
MAX_INCIDENTS = 40
WINDOW_SECONDS = 300
ALERT_COOLDOWN_SECONDS = 1800
# RouterOS logs are loosely formatted, so require strong topic + phrase evidence.
LOGIN_FAILURE = re.compile(r"\b(?:login failure|login failed|failed login|authentication failed|invalid password|login incorrect)\b", re.I)
LOGIN_SUCCESS = re.compile(r"\blogged in from\b", re.I)
FROM_IP = re.compile(r"\bfrom\s+\[?([a-fA-F0-9:.]+)\]?\b", re.I)
SRC_IP = re.compile(r"\b(?:src-address|src|source)\s*[=:]\s*\[?([a-fA-F0-9:.]+)", re.I)
PACKET_SRC = re.compile(r"(?<![\d.])((?:\d{1,3}\.){3}\d{1,3}):\d{1,5}\s*->")
# Strip access credentials that an administrator / custom script might log.
SECRET = re.compile(r"(?i)\b(password|passwd|token|secret|authorization|api[_-]?key)\s*[=:]\s*\S+")
CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]")


def safe_text(value: Any, limit: int = 500) -> str:
    text = CONTROL.sub(" ", str(value or ""))
    text = SECRET.sub(lambda m: f"{m.group(1)}=<redacted>", text)
    return " ".join(text.split())[:limit]


def public_address(value: str | None) -> str | None:
    if not value:
        return None
    candidate = str(value).strip().strip("[]")
    try:
        address = ipaddress.ip_address(candidate)
        return str(address) if address.is_global else None
    except ValueError:
        return None


def extract_public_ip(message: str) -> str | None:
    """Return IP only when its location in the log identifies the source."""
    for expression in (FROM_IP, SRC_IP, PACKET_SRC):
        match = expression.search(message)
        if match and (ip := public_address(match.group(1))):
            return ip
    return None


def classify_log(topics: str, message: str) -> tuple[str | None, str | None]:
    """Classify one entry; not an incident until an explicit threshold is met."""
    t = str(topics).lower().split(",")
    lowered = str(message).lower()
    source = extract_public_ip(message)
    if not source:
        return None, None
    # Account logs can also contain PPP login / system account data. Only
    # RouterOS management account topic is accepted, not PPP/hotspot/ssh alone.
    if "account" in t and LOGIN_SUCCESS.search(lowered):
        return "external_admin_login", source
    if ("account" in t or "system" in t) and LOGIN_FAILURE.search(lowered):
        return "failed_admin_login", source
    if "firewall" in t and "nwmikmi-wan" in lowered:
        return "wan_management_probe", source
    return None, None


class RouterLogMonitor:
    """Deduplicate logs over restarts, show recent rows, and rate-limit incidents.

    Important: a first snapshot, and a recovery after >10 min offline,
    establishes a baseline without triggering historic alerts.
    """
    def __init__(self, state: dict[str, Any] | None = None) -> None:
        data = state if isinstance(state, dict) else {}
        seen = data.get("seen", [])
        self._seen: deque[str] = deque([x for x in seen if isinstance(x, str)][:MAX_SEEN], maxlen=MAX_SEEN)
        self._seen_set = set(self._seen)
        self.baselined = bool(data.get("baselined", False))
        self.last_poll_epoch = float(data.get("last_poll_epoch", 0) or 0)
        self._recent: list[dict[str, str]] = []
        self._incidents: deque[dict[str, Any]] = deque(maxlen=MAX_INCIDENTS)
        self._counters: dict[tuple[str, str], deque[float]] = {}
        self._last_alert: dict[tuple[str, str], float] = {}

    def dump(self) -> dict[str, Any]:
        """Persist only dedup fingerprints; never the full log or WAN IPs."""
        return {"baselined": self.baselined, "last_poll_epoch": self.last_poll_epoch, "seen": list(self._seen)}

    def _remember(self, fingerprint: str) -> bool:
        if fingerprint in self._seen_set:
            return False
        if len(self._seen) == MAX_SEEN:
            self._seen_set.discard(self._seen.popleft())
        self._seen.append(fingerprint)
        self._seen_set.add(fingerprint)
        return True

    def ingest(self, rows: list[dict[str, Any]], *, timestamp: float | None = None,
               login_failures: int = 3, firewall_probes: int = 10) -> list[dict[str, Any]]:
        now = float(time.time() if timestamp is None else timestamp)
        login_failures = max(2, min(int(login_failures), 50))
        firewall_probes = max(3, min(int(firewall_probes), 100))
        warm_start = not self.baselined or (self.last_poll_epoch and now - self.last_poll_epoch > 600)
        self.baselined = True
        self.last_poll_epoch = now
        incidents: list[dict[str, Any]] = []
        display: list[dict[str, str]] = []
        # Rows from /log/print arrive oldest first; display newest first.
        for row in rows[-MAX_SEEN:]:
            original_message = str(row.get("message") or "")
            original_topics = str(row.get("topics") or "")
            original_time = str(row.get("time") or "")
            key = hashlib.sha256((str(row.get(".id") or "") + "\x1f" + original_time + "\x1f" + original_topics + "\x1f" + original_message).encode("utf-8", "replace")).hexdigest()[:32]
            event_kind, source_ip = classify_log(original_topics, original_message)
            entry = {"time": safe_text(original_time, 50),
                     "topics": safe_text(original_topics, 90),
                     "message": safe_text(original_message),
                     "category": event_kind or "normal",
                     "severity": "security" if event_kind else "normal"}
            display.append(entry)
            if not self._remember(key) or warm_start or not event_kind or not source_ip:
                continue
            group = (event_kind, source_ip)
            counts = self._counters.setdefault(group, deque())
            counts.append(now)
            while counts and now - counts[0] > WINDOW_SECONDS:
                counts.popleft()
            threshold = 1 if event_kind == "external_admin_login" else login_failures if event_kind == "failed_admin_login" else firewall_probes
            if len(counts) < threshold or now - self._last_alert.get(group, 0) < ALERT_COOLDOWN_SECONDS:
                continue
            self._last_alert[group] = now
            incident = {"category": event_kind, "source_ip": source_ip, "count": len(counts),
                        "time": entry["time"], "topics": entry["topics"],
                        "observed_at": datetime.fromtimestamp(now, timezone.utc).isoformat(),
                        "confidence": "high" if event_kind == "external_admin_login" else "medium"}
            incidents.append(incident)
            self._incidents.append(incident)
        self._recent = list(reversed(display[-MAX_LOG_ROWS:]))
        # Bound internal counters; stale entries must not occupy memory indefinitely.
        for group in list(self._counters):
            counter = self._counters[group]
            while counter and now - counter[0] > WINDOW_SECONDS:
                counter.popleft()
            if not counter:
                self._counters.pop(group, None)
        for group, stamp in list(self._last_alert.items()):
            if now - stamp > 86400:
                self._last_alert.pop(group, None)
        return incidents

    def rows(self, *, category: str = "all", search: str = "", offset: int = 0, limit: int = 50) -> tuple[list[dict[str, str]], int]:
        query = safe_text(search, 80).casefold()
        filtered = [r for r in self._recent
                    if (category == "all" or category == "security" and r["category"] != "normal"
                        or category == "warning" and ("warning" in r["topics"].lower() or "error" in r["topics"].lower() or "critical" in r["topics"].lower()))
                    and (not query or query in (r["time"] + " " + r["topics"] + " " + r["message"]).casefold())]
        return filtered[offset:offset + min(limit, 100)], len(filtered)

    @property
    def recent_incidents(self) -> list[dict[str, Any]]:
        return list(self._incidents)
