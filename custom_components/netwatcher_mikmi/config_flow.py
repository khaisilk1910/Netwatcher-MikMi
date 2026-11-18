"""Config, reauthentication, reconfigure, and options via the Home Assistant UI."""
from __future__ import annotations

from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType

from .const import (
    CONF_LAN_PORTS, CONF_NOTIFY_EXISTING,
    CONF_NOTIFY_PERSISTENT, CONF_OFFLINE_AFTER, CONF_POLL_INTERVAL,
    CONF_ROUTER_FINGERPRINT, CONF_ROUTER_HOST, CONF_ROUTER_PASSWORD,
    CONF_ROUTER_PORT, CONF_ROUTER_USERNAME, CONF_TRACKERS,
    DEFAULT_OFFLINE, DEFAULT_POLL, DOMAIN,
    CONF_ZALO_BOT_ENABLED, CONF_ZALO_BOT_ACCOUNT, CONF_ZALO_BOT_USERS, CONF_ZALO_BOT_GROUPS,
    CONF_ZALO_NOTIFY_DYNAMIC, CONF_ZALO_NOTIFY_ONLINE, CONF_ZALO_NOTIFY_OFFLINE,
    CONF_ZALO_INCLUDE_MAC,
    CONF_LOG_ENABLED, CONF_LOG_INTERVAL, CONF_WAN_ALERTS, CONF_ZALO_NOTIFY_WAN,
    CONF_LOGIN_FAIL_THRESHOLD, CONF_FIREWALL_THRESHOLD, DEFAULT_LOG_INTERVAL,
    CONF_HARDWARE_INTERVAL, CONF_HEALTH_DETAIL_INTERVAL,
    CONF_HARDWARE_ALERTS, CONF_HARDWARE_CPU_ENABLED, CONF_HARDWARE_RAM_ENABLED,
    CONF_HARDWARE_TEMP_ENABLED, CONF_HARDWARE_CPU_THRESHOLD,
    CONF_HARDWARE_RAM_THRESHOLD, CONF_HARDWARE_TEMP_THRESHOLD,
    CONF_HARDWARE_SAMPLES, CONF_HARDWARE_RECOVERY, CONF_HARDWARE_ZALO,
    CONF_HARDWARE_COOLDOWN, DEFAULT_HARDWARE_INTERVAL,
    DEFAULT_HEALTH_DETAIL_INTERVAL, CONF_NETWATCH_ENABLED,
    CONF_NETWATCH_INTERVAL, DEFAULT_NETWATCH_INTERVAL, CONF_WAN_INTERFACE,
)
from .routeros import RouterAuthError, RouterCertificateError, RouterOSReader
from .security import fingerprint_sha256, port_names, private_ipv4, parse_recipients

PASSWORD = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))


def _schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    data = defaults or {}
    return vol.Schema({
        vol.Required(CONF_ROUTER_HOST, default=data.get(CONF_ROUTER_HOST, "192.168.88.1")): str,
        vol.Required(CONF_ROUTER_PORT, default=int(data.get(CONF_ROUTER_PORT, 8729))): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
        vol.Required(CONF_ROUTER_USERNAME, default=data.get(CONF_ROUTER_USERNAME, "ha_reader")): str,
        vol.Required(CONF_ROUTER_PASSWORD, default=data.get(CONF_ROUTER_PASSWORD, "")): PASSWORD,
        vol.Required(CONF_ROUTER_FINGERPRINT, default=data.get(CONF_ROUTER_FINGERPRINT, "")): str,
    })


async def _verify(hass, values: dict[str, Any]) -> str | None:
    try:
        private_ipv4(values[CONF_ROUTER_HOST])
        fingerprint_sha256(values[CONF_ROUTER_FINGERPRINT])
    except (ValueError, TypeError):
        return "invalid_hosts"
    reader = RouterOSReader(values[CONF_ROUTER_HOST], values[CONF_ROUTER_PORT],
                            values[CONF_ROUTER_USERNAME], values[CONF_ROUTER_PASSWORD],
                            values[CONF_ROUTER_FINGERPRINT])
    try:
        # This network check only runs on the INTERACTIVE config screen.
        await hass.async_add_executor_job(reader.fetch)
    except RouterCertificateError:
        return "bad_fingerprint"
    except RouterAuthError:
        return "invalid_auth"
    except Exception:
        return "cannot_connect"
    return None


class NetwatcherMikMiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors = {}
        if user_input is not None:
            error = await _verify(self.hass, user_input)
            if error:
                errors["base"] = error
            else:
                await self.async_set_unique_id(private_ipv4(user_input[CONF_ROUTER_HOST]))
                self._abort_if_unique_id_configured()
                config = dict(user_input)
                config[CONF_ROUTER_FINGERPRINT] = fingerprint_sha256(config[CONF_ROUTER_FINGERPRINT])
                return self.async_create_entry(title=f"Netwatcher MikMi - {config[CONF_ROUTER_HOST]}", data=config)
        return self.async_show_form(step_id="user", data_schema=_schema(), errors=errors)

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        if entry is None:
            return self.async_abort(reason="unknown")
        errors = {}
        if user_input is not None:
            updated = {**entry.data, **user_input}
            error = await _verify(self.hass, updated)
            if error:
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(entry, data=updated)
        return self.async_show_form(step_id="reauth_confirm", data_schema=vol.Schema({
            vol.Required(CONF_ROUTER_PASSWORD): PASSWORD,
            vol.Required(CONF_ROUTER_FINGERPRINT, default=entry.data[CONF_ROUTER_FINGERPRINT]): str,
        }), errors=errors)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        if entry is None:
            return self.async_abort(reason="unknown")
        errors = {}
        if user_input is not None:
            error = await _verify(self.hass, user_input)
            if error:
                errors["base"] = error
            else:
                data = dict(user_input)
                data[CONF_ROUTER_FINGERPRINT] = fingerprint_sha256(data[CONF_ROUTER_FINGERPRINT])
                return self.async_update_reload_and_abort(entry, data=data)
        return self.async_show_form(step_id="reconfigure", data_schema=_schema(entry.data), errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> config_entries.OptionsFlow:
        return NetwatcherMikMiOptionsFlow()


class NetwatcherMikMiOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors = {}
        if user_input is not None:
            try:
                port_names(user_input.get(CONF_LAN_PORTS, ""))
                users = parse_recipients(user_input.get(CONF_ZALO_BOT_USERS, ""))
                groups = parse_recipients(user_input.get(CONF_ZALO_BOT_GROUPS, ""))
                if len(users) + len(groups) > 20:
                    errors["base"] = "invalid_options"
                if user_input.get(CONF_ZALO_BOT_ENABLED, False):
                    account = str(user_input.get(CONF_ZALO_BOT_ACCOUNT, "")).strip()
                    # Supports configured Zalo Bot phone (+84...) or own ID, no URL.
                    import re
                    if not re.fullmatch(r"\+?[0-9]{7,24}", account):
                        errors["base"] = "invalid_zalo_account"
                    elif not (users or groups):
                        errors["base"] = "missing_zalo_recipients"
            except ValueError:
                errors["base"] = "invalid_options"
            if (user_input.get(CONF_ZALO_NOTIFY_WAN, False)
                    and not user_input.get(CONF_WAN_ALERTS, False)):
                errors["base"] = "wan_zalo_requires_alerts"
            if (user_input.get(CONF_WAN_ALERTS, False)
                    and not user_input.get(CONF_LOG_ENABLED, True)):
                errors["base"] = "wan_alerts_require_logs"
            if user_input.get(CONF_HARDWARE_ZALO, False) and not user_input.get(CONF_ZALO_BOT_ENABLED, False):
                errors["base"] = "hardware_zalo_requires_bot"
            if user_input.get(CONF_HARDWARE_ZALO, False) and not user_input.get(CONF_HARDWARE_ALERTS, False):
                errors["base"] = "hardware_zalo_requires_alerts"
            if (int(user_input.get(CONF_HEALTH_DETAIL_INTERVAL, DEFAULT_HEALTH_DETAIL_INTERVAL))
                    < int(user_input.get(CONF_HARDWARE_INTERVAL, DEFAULT_HARDWARE_INTERVAL))):
                errors["base"] = "health_interval_too_short"
            if not errors:
                # Only fields in the new schema are saved: old OA tokens are
                # dropped from this config entry on the first Options save.
                return self.async_create_entry(title="", data=user_input)
        opts = self.config_entry.options
        schema = vol.Schema({
            vol.Required(CONF_POLL_INTERVAL, default=opts.get(CONF_POLL_INTERVAL, DEFAULT_POLL)): vol.All(vol.Coerce(int), vol.Range(min=15, max=600)),
            vol.Optional(CONF_WAN_INTERFACE, default=opts.get(CONF_WAN_INTERFACE, "")): str,
            vol.Required(CONF_OFFLINE_AFTER, default=opts.get(CONF_OFFLINE_AFTER, DEFAULT_OFFLINE)): vol.All(vol.Coerce(int), vol.Range(min=60, max=3600)),
            vol.Required(CONF_HARDWARE_INTERVAL, default=opts.get(CONF_HARDWARE_INTERVAL, DEFAULT_HARDWARE_INTERVAL)): vol.All(vol.Coerce(int), vol.Range(min=10, max=300)),
            vol.Required(CONF_HEALTH_DETAIL_INTERVAL, default=opts.get(CONF_HEALTH_DETAIL_INTERVAL, DEFAULT_HEALTH_DETAIL_INTERVAL)): vol.All(vol.Coerce(int), vol.Range(min=30, max=600)),
            vol.Required(CONF_HARDWARE_ALERTS, default=opts.get(CONF_HARDWARE_ALERTS, False)): bool,
            vol.Required(CONF_HARDWARE_CPU_ENABLED, default=opts.get(CONF_HARDWARE_CPU_ENABLED, True)): bool,
            vol.Required(CONF_HARDWARE_RAM_ENABLED, default=opts.get(CONF_HARDWARE_RAM_ENABLED, True)): bool,
            vol.Required(CONF_HARDWARE_TEMP_ENABLED, default=opts.get(CONF_HARDWARE_TEMP_ENABLED, True)): bool,
            vol.Required(CONF_HARDWARE_CPU_THRESHOLD, default=opts.get(CONF_HARDWARE_CPU_THRESHOLD, 85)): vol.All(vol.Coerce(int), vol.Range(min=30, max=100)),
            vol.Required(CONF_HARDWARE_RAM_THRESHOLD, default=opts.get(CONF_HARDWARE_RAM_THRESHOLD, 90)): vol.All(vol.Coerce(int), vol.Range(min=30, max=100)),
            vol.Required(CONF_HARDWARE_TEMP_THRESHOLD, default=opts.get(CONF_HARDWARE_TEMP_THRESHOLD, 75)): vol.All(vol.Coerce(int), vol.Range(min=30, max=120)),
            vol.Required(CONF_HARDWARE_SAMPLES, default=opts.get(CONF_HARDWARE_SAMPLES, 3)): vol.All(vol.Coerce(int), vol.Range(min=1, max=10)),
            vol.Required(CONF_HARDWARE_COOLDOWN, default=opts.get(CONF_HARDWARE_COOLDOWN, 30)): vol.All(vol.Coerce(int), vol.Range(min=0, max=1440)),
            vol.Required(CONF_HARDWARE_RECOVERY, default=opts.get(CONF_HARDWARE_RECOVERY, True)): bool,
            vol.Required(CONF_HARDWARE_ZALO, default=opts.get(CONF_HARDWARE_ZALO, False)): bool,
            vol.Required(CONF_NETWATCH_ENABLED, default=opts.get(CONF_NETWATCH_ENABLED, False)): bool,
            vol.Required(CONF_NETWATCH_INTERVAL, default=opts.get(CONF_NETWATCH_INTERVAL, DEFAULT_NETWATCH_INTERVAL)): vol.All(vol.Coerce(int), vol.Range(min=60, max=600)),
            vol.Required(CONF_NOTIFY_EXISTING, default=opts.get(CONF_NOTIFY_EXISTING, False)): bool,
            vol.Required(CONF_NOTIFY_PERSISTENT, default=opts.get(CONF_NOTIFY_PERSISTENT, True)): bool,
            vol.Required(CONF_TRACKERS, default=opts.get(CONF_TRACKERS, False)): bool,
            vol.Optional(CONF_LAN_PORTS, default=opts.get(CONF_LAN_PORTS, "")): str,
            vol.Required(CONF_ZALO_BOT_ENABLED, default=opts.get(CONF_ZALO_BOT_ENABLED, False)): bool,
            vol.Optional(CONF_ZALO_BOT_ACCOUNT, default=opts.get(CONF_ZALO_BOT_ACCOUNT, "")): str,
            vol.Optional(CONF_ZALO_BOT_USERS, default=opts.get(CONF_ZALO_BOT_USERS, "")): str,
            vol.Optional(CONF_ZALO_BOT_GROUPS, default=opts.get(CONF_ZALO_BOT_GROUPS, "")): str,
            vol.Required(CONF_ZALO_NOTIFY_DYNAMIC, default=opts.get(CONF_ZALO_NOTIFY_DYNAMIC, True)): bool,
            vol.Required(CONF_ZALO_NOTIFY_ONLINE, default=opts.get(CONF_ZALO_NOTIFY_ONLINE, False)): bool,
            vol.Required(CONF_ZALO_NOTIFY_OFFLINE, default=opts.get(CONF_ZALO_NOTIFY_OFFLINE, False)): bool,
            vol.Required(CONF_ZALO_INCLUDE_MAC, default=opts.get(CONF_ZALO_INCLUDE_MAC, False)): bool,
            vol.Required(CONF_LOG_ENABLED, default=opts.get(CONF_LOG_ENABLED, True)): bool,
            vol.Required(CONF_LOG_INTERVAL, default=opts.get(CONF_LOG_INTERVAL, DEFAULT_LOG_INTERVAL)): vol.All(vol.Coerce(int), vol.Range(min=30, max=600)),
            vol.Required(CONF_WAN_ALERTS, default=opts.get(CONF_WAN_ALERTS, False)): bool,
            vol.Required(CONF_ZALO_NOTIFY_WAN, default=opts.get(CONF_ZALO_NOTIFY_WAN, False)): bool,
            vol.Required(CONF_LOGIN_FAIL_THRESHOLD, default=opts.get(CONF_LOGIN_FAIL_THRESHOLD, 3)): vol.All(vol.Coerce(int), vol.Range(min=2, max=50)),
            vol.Required(CONF_FIREWALL_THRESHOLD, default=opts.get(CONF_FIREWALL_THRESHOLD, 10)): vol.All(vol.Coerce(int), vol.Range(min=3, max=100)),
        })
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
