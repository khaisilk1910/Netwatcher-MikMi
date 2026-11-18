"""Zalo PERSONAL transport using the user's independently installed Zalo Bot.

Netwatcher never logs in to Zalo, never holds cookies or account passwords,
and never calls an undocumented Zalo endpoint itself. Only explicit read-only
monitor events are forwarded to the trusted Home Assistant service action.

Zalo Bot / zca-js is unofficial personal-account automation: legal/ToS and
account restriction risk MUST be accepted separately before enabling it.
"""
from __future__ import annotations

import asyncio
from collections import deque
import logging
import time
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import (
    CONF_ZALO_BOT_ENABLED, CONF_ZALO_BOT_ACCOUNT, CONF_ZALO_BOT_USERS,
    CONF_ZALO_BOT_GROUPS, CONF_ZALO_NOTIFY_DYNAMIC,
    CONF_ZALO_NOTIFY_ONLINE, CONF_ZALO_NOTIFY_OFFLINE, CONF_ZALO_INCLUDE_MAC,
)
from .security import parse_recipients

_LOGGER = logging.getLogger(__name__)
SERVICE_DOMAIN = "zalo_bot"
SERVICE_NAME = "send_message"
MAX_SENDS_PER_HOUR = 60
MAX_BATCH_RECIPIENTS = 20
SERVICE_TIMEOUT = 18


def _single_line(value: object, limit: int = 90) -> str:
    """Avoid forged newlines in DHCP comments and client-provided host names."""
    text = " ".join(str(value or "").split())
    return text[:limit] if text else "-"


def format_alert(event: str, device: dict[str, Any], local_time: str, include_mac: bool = True) -> str:
    """Consistent emoji text (Zalo Bot handles any optional formatting)."""
    titles = {
        "new_dynamic": "\U0001f6a8 NETWATCHER MIKMI | THI\u1ebeT B\u1eca M\u1edaI",
        "connected": "\U0001f7e2 NETWATCHER MIKMI | ONLINE",
        "disconnected": "\U0001f534 NETWATCHER MIKMI | OFFLINE",
    }
    summaries = {
        "new_dynamic": "\u26a0\ufe0f DHCP: D (Dynamic) - ch\u01b0a g\u00e1n Static Lease",
        "connected": "\u2705 Tr\u1ea1ng th\u00e1i: \u0110\u00e3 k\u1ebft n\u1ed1i",
        "disconnected": "\U0001f4f4 Tr\u1ea1ng th\u00e1i: Kh\u00f4ng c\u00f2n \u0111\u01b0\u1ee3c ph\u00e1t hi\u1ec7n",
    }
    link = str(device.get("connection") or "unknown")
    mode = (
        "Wi-Fi" + (f" {_single_line(device.get('wifi_band'), 20)}" if device.get("wifi_band") else "")
        if link == "wifi" else "LAN" if link == "lan" else "Ch\u01b0a x\u00e1c \u0111\u1ecbnh"
    )
    lines = [
        titles.get(event, titles["connected"]),
        "\u2501" * 22,
        summaries.get(event, ""),
        "",
        f"\U0001f4f1 Thi\u1ebft b\u1ecb: {_single_line(device.get('alias') or device.get('comment') or device.get('xiaomi_name') or device.get('host_name') or device.get('mac'))}",
        f"\U0001f310 IP: {_single_line(device.get('ip'))}",
    ]
    if include_mac:
        lines.append(f"\U0001f516 MAC: {_single_line(device.get('mac'))}")
    lines += [
        f"\U0001f4dd Comment: {_single_line(device.get('comment'))}",
        f"\U0001f512 DHCP: {'D - Dynamic' if device.get('dhcp_dynamic') is True else 'Static' if device.get('dhcp_dynamic') is False else 'Unmanaged / Unknown'}",
        f"\U0001f50c K\u1ebft n\u1ed1i: {mode}",
        f"\U0001f4e1 AP / Port: {_single_line(device.get('ap_name') or device.get('port') or 'Ch\u01b0a x\u00e1c \u0111\u1ecbnh')}",
        f"\U0001f552 Th\u1eddi gian: {_single_line(local_time)}",
        "",
    ]
    if event == "new_dynamic":
        lines.append("\U0001f6e1\ufe0f Ki\u1ec3m tra thi\u1ebft b\u1ecb tr\u01b0\u1edbc khi cho ph\u00e9p s\u1eed d\u1ee5ng m\u1ea1ng.")
    elif event == "disconnected":
        lines.append("\u2139\ufe0f Offline theo d\u1eef li\u1ec7u quan s\u00e1t, kh\u00f4ng kh\u1eb3ng \u0111\u1ecbnh thi\u1ebft b\u1ecb t\u1eaft ngu\u1ed3n.")
    else:
        lines.append("\u2705 Thi\u1ebft b\u1ecb v\u1eeba tr\u1edf l\u1ea1i tr\u1ef1c tuy\u1ebfn.")
    lines.append("\U0001f3e0 Netwatcher MikMi | Network Monitor")
    return "\n".join(lines)[:1900]



