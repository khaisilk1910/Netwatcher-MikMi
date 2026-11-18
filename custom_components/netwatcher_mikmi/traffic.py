"""Accurate bitrate from monotonic time and cumulative interface counters.

First sample, clock anomalies, and counter resets are unknown (None), not zero.
"""
from __future__ import annotations

import time
from typing import Any


class InterfaceRateTracker:
    def __init__(self) -> None:
        self._prev: dict[str, tuple[int, int, float]] = {}

    @staticmethod
    def _parse(value: Any) -> int | None:
        try:
            parsed = int(str(value))
            return parsed if parsed >= 0 else None
        except (TypeError, ValueError):
            return None

    def ingest(self, rows: list[dict[str, Any]], now: float | None = None) -> dict[str, dict[str, float | None]]:
        now = time.monotonic() if now is None else now
        rates: dict[str, dict[str, float | None]] = {}
        active: set[str] = set()
        for row in rows[:512]:
            name = str(row.get('name') or '').strip()[:64]
            if not name:
                continue
            active.add(name)
            rx = self._parse(row.get('rx-byte'))
            tx = self._parse(row.get('tx-byte'))
            prev = self._prev.get(name)
            in_bps = out_bps = None
            if rx is not None and tx is not None:
                if prev and now > prev[2]:
                    seconds = now - prev[2]
                    if rx >= prev[0]:
                        in_bps = round((rx - prev[0]) * 8 / seconds, 1)
                    if tx >= prev[1]:
                        out_bps = round((tx - prev[1]) * 8 / seconds, 1)
                self._prev[name] = (rx, tx, now)
            rates[name] = {'rx_bps': in_bps, 'tx_bps': out_bps, 'running': row.get('running') == 'true'}
        self._prev = {k: v for k, v in self._prev.items() if k in active}
        return rates


def choose_wan(rows: list[dict[str, Any]], configured: str = '') -> str | None:
    names = {str(r.get('name') or '') for r in rows}
    if configured:
        return configured if configured in names else None
    for row in rows:
        if 'pppoe' in str(row.get('type') or '').lower() and row.get('name'):
            return str(row['name'])
    if 'pppoe-out1' in names:
        return 'pppoe-out1'
    return None
