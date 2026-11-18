"""Pure, separately testable hardware normalization and threshold state machine.

Never derive a fabricated temperature if RouterOS does not expose a sensor.
No host, password, IP, serial, MAC, log contents, or account ID is logged.
"""
from __future__ import annotations

import re
import time
from typing import Any

_BYTE_UNITS = {"": 1, "b": 1, "k": 1000, "kb": 1000, "m": 1000**2,
               "mb": 1000**2, "g": 1000**3, "gb": 1000**3,
               "ki": 1024, "kib": 1024, "mi": 1024**2, "mib": 1024**2,
               "gi": 1024**3, "gib": 1024**3}


def number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip().replace(",", ".")
    match = re.fullmatch(r"([-+]?(?:\d+(?:\.\d*)?|\.\d+))\s*(?:%|°?[CF]|rpm|V|A|W|MHz)?", text, re.I)
    if not match:
        return None
    try:
        val = float(match.group(1))
        return val if abs(val) < 10**16 else None
    except ValueError:
        return None


def byte_count(value: Any) -> int | None:
    if value is None:
        return None
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([kmg]?i?b?|b)?\s*", str(value), re.I)
    if not match:
        return None
    unit = (match.group(2) or "").lower()
    factor = _BYTE_UNITS.get(unit)
    return round(float(match.group(1)) * factor) if factor else None


def percent(used: float, total: float) -> float | None:
    if total <= 0 or used < 0 or used > total:
        return None
    return round(min(100.0, max(0.0, 100 * used / total)), 1)


def uptime_seconds(value: Any) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    if re.fullmatch(r"\d+:\d{2}:\d{2}", text):
        hh, mm, ss = map(int, text.split(":"))
        return hh * 3600 + mm * 60 + ss if mm < 60 and ss < 60 else None
    # RouterOS prints 1w2d03:04:05 in some revisions, 2w3d4h5m6s in others.
    prefix = re.fullmatch(r"(?:(\d+)w)?(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?", text)
    if prefix and any(x is not None for x in prefix.groups()):
        w, d, h, m, s = (int(x or 0) for x in prefix.groups())
        return w * 604800 + d * 86400 + h * 3600 + m * 60 + s
    mixed = re.fullmatch(r"(?:(\d+)w)?(?:(\d+)d)?(\d+):(\d{2}):(\d{2})", text)
    if mixed:
        w, d, h, m, s = (int(x or 0) for x in mixed.groups())
        return w * 604800 + d * 86400 + h * 3600 + m * 60 + s if m < 60 and s < 60 else None
    return None


def clean_label(value: Any, limit: int = 80) -> str:
    return re.sub(r"[\x00-\x1f\x7f]", " ", str(value or "")).strip()[:limit]


def normalize_hardware(raw: dict[str, Any], previous: dict[str, Any] | None = None) -> dict[str, Any]:
    """Produce typed readings and metadata for sensors and the card.

    Only reuse slower fields when they were deliberately not queried, not when
    the router replied with an empty (unsupported) sensor list.
    """
    previous = previous or {}
    r = (raw.get("resource") or [{}])[0]
    # /system/routerboard is polled slowly; its previous normalized keys are
    # firmware/upgrade_firmware, not RouterOS current-firmware/upgrade-firmware.
    # Preserve these values when the command was skipped or returned no rows.
    b = (raw.get("routerboard") or [{}])[0] if "routerboard" in raw else {}
    prior_board = previous.get("board", {})
    total_ram = byte_count(r.get("total-memory"))
    free_ram = byte_count(r.get("free-memory"))
    total_disk = byte_count(r.get("total-hdd-space"))
    free_disk = byte_count(r.get("free-hdd-space"))
    cpu = number(r.get("cpu-load"))
    readings: dict[str, Any] = {
        "cpu": round(cpu, 1) if cpu is not None and 0 <= cpu <= 100 else None,
        "ram": percent(total_ram - free_ram, total_ram) if total_ram is not None and free_ram is not None else None,
        "storage": percent(total_disk - free_disk, total_disk) if total_disk is not None and free_disk is not None else None,
        "total_ram_mib": round(total_ram / 1048576, 1) if total_ram is not None else None,
        "free_ram_mib": round(free_ram / 1048576, 1) if free_ram is not None else None,
        "total_storage_mib": round(total_disk / 1048576, 1) if total_disk is not None else None,
        "temperature": None, "cpu_temperature": None, "board_temperature": None,
        "voltage": None, "fan_rpm": None, "uptime_seconds": uptime_seconds(r.get("uptime")),
        "cpu_count": int(number(r.get("cpu-count"))) if number(r.get("cpu-count")) is not None else None,
        "cpu_frequency_mhz": number(r.get("cpu-frequency")),
    }
    # API /system/health outputs either one row per named sensor (RouterOS 7)
    # or a flat dictionary with temperature, cpu-temperature, voltage, etc.
    if "health" in raw:
        sensors: dict[str, dict[str, Any]] = {}
        for row in raw.get("health", []):
            if "name" in row and "value" in row:
                name = clean_label(row.get("name")).lower().replace("_", "-")
                if name and len(sensors) < 64:
                    sensors[name] = {"value": number(row.get("value")), "raw": clean_label(row.get("value"), 50), "unit": clean_label(row.get("type"), 10)}
            else:
                for key, val in row.items():
                    name = clean_label(key).lower().replace("_", "-")
                    if name in (".id", "name", "type"):
                        continue
                    if len(sensors) < 64:
                        sensors[name] = {"value": number(val), "raw": clean_label(val, 50), "unit": ""}
    else:
        sensors = dict(previous.get("sensors", {}))
    # Non-x86 field 'type=C' or names ending in '-temperature'.
    def first(*aliases: str) -> float | None:
        for alias in aliases:
            record = sensors.get(alias, {})
            value = record.get("value")
            if value is not None:
                return value
        return None
    readings["cpu_temperature"] = first("cpu-temperature", "cpu-temp")
    readings["board_temperature"] = first("board-temperature", "board-temp", "temperature")
    readings["temperature"] = first("cpu-temperature", "cpu-temp", "temperature", "board-temperature", "board-temp", "lm87-temp")
    readings["voltage"] = first("voltage", "input-voltage", "voltage1", "12v")
    readings["fan_rpm"] = first("fan1-speed", "fan1", "fan-speed", "fan1-rpm")
    return {
        "readings": readings,
        "sensors": sensors,
        "board": {
            "model": clean_label(b.get("model") or prior_board.get("model") or r.get("board-name") or "MikroTik"),
            "architecture": clean_label(r.get("architecture-name")),
            "cpu_name": clean_label(r.get("cpu")),
            "platform": clean_label(r.get("platform")),
            "routeros_version": clean_label(r.get("version")),
            "firmware": clean_label(b.get("current-firmware") or prior_board.get("firmware")),
            "upgrade_firmware": clean_label(b.get("upgrade-firmware") or prior_board.get("upgrade_firmware")),
            # Never expose serial number via WebSocket or HA recorder.
        },
        "sampled_at": time.time(),
        "health_supported": bool(sensors),
    }


