"""Constants for Netwatcher MikMi."""
from __future__ import annotations

DOMAIN = "netwatcher_mikmi"
NAME = "Netwatcher MikMi"
VERSION = "0.3.0-beta.1"

CONF_ROUTER_HOST = "router_host"
CONF_ROUTER_PORT = "router_port"
CONF_ROUTER_USERNAME = "router_username"
CONF_ROUTER_PASSWORD = "router_password"
CONF_ROUTER_FINGERPRINT = "router_sha256_fingerprint"
CONF_XIAOMI_HOSTS = "xiaomi_hosts"
CONF_XIAOMI_PASSWORD = "xiaomi_password"
CONF_POLL_INTERVAL = "poll_interval"
CONF_OFFLINE_AFTER = "offline_after"
CONF_NOTIFY_EXISTING = "notify_existing_dynamic"
CONF_NOTIFY_PERSISTENT = "notify_persistent"
CONF_LAN_PORTS = "lan_endpoint_ports"
CONF_DIRECT_AP_HOSTS = "verified_direct_ap_hosts"
CONF_TRACKERS = "enable_device_trackers"

DEFAULT_POLL = 30
DEFAULT_OFFLINE = 120
MAX_DEVICES = 2500
EVENT_NEW_DYNAMIC = "netwatcher_mikmi_new_dynamic_device"
EVENT_CONNECTED = "netwatcher_mikmi_device_connected"
EVENT_DISCONNECTED = "netwatcher_mikmi_device_disconnected"
CARD_URL = "/netwatcher-mikmi/netwatcher-mikmi-card.js"

# Zalo personal-account notifications via the separately installed Zalo Bot integration.
# Deliberately different names from v0.2.0-beta.1 OA options (safe migration).
CONF_ZALO_BOT_ENABLED = "zalo_bot_enabled"
CONF_ZALO_BOT_ACCOUNT = "zalo_bot_account_selection"
CONF_ZALO_BOT_USERS = "zalo_bot_user_thread_ids"
CONF_ZALO_BOT_GROUPS = "zalo_bot_group_thread_ids"
CONF_ZALO_NOTIFY_DYNAMIC = "zalo_notify_dynamic"
CONF_ZALO_NOTIFY_ONLINE = "zalo_notify_online"
CONF_ZALO_NOTIFY_OFFLINE = "zalo_notify_offline"
CONF_ZALO_INCLUDE_MAC = "zalo_include_mac"

# RouterOS logs: read-only memory buffer, optional WAN/security notifications.
CONF_LOG_ENABLED = "enable_router_logs"
CONF_LOG_INTERVAL = "router_log_poll_interval"
CONF_WAN_ALERTS = "notify_wan_security"
CONF_ZALO_NOTIFY_WAN = "zalo_notify_wan_security"
CONF_LOGIN_FAIL_THRESHOLD = "login_failures_threshold"
CONF_FIREWALL_THRESHOLD = "wan_firewall_threshold"
DEFAULT_LOG_INTERVAL = 60
EVENT_WAN_SECURITY = "netwatcher_mikmi_wan_security_alert"