class ZaloNotifier:
    """Submit events through Home Assistant's Zalo Bot service.

    A completed service response means *accepted by the integration*, not
    guaranteed delivery to the recipient's mobile phone.
    """

    def __init__(self, hass: HomeAssistant, settings: dict[str, Any]) -> None:
        self._hass = hass
        self._settings = settings
        self._send_slots = asyncio.Semaphore(2)
        self._used: deque[float] = deque()
        self._last_test = 0.0

    @property
    def enabled(self) -> bool:
        # Intentionally ignores v0.2.0-beta.1 zalo_enabled and OA credentials.
        return bool(self._settings.get(CONF_ZALO_BOT_ENABLED, False))

    def wants(self, event: str) -> bool:
        return self.enabled and bool(self._settings.get({
            "new_dynamic": CONF_ZALO_NOTIFY_DYNAMIC,
            "connected": CONF_ZALO_NOTIFY_ONLINE,
            "disconnected": CONF_ZALO_NOTIFY_OFFLINE,
        }.get(event, ""), event == "new_dynamic"))

    def _targets(self) -> list[tuple[str, str]]:
        users = parse_recipients(self._settings.get(CONF_ZALO_BOT_USERS, ""))
        groups = parse_recipients(self._settings.get(CONF_ZALO_BOT_GROUPS, ""))
        return ([('0', uid) for uid in users] + [('1', gid) for gid in groups])[:MAX_BATCH_RECIPIENTS]

    def _allow_send(self) -> bool:
        now = time.monotonic()
        while self._used and now - self._used[0] >= 3600:
            self._used.popleft()
        if len(self._used) >= MAX_SENDS_PER_HOUR:
            return False
        self._used.append(now)
        return True

    async def _send_to_target(self, target_type: str, thread_id: str, message: str) -> bool:
        """Avoid putting raw numeric IDs in HA templates or frontend numbers.

        Zalo Bot strips the `zalo:` prefix before passing the exact ID text
        to its JS backend. Never cast IDs to int/float (53-bit precision risk).
        """
        account = str(self._settings.get(CONF_ZALO_BOT_ACCOUNT, "")).strip()
        if not self._hass.services.has_service(SERVICE_DOMAIN, SERVICE_NAME):
            return False
        payload = {
            "message": message,
            "thread_id": f"zalo:{thread_id}",
            "account_selection": account,
            "type": target_type,
        }
        try:
            async with self._send_slots:
                # v2026.11 Zalo Bot supports optional service response and
                # propagates server errors as HomeAssistantError.
                result = await asyncio.wait_for(
                    self._hass.services.async_call(
                        SERVICE_DOMAIN, SERVICE_NAME, payload,
                        blocking=True, return_response=True,
                    ),
                    timeout=SERVICE_TIMEOUT,
                )
            if isinstance(result, dict) and (result.get('success') is False or result.get('error')):
                _LOGGER.warning('Personal Zalo service rejected a message (type=%s)', target_type)
                return False
            return True
        except Exception as exc:
            # Avoid logging exception strings: some third-party exceptions may
            # include thread ID, account selection, or message content.
            _LOGGER.warning('Personal Zalo service failed: kind=%s type=%s', type(exc).__name__, target_type)
            return False

    async def _send_text(self, message: str) -> dict[str, int | bool]:
        if not self.enabled:
            return {"submitted": 0, "failed": 0, "rate_limited": 0}
        targets = self._targets()
        if not targets or not self._settings.get(CONF_ZALO_BOT_ACCOUNT):
            _LOGGER.warning('Personal Zalo is enabled but account/recipients are not configured')
            return {"submitted": 0, "failed": len(targets), "rate_limited": 0}
        if not self._hass.services.has_service(SERVICE_DOMAIN, SERVICE_NAME):
            _LOGGER.warning('Personal Zalo unavailable: install and configure Zalo Bot before enabling alerts')
            return {"submitted": 0, "failed": len(targets), "rate_limited": 0, "service_missing": True}
        result: dict[str, int | bool] = {"submitted": 0, "failed": 0, "rate_limited": 0}
        for target_type, thread_id in targets:
            if not self._allow_send():
                result['rate_limited'] += 1
                continue
            if await self._send_to_target(target_type, thread_id, message):
                result['submitted'] += 1
            else:
                result['failed'] += 1
        return result

    async def send_event(self, event: str, device: dict[str, Any]) -> dict[str, int | bool]:
        if not self.wants(event):
            return {"submitted": 0, "failed": 0, "rate_limited": 0}
        timestamp = dt_util.now().strftime('%d/%m/%Y %H:%M:%S')
        body = format_alert(event, device, timestamp, bool(self._settings.get(CONF_ZALO_INCLUDE_MAC, False)))
        result = await self._send_text(body)
        _LOGGER.info('Personal Zalo alert %s: submitted=%d failed=%d throttled=%d',
                     event, result['submitted'], result['failed'], result['rate_limited'])
        return result

    async def send_security_alert(self, incident: dict[str, Any]) -> dict[str, int | bool]:
        """Send a deduplicated WAN log incident via the SAME personal Zalo action."""
        if not self.enabled:
            return {"submitted": 0, "failed": 0, "rate_limited": 0}
        kind = str(incident.get("category") or "unknown")
        labels = {
            "external_admin_login": "🚨 ĐĂNG NHẬP QUẢN TRỊ TỪ IP CÔNG CỘNG",
            "failed_admin_login": "⚠️ NHIỀU LẦN ĐĂNG NHẬP THẤT BẠI",
            "wan_management_probe": "🛡️ TRUY CẬP WAN VÀO CỔNG QUẢN TRỊ",
        }
        message = "\n".join([
            "🚨 NETWATCHER MIKMI | CẢNH BÁO WAN",
            "━━━━━━━━━━━━━━━━━━━━━━",
            labels.get(kind, "⚠️ Sự kiện bảo mật cần kiểm tra"),
            "",
            f"🌍 IP nguồn: {_single_line(incident.get('source_ip'), 60)}",
            f"🔁 Số lần ghi nhận trong 5 phút: {int(incident.get('count', 1))}",
            f"🏷️ Phân loại: {_single_line(kind, 60)}",
            f"📋 RouterOS topic: {_single_line(incident.get('topics'), 90)}",
            f"🕒 Thời điểm RouterOS: {_single_line(incident.get('time'), 50)}",
            "",
            "ℹ️ Đây là cảnh báo từ log, KHÔNG phải kết luận router đã bị xâm nhập.",
            "🔒 Kiểm tra firewall input, nhật ký đăng nhập và VPN quản trị.",
            "🏠 Netwatcher MikMi | Network Security",
        ])[:1500]
        result = await self._send_text(message)
        _LOGGER.info('Personal Zalo WAN alert category=%s: submitted=%d failed=%d',
                     kind, result['submitted'], result['failed'])
        return result

    async def send_test(self) -> dict[str, int | bool]:
        if not self.enabled:
            return {"submitted": 0, "failed": 0, "rate_limited": 0, "disabled": True}
        now = time.monotonic()
        if now - self._last_test < 60:
            return {"submitted": 0, "failed": 0, "rate_limited": 0, "cooldown": True}
        self._last_test = now
        message = ('🧪 NETWATCHER MIKMI | KIỂM TRA ZALO CÁ NHÂN\n'
                   '━━━━━━━━━━━━━━━━━━━━━━\n'
                   '✅ Netwatcher đã gọi action zalo_bot.send_message.\n'
                   '📨 Đây là tin kiểm tra đến danh sách người nhận đã cấu hình.\n'
                   '🛡️ Không chứa thông tin thiết bị mạng.\n'
                   f'🕒 Thời gian: {dt_util.now().strftime("%d/%m/%Y %H:%M:%S")}')
        return await self._send_text(message)