METRIC_NAMES = {"cpu": "CPU", "ram": "RAM", "temperature": "Nhiệt độ"}


class HardwareAlertEngine:
    """Debounced, hysteretic, persisted threshold alerts; no network side effects."""

    def __init__(self, previous: dict[str, Any] | None = None) -> None:
        saved = previous.get("metrics", {}) if isinstance(previous, dict) else {}
        self.metrics: dict[str, dict[str, Any]] = {
            k: {"active": bool(saved.get(k, {}).get("active", False)),
                "high": 0, "low": 0,
                "last_alert": float(saved.get(k, {}).get("last_alert", 0) or 0)}
            for k in METRIC_NAMES
        }

    def dump(self) -> dict[str, Any]:
        return {"metrics": {k: {"active": v["active"], "last_alert": v["last_alert"]}
                            for k, v in self.metrics.items()}}

    def process(self, readings: dict[str, Any], settings: dict[str, Any], now: float | None = None, observed: set[str] | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        from .const import (
            CONF_HARDWARE_ALERTS, CONF_HARDWARE_CPU_ENABLED, CONF_HARDWARE_RAM_ENABLED,
            CONF_HARDWARE_TEMP_ENABLED, CONF_HARDWARE_CPU_THRESHOLD,
            CONF_HARDWARE_RAM_THRESHOLD, CONF_HARDWARE_TEMP_THRESHOLD,
            CONF_HARDWARE_SAMPLES, CONF_HARDWARE_COOLDOWN,
        )
        now = now if now is not None else time.time()
        samples = max(1, int(settings.get(CONF_HARDWARE_SAMPLES, 3)))
        cooldown = max(0, int(settings.get(CONF_HARDWARE_COOLDOWN, 30))) * 60
        globally_enabled = bool(settings.get(CONF_HARDWARE_ALERTS, False))
        observed = set(METRIC_NAMES) if observed is None else observed
        keys = {
            "cpu": (CONF_HARDWARE_CPU_ENABLED, CONF_HARDWARE_CPU_THRESHOLD, 85., 5.),
            "ram": (CONF_HARDWARE_RAM_ENABLED, CONF_HARDWARE_RAM_THRESHOLD, 90., 5.),
            "temperature": (CONF_HARDWARE_TEMP_ENABLED, CONF_HARDWARE_TEMP_THRESHOLD, 75., 3.),
        }
        result: list[dict[str, Any]] = []
        statuses: dict[str, Any] = {}
        for metric, (flag, threshold_option, default, hysteresis) in keys.items():
            state = self.metrics[metric]
            threshold = float(settings.get(threshold_option, default))
            value = readings.get(metric)
            enabled = globally_enabled and bool(settings.get(flag, True))
            statuses[metric] = {"active": state["active"], "threshold": threshold, "enabled": enabled,
                                "value": value}
            if metric not in observed:
                # Cached slow sensor values are NOT fresh observations.
                continue
            if value is None:
                state["high"] = state["low"] = 0
                continue
            if value >= threshold:
                state["high"] += 1
                state["low"] = 0
                if not state["active"] and state["high"] >= samples:
                    state["active"] = True
                    if enabled and (state["last_alert"] == 0 or now - state["last_alert"] >= cooldown):
                        state["last_alert"] = now
                        result.append({"metric": metric, "kind": "high", "value": value,
                                       "threshold": threshold, "timestamp": now})
            elif value <= threshold - hysteresis:
                state["low"] += 1
                state["high"] = 0
                if state["active"] and state["low"] >= samples:
                    state["active"] = False
                    if enabled:
                        result.append({"metric": metric, "kind": "recovered", "value": value,
                                       "threshold": threshold, "timestamp": now})
            else:
                state["high"] = state["low"] = 0
            statuses[metric]["active"] = state["active"]
        return result, statuses
